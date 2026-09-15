#!/usr/bin/env python3
"""agent2：跨 AGS 验证器（运行于 validator 沙箱实例内）。

职责（Phase A 数据集自检，判定协议与主项目 validate_ags.py 完全一致）：
  1. 读取注入的单元包（/work/：manifest.jsonl + tests.patch + golden.patch + repo.tar.gz）
  2. 通过 E2B API 在【另一个 AGS 实例】拉起题目沙箱（BENCH_TOOL 基座 + 内容注入）
  3. 注入题目内容（files API，KB-MB 级，SANDBOX 隔离网络下控制面仍可达）
  4. answer ×N 轮一致性（reset+tests+golden → F2P 全过）+ baseline 负向对照（F2P 全 FAIL）
  5. 输出 verdict JSON，销毁题目沙箱

凭据最小化：本 agent 只需 E2B_API_KEY（数据面）；COS/TCR 凭据不进入本沙箱。

环境变量（驱动方经 commands.run(envs=...) 命令级注入）：
  E2B_API_KEY / E2B_DOMAIN —— 数据面凭据与域名
  BENCH_TOOL               —— 题目基座沙箱工具名（内容注入模式）
  VERIFY_ROUNDS            —— answer 一致性轮数（默认 2）
"""
import json
import os
import sys

from e2b_code_interpreter import Sandbox
from e2b.sandbox.commands.command_handle import CommandExitException

WORK = "/work"
OUT = "/output"


def sh(sb, cmd, timeout=600):
    try:
        return sb.commands.run(cmd, timeout=timeout, user="root")
    except CommandExitException as e:
        return e


def run_tests(bench, instance_id, golden: bool, seq: str):
    """调用题目沙箱 harness，返回 (fail_to_pass 明细, all_passed)。"""
    flags = "--reset --apply-tests" + (" --apply-golden" if golden else "")
    r = sh(bench, f"/benchmark/harness/run_tests.sh {instance_id} {flags}", timeout=1200)
    out = (r.stdout or "") + (r.stderr or "")
    try:
        data = json.loads(out[out.rfind("{"):out.rfind("}") + 1])
        return data.get("fail_to_pass", {}), bool(data.get("all_passed"))
    except (ValueError, IndexError):
        return {"__harness__": "crash"}, False


def main():
    manifest = json.loads(open(f"{WORK}/manifest.jsonl").read().strip())
    iid = manifest["instance_id"]
    f2p_ids = manifest["FAIL_TO_PASS"]
    rounds_n = int(os.environ.get("VERIFY_ROUNDS", "2"))

    bench = None
    verdict = {"instance_id": iid, "result": "error"}
    try:
        # ── ① 跨 AGS：拉起题目沙箱（独立实例，SANDBOX 隔离网络）──
        bench = Sandbox.create(template=os.environ["BENCH_TOOL"], timeout=1800)

        # ── ② 内容注入（files 控制面不受数据面网络隔离影响）──
        for fn in ("repo.tar.gz", "tests.patch", "golden.patch"):
            with open(f"{WORK}/{fn}", "rb") as f:
                bench.files.write(f"/tmp/{fn}", f.read(), user="root")
        sh(bench, f"mkdir -p /benchmark/repos && "
                  f"tar -xzf /tmp/repo.tar.gz -C /benchmark/repos/ && "
                  f"cp /tmp/tests.patch /tmp/golden.patch /benchmark/ && "
                  f"cp {WORK}/manifest.jsonl /benchmark/manifest.jsonl", timeout=300)
        # manifest 中补丁/仓库路径指向注入位置
        m = dict(manifest)
        m["test_patch"], m["golden_patch"] = "/benchmark/tests.patch", "/benchmark/golden.patch"
        bench.files.write("/benchmark/manifest.jsonl",
                          json.dumps(m, ensure_ascii=False), user="root")

        # ── ③ answer ×N 轮一致性 ──
        rounds = []
        for i in range(rounds_n):
            rounds.append(run_tests(bench, iid, golden=True, seq=f"a{i}"))
        if any(r[0].get("__harness__") for r in rounds):
            verdict = {"instance_id": iid, "result": "rejected",
                       "reason": "harness_crash"}
        elif not all(r[1] for r in rounds):        # all_passed 必须 N 轮全真
            fails = [k for k in f2p_ids
                     for r in rounds if r[0].get(k) != "passed"]
            verdict = {"instance_id": iid, "result": "rejected",
                       "reason": f"answer_not_all_passed: {fails[:3]}"}
        elif len({json.dumps(r[0], sort_keys=True) for r in rounds}) != 1:
            verdict = {"instance_id": iid, "result": "rejected",
                       "reason": "answer_rounds_inconsistent"}
        else:
            # ── ④ baseline 负向对照：F2P 必须 FAIL ──
            base_f2p, _ = run_tests(bench, iid, golden=False, seq="b0")
            leaked = [k for k in f2p_ids if base_f2p.get(k) == "passed"]
            verdict = ({"instance_id": iid, "result": "validated",
                        "f2p": len(f2p_ids), "p2p": len(manifest.get("PASS_TO_PASS", [])),
                        "rounds": rounds_n}
                       if not leaked else
                       {"instance_id": iid, "result": "rejected",
                        "reason": f"baseline_leak: {leaked[:3]}"})
    except Exception as e:
        verdict = {"instance_id": iid, "result": "error", "error": str(e)[:300]}
    finally:
        if bench is not None:
            try:
                bench.kill()       # 题目沙箱必销毁（用完即弃，无状态）
            except Exception:
                pass

    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/verdict.json", "w").write(json.dumps(verdict, ensure_ascii=False))
    print("VERDICT " + json.dumps(verdict, ensure_ascii=False))
    sys.exit(0 if verdict["result"] in ("validated", "rejected") else 1)


if __name__ == "__main__":
    main()
