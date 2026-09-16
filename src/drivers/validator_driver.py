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


# ─────────────────── Phase A / agent 解题（沙箱执行体驱动） ───────────────────
def sh_sbx(sb, cmd, timeout=900, envs=None):
    try:
        return sb.commands.run(cmd, timeout=timeout, user="root", envs=envs)
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


# ─────────────────── agent 解题阶段（沙箱互访 + pass@1） ───────────────────
AGENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                         "images", "dsharness", "agents")
AGENT_TOOL = os.environ.get("AGENT_TOOL", "bench-solver")


def acquire_instance_token(instance_id):
    """实例级访问 Token（AGS 官方互访机制：AcquireSandboxInstanceToken，~24h）。

    该 Token 即 envd 层 X-Access-Token 凭证（与 SDK connect 换回的
    envd_access_token 同源，实测），agent 沙箱凭它直访 bench 沙箱。
    """
    r = tccli("AcquireSandboxInstanceToken", "--InstanceId", instance_id)
    if r.returncode != 0 or "Token" not in r.stdout:
        raise RuntimeError(f"获取实例 Token 失败: {r.stderr[-150:] or r.stdout[-150:]}")
    return json.loads(r.stdout)["Token"]


def phase_agent(agent_sb, bench_sb, rec):
    """独立 agent 沙箱解题（经 sit Token 直访 bench 沙箱），返回 pass@1 结果。

    流程：上传 solver → envs 注入 Token/题面/F2P → agent 沙箱内运行
    solver_agent.py（monkey-patch e2b + 直连 bench）→ CVM 在 bench 上
    裸判定（solver 已将仓库置于其修复后状态）。
    """
    iid = rec["instance_id"]
    sit = acquire_instance_token(bench_sb.sandbox_id)
    for fn in ("solver_agent.py", "deepseek_harness.py"):
        agent_sb.files.write(f"/opt/solver/{fn}",
                             open(os.path.join(AGENTS_DIR, fn)).read(), user="root")
    problem = rec.get("problem") or iid
    if rec.get("_problem_md") and os.path.exists(rec["_problem_md"]):
        problem = open(rec["_problem_md"]).read()
    envs = {
        "BENCH_SIT_TOKEN": sit, "BENCH_SANDBOX_ID": bench_sb.sandbox_id,
        "E2B_DOMAIN": os.environ["E2B_DOMAIN"], "INSTANCE_ID": iid,
        "REPO": rec["repo"], "PROBLEM": problem[:12000],
        "F2P_TESTS": "\n".join(rec["FAIL_TO_PASS"]),
        "MAX_TURNS": os.environ.get("AGENT_MAX_TURNS", "20"),
    }
    for k in ("OPENAI_BASE_URL", "OPENAI_API_KEY", "LLM_MODEL"):
        if os.environ.get(k):
            envs[k] = os.environ[k]
    r = sh_sbx(agent_sb, "python3 /opt/solver/solver_agent.py",
               timeout=3600, envs=envs)
    out = (r.stdout or "") + "\n" + (r.stderr or "")
    m = re.findall(r"RESULT (\{.*\})", out)
    solver = json.loads(m[-1]) if m else {"result": "error", "error": out[-300:]}

    # ★ LLM 使用证据收集：完整对话轨迹落盘（agent 沙箱 → CVM 审计档案）
    tr = sh_sbx(agent_sb, "base64 -w0 /output/transcript.json 2>/dev/null", timeout=120)
    if (tr.stdout or "").strip():
        try:
            import base64 as _b64
            transcript = json.loads(_b64.b64decode((tr.stdout or "").strip()))
            os.makedirs("output/validate-transcripts", exist_ok=True)
            with open(f"output/validate-transcripts/{iid}.json", "w") as f:
                json.dump(transcript, f, ensure_ascii=False, indent=1)
            solver["llm_evidence"] = (f"model={transcript.get('model')} "
                                     f"turns={transcript.get('turns')} "
                                     f"transcript_bytes={len((tr.stdout or ''))}")
        except Exception as e:
            solver["llm_evidence"] = f"collect_failed: {str(e)[:80]}"

    f2p_map, all_ok = run_tests(bench_sb, iid, "")     # pass@1 裸判定
    passed = sum(1 for v in f2p_map.values() if v == "passed")
    total = len(rec["FAIL_TO_PASS"])
    solver["pass_at_1"] = bool(all_ok)
    solver["f2p_passed"] = f"{passed}/{total}"
    return solver


def analyze_failure(bench_sb, rec, agent_out):
    """agent 答案错误时的对比分析：agent 修改 vs 标准答案 + 失败清单 + LLM 归因。"""
    iid = rec["instance_id"]
    repo = f"/benchmark/repos/{rec['repo'].replace('/', '__')}"
    agent_diff = (sh_sbx(bench_sb, f"cd {repo} && git diff", timeout=120).stdout or "")[:6000]
    f2p_map, _ = run_tests(bench_sb, iid, "")
    failed = [k.split("::")[-1][:60] for k, v in f2p_map.items() if v != "passed"][:10]
    golden = (rec.get("golden_patch") or "")[:4000]
    analysis = {
        "failed_tests": failed,
        "agent_touched": agent_out.get("files_changed", [])[:10],
        "agent_diff_lines": len(agent_diff.splitlines()),
        "golden_diff_lines": len(golden.splitlines()),
    }
    try:
        h = DeepSeekHarness()
        task = (f"【agent 尝试的修复 diff】\n{agent_diff or '(无任何修改)'}\n\n"
                f"【标准答案 diff（golden patch）】\n{golden or '(空)'}\n\n"
                f"【agent 修复后仍未通过的测试】\n" + "\n".join(f"- {t}" for t in failed) +
                "\n\n请从三个维度分析：① agent 是否定位到了正确根因；"
                "② 与标准答案的差距本质（方向性错误/边界遗漏/精度不足）；"
                "③ 该题难度评级（简单/中等/困难）。200 字内。")
        out = h.run_task("你是资深代码评审专家，对比分析两个修复尝试的差异。",
                         task, [], lambda n, a: "", max_turns=1)
        analysis["llm_analysis"] = (out.get("answer") or "")[:800]
    except Exception as e:
        analysis["llm_analysis"] = f"unavailable: {str(e)[:100]}"
    return analysis


