#!/usr/bin/env python3
"""agent2 验证驱动（CVM 中心化编排版）。

架构（修订版）：工具创建/销毁由 CVM 上的 tccli 执行，沙箱只与 CVM 通信
（E2B 数据面），CAM 凭据零进入沙箱：

    CVM 驱动器
     ├─ tccli CreateSandboxTool（每题临时工具 bench-u-<hash>，镜像=题目镜像）
     ├─ Sandbox.create（E2B API，内容已烧入镜像）
     ├─ Phase A：answer×N 轮 + baseline 负向（commands.run 从 CVM 下发）
     ├─ Phase B：DeepSeek Harness 解题（solver 在 CVM，工具调用→沙箱命令）
     ├─ Sandbox.kill
     └─ tccli DeleteSandboxTool（孤儿清扫 + 配额守卫）

吞吐约束（实测）：工具配额 10/账号，固定工具 1（bench-maker-ds）→ 并发临时
工具 ≤8；单题周期 ≈4-5min（建工具~25s+预热~60s+验证~2-3min+清理）。

用法：
  set -a; source deploy/.env; set +a
  python3 src/drivers/validator_driver.py --units-file output/maker/dataset.jsonl \
      [--phase-b] [--concurrency 3]
"""
import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "images", "dsharness", "agents"))
from dedup.claim import make_claim_store                             # noqa: E402
from dedup.dataset import CosShardWriter, LocalDataset               # noqa: E402
from deepseek_harness import DeepSeekHarness, HarnessError           # noqa: E402

from e2b.sandbox.commands.command_handle import CommandExitException

REGION = os.environ.get("TCR_REGION", "ap-singapore")
ROLE_ARN = os.environ.get("ROLE_ARN", "")
TOOL_PREFIX = "bench-u-"
VERDICT_RE = re.compile(r"VERDICT (\{.*\})")


# ─────────────────── 工具生命周期（tccli，CVM 执行） ───────────────────
def tccli(*args, timeout=180):
    return subprocess.run(["tccli", "ags", *args, "--region", REGION],
                          capture_output=True, text=True, timeout=timeout)


def list_tools():
    r = tccli("DescribeSandboxToolList")
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:])["SandboxToolSet"] if i >= 0 else []


def create_unit_tool(image_ref, tool_name):
    """创建每题临时工具（SANDBOX 隔离网络；镜像=题目镜像；envd 启动）。"""
    r = tccli("CreateSandboxTool", "--cli-unfold-argument",
              "--ToolName", tool_name, "--ToolType", "custom",
              "--NetworkConfiguration.NetworkMode", "SANDBOX",
              "--CustomConfiguration.Image", image_ref,
              "--CustomConfiguration.ImageRegistryType", "enterprise",
              "--CustomConfiguration.Command", "/usr/bin/envd",
              "--CustomConfiguration.Ports.0.Name", "envd",
              "--CustomConfiguration.Ports.0.Port", "49983",
              "--CustomConfiguration.Ports.0.Protocol", "TCP",
              "--CustomConfiguration.Probe.HttpGet.Path", "/health",
              "--CustomConfiguration.Probe.HttpGet.Port", "49983",
              "--CustomConfiguration.Probe.HttpGet.Scheme", "HTTP",
              "--CustomConfiguration.Probe.ReadyTimeoutMs", "30000",
              "--CustomConfiguration.Probe.ProbeTimeoutMs", "3000",
              "--CustomConfiguration.Probe.ProbePeriodMs", "3000",
              "--CustomConfiguration.Probe.SuccessThreshold", "1",
              "--CustomConfiguration.Probe.FailureThreshold", "100",
              "--CustomConfiguration.Resources.CPU", "1",
              "--CustomConfiguration.Resources.Memory", "2Gi",
              "--CustomConfiguration.Resources.Storage", "10Gi",
              "--RoleArn", ROLE_ARN, "--DefaultTimeout", "2h",
              "--Description", "ephemeral per-unit bench tool")
    if r.returncode != 0:
        raise RuntimeError(f"工具创建失败: {r.stderr[-200:]}")
    # 预热（内容层小，但基座层预热可大幅缩短实例冷启动）
    tccli("CreatePreCacheImageTask", "--cli-unfold-argument",
          "--Image", image_ref.split("@")[0], "--ImageRegistryType", "enterprise")
    return tool_name


