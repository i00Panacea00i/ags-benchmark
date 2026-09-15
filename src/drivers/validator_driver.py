#!/usr/bin/env python3
"""agent2 池化批量驱动：跨 AGS 验证的无状态编排器。

数据流（对应 docs/ARCHITECTURE.md 图 3-2）：
  单元包清单 → L1 claim（去重）→ validator 池 acquire → 注入单元包 →
  agent2 沙箱内跨 AGS 拉起题目沙箱并验证 → verdict 回读 → L2 分片写入 → release

无状态：本驱动可在任意机器/K8s Pod 并行多副本启动，互斥与去重由
claim/dataset 后端保证（flock=单机，cos=多副本），本地不保留跨运行状态。

用法：
  set -a; source deploy/.env; set +a
  python3 src/drivers/validator_driver.py \
      --bundles-dir output/builder/units --batch b001 --worker w1 \
      [--concurrency 8 --warm 3]
"""
import argparse
import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from pool.sandbox_pool import SandboxPool                    # noqa: E402
from dedup.claim import make_claim_store                     # noqa: E402
from dedup.dataset import CosShardWriter, LocalDataset       # noqa: E402

from e2b.sandbox.commands.command_handle import CommandExitException

VERDICT_RE = re.compile(r"VERDICT (\{.*\})")


async def run_remote(sb, cmd, timeout, envs=None):
    try:
        return await sb.commands.run(cmd, timeout=timeout, user="root", envs=envs)
    except CommandExitException as e:
        return e


async def validate_unit(pool, claim, results, bundles_dir, instance_id, cfg):
    key = f"validate/{instance_id}"
    ok, rec = await asyncio.to_thread(claim.claim, key, {"stage": "phase-a"})
    if not ok:
        print(f"[{instance_id}] L1 拦截：已是 {rec.get('state')}")
        return "blocked"
    bundle = os.path.join(bundles_dir, instance_id, instance_id)
    if not os.path.isdir(bundle):
        await asyncio.to_thread(claim.finish, key, "failed", "bundle_missing")
        return "missing"

    handle = await pool.acquire()
    try:
        # 单元包上传（驱动方持有文件；沙箱只需 E2B 凭据，凭据面最小化）
        await handle.sb.commands.run("mkdir -p /work /output", timeout=30, user="root")
        for fn in ("manifest.jsonl", "tests.patch", "golden.patch", "repo.tar.gz"):
            with open(os.path.join(bundle, fn), "rb") as f:
                await handle.sb.files.write(f"/work/{fn}", f.read(), user="root")
        envs = {"E2B_API_KEY": os.environ["E2B_API_KEY"],
                "E2B_DOMAIN": os.environ.get("E2B_DOMAIN", ""),
                "BENCH_TOOL": cfg["bench_tool"],
                "VERIFY_ROUNDS": str(cfg["rounds"])}
        r = await run_remote(handle.sb, "python3 /opt/validator/validator_agent.py",
                             timeout=2400, envs=envs)
        m = VERDICT_RE.search((r.stdout or "") + (r.stderr or ""))
        verdict = json.loads(m.group(1)) if m else \
            {"instance_id": instance_id, "result": "error",
             "error": (r.stdout or "")[-200:]}
        print(f"[{instance_id}] verdict: {json.dumps(verdict, ensure_ascii=False)[:120]}")
        dup = results.is_dup(verdict)
        if dup:
            await asyncio.to_thread(claim.finish, key, "done", f"dup: {dup}")
            return "dup"
        await asyncio.to_thread(results.append, verdict)
        state = "done" if verdict["result"] in ("validated", "rejected") else "failed"
        await asyncio.to_thread(claim.finish, key, state,
                                verdict.get("reason") or verdict["result"])
        return verdict["result"]
    except Exception as e:
        await asyncio.to_thread(claim.finish, key, "failed", f"驱动异常: {str(e)[:120]}")
        return "crash"
    finally:
        await pool.release(handle)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundles-dir", required=True, help="单元包根目录（含 <id>/<id>/）")
    ap.add_argument("--batch", default="b001")
    ap.add_argument("--worker", default=os.uname().nodename)
    ap.add_argument("--validator-tool", default=os.environ.get("VALIDATOR_TOOL", "bench-validator"))
    ap.add_argument("--bench-tool", default=os.environ.get("BENCH_TOOL", "bench-base"))
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--warm", type=int, default=3)
    ap.add_argument("--claims", default="output/validate-claims.json")
    ap.add_argument("--results", default=None, help="默认 output/validate-results.jsonl")
    args = ap.parse_args()

    for k in ("E2B_DOMAIN", "E2B_API_KEY"):
        if not os.environ.get(k):
            sys.exit(f"缺少环境变量: {k}")

    units = [d for d in os.listdir(args.bundles_dir)
             if os.path.isdir(os.path.join(args.bundles_dir, d, d))]
    print(f"[validate] {len(units)} 个单元包 | validator={args.validator_tool} "
          f"| bench={args.bench_tool} | 并发 {args.concurrency}")

    claim = await asyncio.to_thread(
        make_claim_store, None,
        **{"path": args.claims,
           "bucket": os.environ.get("COS_BUCKET", ""),
           "prefix": f"validate/{args.batch}/claims"})
    if os.environ.get("CLAIM_BACKEND") == "cos":
        results = CosShardWriter(os.environ["COS_BUCKET"], args.batch, args.worker,
                                 prefix=f"validate/{args.batch}")
    else:
        results = LocalDataset(args.results or "output/validate-results.jsonl")

    concurrency = min(args.concurrency, 40)   # 标定上限（见 ARCHITECTURE.md §6）
    pool = SandboxPool(args.validator_tool, warm_size=min(args.warm, concurrency),
                       max_concurrent=concurrency, instance_timeout=3600)
    await pool.start()
    cfg = {"bench_tool": args.bench_tool, "rounds": args.rounds}
    try:
        outs = await asyncio.gather(*[
            validate_unit(pool, claim, results, args.bundles_dir, u, cfg)
            for u in units])
    finally:
        await pool.close()

    from collections import Counter
    print(f"\n[validate] 完成: {dict(Counter(outs))}")
    print(f"[validate] 池指标: {pool.metrics.summary()}")


if __name__ == "__main__":
    asyncio.run(main())