# ─────────────────── 单元验证编排 ───────────────────
async def validate_unit(sem, rec, results, agent_on, rounds):
    """一个单元的完整核验（v2 双沙箱）：
    建临时工具 → bench 实例 → agent 实例 → ①agent 解题(pass@1)
    → ②标准答案核验(Phase A) → ③agent 答错时对比分析 → 销毁。
    每题同时占用 2 个实例（agent + bench），受全局信号量背压。
    """
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
        sb = agent_sb = None
        verdict = {"instance_id": iid}
        try:
            # ① CVM: tccli 建工具 + 预热 + 等 ACTIVE；拉起 bench 实例（题目烧入）
            create_unit_tool(image_ref, tool_name)
            wait_tool_active(tool_name)
            sb = Sandbox.create(template=tool_name, timeout=3600)
            print(f"[{time.strftime('%H:%M:%S')}] [{iid}] bench 实例就绪")

            # ② agent 沙箱（独立实例）解题 → pass@1
            if agent_on:
                agent_sb = Sandbox.create(template=AGENT_TOOL, timeout=3600)
                verdict["agent"] = phase_agent(agent_sb, sb, rec)
                print(f"[{time.strftime('%H:%M:%S')}] [{iid}] agent 解题: "
                      f"pass@1={'✅' if verdict['agent'].get('pass_at_1') else '❌'} "
                      f"({verdict['agent'].get('f2p_passed')}, "
                      f"{verdict['agent'].get('turns')} 轮)")
                agent_sb.kill()
                agent_sb = None

            # ③ 标准答案核验（原流程：answer×N 轮一致 + baseline 负向）
            verdict["phase_a"] = phase_a(sb, rec, rounds)
            print(f"[{time.strftime('%H:%M:%S')}] [{iid}] Phase A: "
                  f"{verdict['phase_a'].get('result')}")

            # ④ agent 答案错误 → 对比分析（agent 修改 vs 标准答案）
            if agent_on and not verdict.get("agent", {}).get("pass_at_1"):
                verdict["failure_analysis"] = analyze_failure(sb, rec, verdict["agent"])
                print(f"[{time.strftime('%H:%M:%S')}] [{iid}] 失败分析: "
                      f"{verdict['failure_analysis'].get('llm_analysis', '')[:80]}")
        except Exception as e:
            verdict["error"] = f"{type(e).__name__}: {str(e)[:200]}"
            print(f"[{time.strftime('%H:%M:%S')}] [{iid}] ❌ {verdict['error']}")
        finally:
            for x in (sb, agent_sb):
                if x is not None:
                    try:
                        x.kill()
                    except Exception:
                        pass
            ok = delete_unit_tool(tool_name)      # CVM: tccli 删工具（配额归还）
            print(f"[{time.strftime('%H:%M:%S')}] [{iid}] 工具{'已删' if ok else '删除失败(留待清扫)'}")
        results.append(verdict)
        return verdict.get("phase_a", {}).get("result", "error")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units-file", default="output/maker/dataset.jsonl")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--no-agent", action="store_true",
                    help="跳过 agent 解题阶段（仅标准答案核验）")
    ap.add_argument("--concurrency", type=int, default=3, help="并发临时工具数（配额内 ≤8）")
    ap.add_argument("--claims", default="output/validate-claims.json")
    ap.add_argument("--results", default="output/validate-results.jsonl")
    ap.add_argument("--no-sweep", action="store_true")
    args = ap.parse_args()

    for k in ("E2B_DOMAIN", "E2B_API_KEY", "ROLE_ARN"):
        if not os.environ.get(k):
            sys.exit(f"缺少环境变量: {k}（ROLEArn 为工具创建所需 CAM 角色）")

    recs = [json.loads(l) for l in open(args.units_file) if l.strip()]
    for r in recs:                                   # 附带 problem.md 路径（题面）
        p = os.path.join("output/maker/units", r["instance_id"], r["instance_id"], "problem.md")
        if os.path.exists(p):
            r["_problem_md"] = p
    print(f"[{time.strftime('%H:%M:%S')}] [validate] {len(recs)} 个单元 | 并发 {args.concurrency} | "
          f"agent 解题 {'关' if args.no_agent else '开'} | 模式：双沙箱（agent + bench）")

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
        st = await validate_unit(sem, r, results, not args.no_agent, args.rounds)
        await asyncio.to_thread(claim.finish, key,
                                 "done" if st in ("validated", "rejected") else "failed", st)
        return st

    outs = await asyncio.gather(*[_one(r) for r in recs])
    from collections import Counter
    print(f"\n[{time.strftime('%H:%M:%S')}] [validate] 完成: {dict(Counter(outs))}")


if __name__ == "__main__":
    asyncio.run(main())