def wait_tool_active(tool_name, deadline_s=300):
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        for t in list_tools():
            if t["ToolName"] == tool_name:
                if t["Status"] == "ACTIVE":
                    return True
                if t["Status"] == "FAILED":
                    raise RuntimeError(f"工具 {tool_name} 创建后 FAILED")
        time.sleep(8)
    raise TimeoutError(f"工具 {tool_name} 等待 ACTIVE 超时")


def delete_unit_tool(tool_name):
    for attempt in range(6):
        tid = next((t["ToolId"] for t in list_tools()
                    if t["ToolName"] == tool_name), None)
        if tid is None:
            return True        # 已不存在
        r = tccli("DeleteSandboxTool", "--ToolId", tid)
        if r.returncode == 0:
            return True
        if "ResourceInUse" in r.stderr:      # 残留实例占用 → 强杀后重试
            _kill_tool_instances(tool_name)
        time.sleep(10)
    return False


def _kill_tool_instances(tool_name):
    """通过 E2B 列出并杀掉全部残留实例（工具删除的前置条件，实测 ResourceInUse）。"""
    try:
        from e2b_code_interpreter import Sandbox
        pag = Sandbox.list()
        while True:
            items = pag.next_items()
            if not items:
                break
            for info in items:
                try:
                    Sandbox.connect(info.sandbox_id).kill()
                except Exception:
                    pass
            if not pag.has_next:
                break
    except Exception:
        pass


def sweep_orphan_tools(keep_batch=None):
    """孤儿工具清扫：回收非本批次/陈旧的 bench-u-* 临时工具（防崩溃残留占配额）。"""
    swept = 0
    for t in list_tools():
        if t["ToolName"].startswith(TOOL_PREFIX):
            try:
                ts = t.get("CreatedAt", "")
                if ts and time.time() - ts / 1000 < 3600:
                    continue          # 1h 内创建的不动（可能是并行批次）
                if delete_unit_tool(t["ToolName"]):
                    swept += 1
                    print(f"[sweep] 已回收孤儿工具 {t['ToolName']}")
            except Exception as e:
                print(f"[sweep] {t['ToolName']} 回收失败: {str(e)[:80]}")
    return swept


# ─────────────────── Phase A / Phase B（沙箱执行体驱动） ───────────────────
def sh_sbx(sb, cmd, timeout=900):
    try:
        return sb.commands.run(cmd, timeout=timeout, user="root")
    except CommandExitException as e:
        return e


def run_tests(sb, iid, flags: str):
    r = sh_sbx(sb, f"/benchmark/harness/run_tests.sh {iid} {flags}".strip(), timeout=1200)
    out = (r.stdout or "") + (r.stderr or "")
    try:
        start = out.rfind("\n{") + 1        # 行首 { 定位（防嵌套括号截断）
        data = json.loads(out[start:].strip())
        return data.get("fail_to_pass", {}), bool(data.get("all_passed"))
    except (ValueError, IndexError):
        return {"__harness__": "crash", "__raw__": out[-300:]}, False


def phase_a(sb, manifest, rounds_n):
    iid, f2p_ids = manifest["instance_id"], manifest["FAIL_TO_PASS"]
    rounds = [run_tests(sb, iid, "--reset --apply-tests --apply-golden")
              for _ in range(rounds_n)]
    if any(r[0].get("__harness__") for r in rounds):
        return {"result": "rejected", "reason": "harness_crash",
                "raw": str(rounds[0][0].get("__raw__"))[:200]}
    if not all(r[1] for r in rounds):
        return {"result": "rejected", "reason": "answer_not_all_passed"}
    if len({json.dumps(r[0], sort_keys=True) for r in rounds}) != 1:
        return {"result": "rejected", "reason": "answer_rounds_inconsistent"}
    base_f2p, _ = run_tests(sb, iid, "--reset --apply-tests")
    leaked = [k for k in f2p_ids if base_f2p.get(k) == "passed"]
    if leaked:
        return {"result": "rejected", "reason": f"baseline_leak: {leaked[:3]}"}
    return {"result": "validated", "rounds": rounds_n}


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


