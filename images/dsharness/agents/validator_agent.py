#!/usr/bin/env python3
"""agent2（DeepSeek Harness 版）：跨 AGS 验证器，Phase A + Phase B。

Phase A（确定性，无需 LLM）：数据集自检
  answer ×N 轮一致（F2P 全过）+ baseline 负向对照（F2P 全 FAIL）

Phase B（DeepSeek Harness，需 OPENAI_*）：Agent 可解性验证
  题目沙箱重置为 base+tests（无 golden）→ solver 工具循环解题 →
  裸调用 harness 判定当前状态（不 reset）→ resolved 率

运行环境：validator 沙箱（PUBLIC 网络，内置 e2b SDK）；
题目沙箱：BENCH_TOOL（SANDBOX 隔离，内容注入）。
凭据最小化：本沙箱仅持 E2B_API_KEY + LLM key（命令级注入）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deepseek_harness import DeepSeekHarness, HarnessError          # noqa: E402

from e2b_code_interpreter import Sandbox
from e2b.sandbox.commands.command_handle import CommandExitException

WORK, OUT = "/work", "/output"


def sh(bench, cmd, timeout=900):
    try:
        return bench.commands.run(cmd, timeout=timeout, user="root")
    except CommandExitException as e:
        return e


def inject_bundle(bench, manifest):
    """内容注入 + 离线可跑化（.pth 站点链接，无网络依赖）。

    两个关键修复（实测）：
    ① pip 依赖遮蔽：pytest 等工具依赖的同名包（如 packaging）装在 dist-packages，
       .pth 追加在其后会被遮蔽 → 注入时卸载同名 pip 包，使仓库源码成为唯一来源
    ② manifest 显式拷贝至 /benchmark/（harness 的 jq 读取路径）
    """
    safe = manifest["repo"].replace("/", "__")
    repo_name = manifest["repo"].split("/")[-1]
    for fn in ("repo.tar.gz", "tests.patch", "golden.patch", "manifest.jsonl", "problem.md"):
        src = f"{WORK}/{fn}"
        if os.path.exists(src):
            with open(src, "rb") as f:
                bench.files.write(f"/tmp/{fn}", f.read(), user="root")
    sh(bench, f"mkdir -p /benchmark/repos && "
              f"tar -xzf /tmp/repo.tar.gz -C /benchmark/repos/ && "
              f"cp /tmp/tests.patch /tmp/golden.patch /tmp/manifest.jsonl /benchmark/ && "
              f"pip3 uninstall -y {repo_name} >/dev/null 2>&1 || true")   # 修复①
    repo_dir = f"/benchmark/repos/{safe}"
    # 离线 import：src/ 或根布局 → .pth 站点链接（无构建、无网络）
    sh(bench, f"SRC=$(ls -d {repo_dir}/src 2>/dev/null || echo {repo_dir}) && "
              f"echo $SRC > $(python3 -c 'import site;print(site.getsitepackages()[0])')"
              f"/bench_repo.pth && python3 -c 'import {repo_name} as m; "
              f"print(\"repo import:\", m.__file__[:70])'")
    m = dict(manifest)
    m["test_patch"], m["golden_patch"] = "/benchmark/tests.patch", "/benchmark/golden.patch"
    bench.files.write("/benchmark/manifest.jsonl",
                      json.dumps(m, ensure_ascii=False), user="root")   # 修复②：路径修正版
    return repo_dir


def run_tests(bench, iid, flags: str):
    r = sh(bench, f"/benchmark/harness/run_tests.sh {iid} {flags}".strip(), timeout=1200)
    out = (r.stdout or "") + (r.stderr or "")
    # 汇总 JSON 的 `{` 位于行首；fail_to_pass 等嵌套 `{` 为缩进内层——
    # 用「最后一个行首 {」定位，规避嵌套括号截断（实测 bug：rfind("{") 抓到内层）
    try:
        start = out.rfind("\n{") + 1
        data = json.loads(out[start:].strip())
        return data.get("fail_to_pass", {}), bool(data.get("all_passed"))
    except (ValueError, IndexError):
        print("RAW_OUT>>>" + out[-400:])
        return {"__harness__": "crash"}, False


def phase_a(bench, manifest, rounds_n):
    iid, f2p_ids = manifest["instance_id"], manifest["FAIL_TO_PASS"]
    rounds = [run_tests(bench, iid, "--reset --apply-tests --apply-golden")
              for _ in range(rounds_n)]
    if any(r[0].get("__harness__") for r in rounds):
        return {"result": "rejected", "reason": "harness_crash"}
    if not all(r[1] for r in rounds):
        return {"result": "rejected", "reason": "answer_not_all_passed"}
    if len({json.dumps(r[0], sort_keys=True) for r in rounds}) != 1:
        return {"result": "rejected", "reason": "answer_rounds_inconsistent"}
    base_f2p, _ = run_tests(bench, iid, "--reset --apply-tests")
    leaked = [k for k in f2p_ids if base_f2p.get(k) == "passed"]
    if leaked:
        return {"result": "rejected", "reason": f"baseline_leak: {leaked[:3]}"}
    return {"result": "validated", "rounds": rounds_n}


# ---------------- Phase B：DeepSeek Harness 解题链 ----------------
SOLVER_TOOLS = [
    {"type": "function", "function": {
        "name": "run_command",
        "description": "在题目仓库内执行 shell 命令（查看代码/跑测试/任意操作）",
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
            "required": ["path", "content"]}}}]


def phase_b(bench, manifest, repo_dir, max_turns=20):
    """解题链：base+tests 起步 → solver 循环 → 裸判定 resolved 率。"""
    iid = manifest["instance_id"]
    problem = open(f"{WORK}/problem.md").read() if os.path.exists(f"{WORK}/problem.md") \
        else manifest.get("problem_statement", iid)
    run_tests(bench, iid, "--reset --apply-tests")     # 起点：base+tests，无 golden

    def exec_fn(name, args):
        if name == "run_command":
            r = sh(bench, f"cd {repo_dir} && {args['command']}", timeout=600)
            return ((r.stdout or "") + (r.stderr or ""))[:8000]
        if name == "read_file":
            r = sh(bench, f"cat {repo_dir}/{args['path']}", timeout=60)
            return (r.stdout or "")[:16000]
        if name == "write_file":
            bench.files.write(f"{repo_dir}/{args['path']}", args["content"], user="root")
            return f"written {len(args['content'])} bytes"
        return f"unknown tool {name}"

    try:
        h = DeepSeekHarness()
    except HarnessError as e:
        return {"result": "skipped", "reason": f"no_llm: {e}"}

    system = ("你是一名资深 Python 工程师，在仓库中修复一个 bug。\n"
              "执行命令的方式：输出 <execute command=\"你的命令\"/>\n"
              "流程建议：先 cat/grep 探索相关代码 → 运行评分测试复现失败 → "
              "定位根因 → 用命令修改文件（如 python -c 或 sed）实施最小修复 → "
              "再次运行相关测试确认通过 → 最后输出简要修复说明（不再执行命令）。")
    task = (f"【任务】修复以下问题并让指定测试通过。\n\n{problem}\n\n"
            f"【通过的判据】这些测试全部通过即算成功：\n"
            + "\n".join(f"- {t}" for t in manifest["FAIL_TO_PASS"][:10]))
    out = h.run_task(system, task, SOLVER_TOOLS, exec_fn, max_turns=max_turns)

    # 裸判定：当前（solver 修改后的）仓库状态直接跑套件，不 reset
    f2p_map, all_ok = run_tests(bench, iid, "")
    passed = sum(1 for v in f2p_map.values() if v == "passed")
    total = len(manifest["FAIL_TO_PASS"])
    return {"result": "solved" if all_ok else "unsolved",
            "resolved_ratio": round(passed / total, 3) if total else 0,
            "f2p_passed": f"{passed}/{total}", "solver_turns": out["turns"],
            "solver_status": out["status"],
            "fix_summary": (out["answer"] or "")[:400]}


def main():
    manifest = json.loads(open(f"{WORK}/manifest.jsonl").read().strip())
    iid = manifest["instance_id"]
    rounds_n = int(os.environ.get("VERIFY_ROUNDS", "2"))
    do_phase_b = os.environ.get("PHASE_B", "0") == "1"

    bench = None
    verdict = {"instance_id": iid, "phase_a": {"result": "error"}}
    try:
        bench = Sandbox.create(template=os.environ["BENCH_TOOL"], timeout=3600)
        repo_dir = inject_bundle(bench, manifest)
        verdict["phase_a"] = phase_a(bench, manifest, rounds_n)
        if do_phase_b and verdict["phase_a"]["result"] == "validated":
            verdict["phase_b"] = phase_b(bench, manifest, repo_dir)
    except Exception as e:
        verdict["error"] = str(e)[:300]
    finally:
        if bench is not None:
            try:
                bench.kill()
            except Exception:
                pass

    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/verdict.json", "w").write(json.dumps(verdict, ensure_ascii=False))
    print("VERDICT " + json.dumps(verdict, ensure_ascii=False))
    ok = verdict["phase_a"]["result"] == "validated"
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
