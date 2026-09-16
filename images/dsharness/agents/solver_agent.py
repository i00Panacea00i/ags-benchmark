#!/usr/bin/env python3
"""solver agent：运行在独立 agent 沙箱内，通过实例级 Token 直访 bench 沙箱解题。

架构（沙箱互访）：
    CVM validator_driver
     ├─ Sandbox.create(bench-u-<iid>)        ← 题目镜像（内容烧入）
     ├─ tccli AcquireSandboxInstanceToken    ← 实例级访问 Token（sit_…，~24h）
     ├─ Sandbox.create(bench-solver)         ← 本 agent 的宿主沙箱
     └─ 本脚本（envs 注入 Token）→ e2b SDK 直连 bench 沙箱执行命令

互访机制（实测逆向所得，已验证）：
    URL    https://49983-<sandbox_id>.<E2B_DOMAIN>/<rpc>   （端口在前）
    鉴权    X-Access-Token: <sit_ Token>
    SDK    Sandbox.connect(id, debug=True, sandbox_url=…)
           + monkey-patch build_interceptors 注入 Token 头
           （envd 的 X-Access-Token 即 sit_ Token，与官方
            AcquireSandboxInstanceToken 输出同源）
    限制    files API 走独立 /files 端点不读拦截器 → 文件操作一律命令化
            （base64 编解码传输），commands.run 通道完全可用。

输出（stdout 末行 RESULT JSON）：
    {"result": "solved|unsolved|error", "turns": n, "files_changed": [...],
     "fix_summary": "..."}
"""
import base64
import json
import os
import sys

# ───────── 沙箱互访：monkey-patch + 直连构造 ─────────
SIT = os.environ["BENCH_SIT_TOKEN"]
BENCH_ID = os.environ["BENCH_SANDBOX_ID"]
DOMAIN = os.environ["E2B_DOMAIN"]
IID = os.environ["INSTANCE_ID"]

import e2b.envd.client_sync as _cs          # noqa: E402
import e2b.envd.client_async as _ca          # noqa: E402
from e2b.envd.interceptors import DefaultHeadersInterceptor  # noqa: E402


def _with_token(orig):
    def patched(config, base_url):
        lst = orig(config, base_url)
        lst.insert(0, DefaultHeadersInterceptor({"X-Access-Token": SIT}))
        return lst
    return patched


_cs.build_interceptors = _with_token(_cs.build_interceptors)
_ca.build_interceptors = _with_token(_ca.build_interceptors)

from e2b_code_interpreter import Sandbox      # noqa: E402
from e2b.sandbox.commands.command_handle import CommandExitException  # noqa: E402

bench = Sandbox.connect(
    BENCH_ID, debug=True, domain=DOMAIN,
    sandbox_url=f"https://49983-{BENCH_ID}.{DOMAIN}",
)

REPO = f"/benchmark/repos/{os.environ['REPO'].replace('/', '__')}"

# ───────── bench 沙箱操作封装（全部命令化，绕开 files API 鉴权差异） ─────────


def bsh(cmd, timeout=1200):
    """bench 沙箱执行命令，返回 (stdout+stderr)。"""
    try:
        r = bench.commands.run(cmd, timeout=timeout, user="root")
        return (r.stdout or "") + (r.stderr or "")
    except CommandExitException as e:
        return (e.stdout or "") + (e.stderr or "")


def read_file(path):
    return base64.b64decode(
        bsh(f"base64 -w0 {REPO}/{path}").strip()).decode("utf-8", "replace")


def write_file(path, content):
    blob = base64.b64encode(content.encode()).decode()
    return bsh(f"mkdir -p $(dirname {REPO}/{path}) && "
               f"echo {blob} | base64 -d > {REPO}/{path} && echo written")


# ───────── 解题循环（DeepSeekHarness 双协议） ─────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deepseek_harness import DeepSeekHarness, HarnessError  # noqa: E402

TOOLS = [
    {"type": "function", "function": {
        "name": "run_command",
        "description": "在题目仓库内执行 shell 命令（探索代码/运行测试/任意操作）",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string", "description": "bash 命令"}},
            "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "读取题目仓库中的文件内容",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "仓库内相对路径"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "覆写题目仓库中的文件（实施修复）",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"]}}},
]


def exec_fn(name, args):
    if name == "run_command":
        return bsh(f"cd {REPO} && {args['command']}", timeout=600)[:8000]
    if name == "read_file":
        return read_file(args["path"])[:16000]
    if name == "write_file":
        return write_file(args["path"], args["content"])
    return f"unknown tool {name}"


def main():
    # 起始状态：base + tests（无 golden）
    bsh(f"/benchmark/harness/run_tests.sh {IID} --reset --apply-tests")

    problem = os.environ.get("PROBLEM") or IID
    f2p = [t for t in os.environ.get("F2P_TESTS", "").splitlines() if t.strip()]
    system = (
        "你是一名资深 Python 工程师，在仓库中修复一个 bug。\n"
        "执行命令的方式：输出 <execute command=\"你的命令\"/>\n"
        "流程建议：先 cat/grep 探索相关代码 → 运行评分测试复现失败 → 定位根因 → "
        "用命令修改文件（如 python -c 或 sed）实施最小修复 → 再次运行相关测试确认通过 → "
        "最后输出简要修复说明（不再执行命令）。"
    )
    task = (f"【任务】修复以下问题并让指定测试通过。\n\n{problem}\n\n"
            f"【通过的判据】这些测试全部通过即算成功：\n"
            + "\n".join(f"- {t}" for t in f2p[:10]))

    try:
        h = DeepSeekHarness()
    except HarnessError as e:
        print(json.dumps({"result": "error", "error": f"no_llm: {e}"}))
        return

    out = h.run_task(system, task, TOOLS, exec_fn,
                     max_turns=int(os.environ.get("MAX_TURNS", "20")))

    changed = bsh(f"cd {REPO} && git diff --name-only 2>/dev/null").strip()
    print("RESULT " + json.dumps({
        "result": "done", "turns": out["turns"], "status": out["status"],
        "files_changed": changed.splitlines()[:20],
        "fix_summary": (out["answer"] or "")[:600],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