def phase_b(sb, manifest, max_turns=20):
    """DeepSeek 解题链：reset 到 base+tests → solver 循环 → 裸判定 resolved 率。"""
    iid = manifest["instance_id"]
    problem = manifest.get("problem_statement") or iid
    if os.path.exists(manifest.get("_problem_md", "")):
        problem = open(manifest["_problem_md"]).read()
    run_tests(sb, iid, "--reset --apply-tests")     # 起点：base+tests，无 golden

    def exec_fn(name, args):
        repo = f"/benchmark/repos/{manifest['repo'].replace('/', '__')}"
        if name == "run_command":
            r = sh_sbx(sb, f"cd {repo} && {args['command']}", timeout=600)
            return ((r.stdout or "") + (r.stderr or ""))[:8000]
        if name == "read_file":
            r = sh_sbx(sb, f"cat {repo}/{args['path']}", timeout=60)
            return (r.stdout or "")[:16000]
        if name == "write_file":
            sb.files.write(f"{repo}/{args['path']}", args["content"], user="root")
            return f"written {len(args['content'])} bytes"
        return f"unknown tool {name}"

    system = ("你是一名资深 Python 工程师，在仓库中修复一个 bug。\n"
              "执行命令的方式：输出 <execute command=\"你的命令\"/>\n"
              "流程建议：先 cat/grep 探索相关代码 → 运行评分测试复现失败 → "
              "定位根因 → 用命令修改文件（如 python -c 或 sed）实施最小修复 → "
              "再次运行相关测试确认通过 → 最后输出简要修复说明（不再执行命令）。")
    task = (f"【任务】修复以下问题并让指定测试通过。\n\n{problem}\n\n"
            f"【通过的判据】这些测试全部通过即算成功：\n"
            + "\n".join(f"- {t}" for t in manifest["FAIL_TO_PASS"][:10]))
    try:
        h = DeepSeekHarness()
    except HarnessError as e:
        return {"result": "skipped", "reason": f"no_llm: {e}"}
    out = h.run_task(system, task, SOLVER_TOOLS, exec_fn, max_turns=max_turns)

    f2p_map, all_ok = run_tests(sb, iid, "")       # 裸判定：当前状态直接跑
    passed = sum(1 for v in f2p_map.values() if v == "passed")
    total = len(manifest["FAIL_TO_PASS"])
    return {"result": "solved" if all_ok else "unsolved",
            "resolved_ratio": round(passed / total, 3) if total else 0,
            "f2p_passed": f"{passed}/{total}", "solver_turns": out["turns"],
            "solver_status": out["status"],
            "fix_summary": (out["answer"] or "")[:400]}


# ─────────────────── 单元验证编排 ───────────────────
async def validate_unit(sem, rec, results, phase_b_on, rounds):
    """一个单元的完整验证：建工具→实例→Phase A/B→销毁。受全局信号量背压。"""
    iid = rec["instance_id"]
    image = rec.get("image")
    digest = rec.get("image_digest", "")
    if not image or not digest.startswith("sha256:"):
        print(f"[{time.strftime('%H:%M:%S')}] [{iid}] ⏭ 无镜像记录（旧模式产物），跳过")
        return "skipped"
    image_ref = f"{image}@{digest}"
    tool_name = TOOL_PREFIX + re.sub(r"[^a-z0-9-]", "-", iid.lower())[:40]

    async with sem:
        from e2b_code_interpreter import Sandbox
        sb = None
        verdict = {"instance_id": iid}
        try:
            # ① CVM: tccli 建工具 + 预热 + 等 ACTIVE
            create_unit_tool(image_ref, tool_name)
            wait_tool_active(tool_name)
            print(f"[{time.strftime('%H:%M:%S')}] [{iid}] 临时工具 {tool_name} ACTIVE")
            # ② 实例（内容已烧入镜像）
            sb = Sandbox.create(template=tool_name, timeout=1800)
            # ③ Phase A
            verdict["phase_a"] = phase_a(sb, rec, rounds)
            print(f"[{time.strftime('%H:%M:%S')}] [{iid}] Phase A: {verdict['phase_a'].get('result')}")
            # ④ Phase B（可选）
            if phase_b_on and verdict["phase_a"]["result"] == "validated":
                verdict["phase_b"] = phase_b(sb, rec)
                print(f"[{time.strftime('%H:%M:%S')}] [{iid}] Phase B: {verdict['phase_b'].get('result')} "
                      f"({verdict['phase_b'].get('f2p_passed')})")
        except Exception as e:
            verdict["error"] = f"{type(e).__name__}: {str(e)[:200]}"
            print(f"[{time.strftime('%H:%M:%S')}] [{iid}] ❌ {verdict['error']}")
        finally:
            if sb is not None:
                try:
                    sb.kill()
                except Exception:
                    pass
            ok = delete_unit_tool(tool_name)      # ⑤ CVM: tccli 删工具
            print(f"[{time.strftime('%H:%M:%S')}] [{iid}] 工具{'已删' if ok else '删除失败(留待清扫)'}")
        results.append(verdict)
        return verdict.get("phase_a", {}).get("result", "error")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units-file", default="output/maker/dataset.jsonl")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--phase-b", action="store_true", help="启用 Phase B（DeepSeek 解题）")
    ap.add_argument("--concurrency", type=int, default=3, help="并发临时工具数（配额内 ≤8）")
    ap.add_argument("--claims", default="output/validate-claims.json")
    ap.add_argument("--results", default="output/validate-results.jsonl")
    ap.add_argument("--no-sweep", action="store_true")
    args = ap.parse_args()

    for k in ("E2B_DOMAIN", "E2B_API_KEY", "ROLE_ARN"):
        if not os.environ.get(k):
            sys.exit(f"缺少环境变量: {k}（ROLEArn 为工具创建所需 CAM 角色）")

    recs = [json.loads(l) for l in open(args.units_file) if l.strip()]
    # 附带 problem.md 路径（Phase B 题面）
    for r in recs:
        p = os.path.join("output/maker/units", r["instance_id"], r["instance_id"], "problem.md")
        if os.path.exists(p):
            r["_problem_md"] = p
    print(f"[{time.strftime('%H:%M:%S')}] [validate] {len(recs)} 个单元 | 并发 {args.concurrency} | "
          f"Phase B {'开' if args.phase_b else '关'}")

    if not args.no_sweep:
        sweep_orphan_tools()

    claim = make_claim_store(None, path=args.claims, bucket="",
                            prefix="validate/claims")
    results = LocalDataset(args.results)
    sem = asyncio.Semaphore(min(args.concurrency, 8))

    async def _one(r):
        key = f"validate/{r['instance_id']}"
        ok, _ = await asyncio.to_thread(claim.claim, key, {"stage": "per-unit-tool"})
        if not ok:
            print(f"[{r['instance_id']}] L1 拦截（已验证过）")
            return "blocked"
        st = await validate_unit(sem, r, results, args.phase_b, args.rounds)
        await asyncio.to_thread(claim.finish, key,
                                 "done" if st in ("validated", "rejected") else "failed", st)
        return st

    outs = await asyncio.gather(*[_one(r) for r in recs])
    from collections import Counter
    print(f"\n[{time.strftime('%H:%M:%S')}] [validate] 完成: {dict(Counter(outs))}")


if __name__ == "__main__":
    asyncio.run(main())
