#!/usr/bin/env python3
"""agent1 池化批量驱动：题目制作的无状态编排器。

与 validator_driver 同构（池 + claim + 分片），驱动 agent1（maker）沙箱：
  L1 claim → maker 池 acquire → commands.run(envs=单元参数) 运行镜像内
  /opt/builder/builder_agent.py → tar 产物回传（files API）→ L2 分片写入。

agent1 的制作逻辑（配对/漏斗/F2P 稳定性筛选/模板改写/双镜像构建）全部
封装在 maker 沙箱镜像内（主项目 bench-builder，已验证），本驱动只做编排，
无状态、可多副本并行。

用法：
  set -a; source deploy/.env; set +a
  python3 src/drivers/maker_driver.py \
      --units-file units.json --batch b001 --worker w1 [--concurrency 8 --warm 3]
  units.json: [{"repo": "pypa/packaging", "issue": 1204}, …]
"""
import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import tarfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from pool.sandbox_pool import SandboxPool                    # noqa: E402
from dedup.claim import make_claim_store                     # noqa: E402
from dedup.dataset import CosShardWriter, LocalDataset       # noqa: E402

from e2b.sandbox.commands.command_handle import CommandExitException

MAKER_ENTRY = "/opt/builder/builder_agent.py"    # maker 镜像内入口（已验证协议）


def refresh_tcr_token():
    """TCR 实例令牌每批刷新（实测 ~1.5h 过期）。"""
    r = subprocess.run(["tccli", "tcr", "CreateInstanceToken", "--region",
                        os.environ.get("TCR_REGION", "ap-singapore"),
                        "--RegistryId", os.environ.get("TCR_REGISTRY_ID", "tcr-xxxxxxxx")],
                       capture_output=True, text=True, timeout=60)
    d = json.loads(r.stdout[r.stdout.find("{"):])
    return d["Username"], d["Token"]


def unit_envs(repo, issue, tcr_user, tcr_pass):
    ev = {"WORK_REPO": repo, "WORK_ISSUE": str(issue), "OUTPUT_DIR": "/output",
          "DOCKER_CONFIG": "/root/.docker",
          "TCR_REGISTRY": os.environ["TCR_REGISTRY"],
          "TCR_NAMESPACE": os.environ.get("TCR_NAMESPACE", "benchmark-repo"),
          "TCR_PUSH_USER": tcr_user, "TCR_PUSH_PASS": tcr_pass,
          "DS_HARNESS_MODE": os.environ.get("DS_HARNESS_MODE", "1"),
          "BENCH_TOOL": os.environ.get("BENCH_TOOL", "bench-ds")}
    for k in ("GITHUB_TOKEN", "OPENAI_BASE_URL", "OPENAI_API_KEY", "LLM_MODEL"):
        if os.environ.get(k):
            ev[k] = os.environ[k]          # LLM 就绪时启用 DeepSeek 改写链，否则模板降级
    ip = subprocess.run(["dig", "+short", os.environ["TCR_REGISTRY"], "@8.8.8.8"],
                        capture_output=True, text=True).stdout.split()
    if ip:
        ev["TCR_PUBLIC_IP"] = ip[0]    # 沙箱不在 VPC：强制 TCR 公网端点
    return ev


async def run_remote(sb, cmd, timeout, envs=None):
    try:
        return await sb.commands.run(cmd, timeout=timeout, user="root", envs=envs)
    except CommandExitException as e:
        return e


async def make_unit(pool, claim, dataset, artifacts_dir, repo, issue, envs):
    key = f"make/{repo}#{issue}"
    ok, rec = await asyncio.to_thread(claim.claim, key, {"stage": "make"})
    if not ok:
        print(f"[{key}] L1 拦截：已是 {rec.get('state')}")
        return "blocked"
    handle = await pool.acquire()
    try:
        r = await run_remote(handle.sb, f"python3 {MAKER_ENTRY}",
                             timeout=1800, envs=envs)
        m = re.findall(r'\{.*\}', (r.stdout or "") + "\n" + (r.stderr or ""), re.S)
        result = json.loads(m[-1]) if m else {"result": "error",
                                              "error": "无 RESULT 输出"}
        print(f"[{key}] agent: {json.dumps(result, ensure_ascii=False)[:140]}")
        if result.get("result") == "success":
            await run_remote(handle.sb, "cd /output && tar -czf /output/unit.tar.gz .",
                             timeout=600)
            blob = await handle.sb.files.read("/output/unit.tar.gz",
                                              format="bytes", user="root")
            dest = os.path.join(artifacts_dir, "units", result["instance_id"])
            os.makedirs(dest, exist_ok=True)
            tgz = os.path.join(dest, "unit.tar.gz")
            with open(tgz, "wb") as f:
                f.write(bytes(blob))
            with tarfile.open(tgz) as tar:
                tar.extractall(dest)
            os.unlink(tgz)
            manifest = json.loads(open(os.path.join(
                dest, result["instance_id"], "manifest.jsonl")).read().strip())
            dup = dataset.is_dup(manifest)
            if dup:
                await asyncio.to_thread(claim.finish, key, "done", f"dup: {dup}")
                return "dup"
            await asyncio.to_thread(dataset.append, manifest)
            await asyncio.to_thread(claim.finish, key, "done", "validated-dataset")
            print(f"[{key}] ✅ 入库: F2P {len(manifest['FAIL_TO_PASS'])}"
                  f" / P2P {len(manifest['PASS_TO_PASS'])}")
            return "success"
        if result.get("result") == "filtered":
            await asyncio.to_thread(claim.finish, key, "done",
                                    f"filtered@{result.get('stage')}")
            return "filtered"
        await asyncio.to_thread(claim.finish, key, "failed",
                                str(result.get("error"))[:200])
        return "error"
    except Exception as e:
        await asyncio.to_thread(claim.finish, key, "failed", str(e)[:150])
        return "crash"
    finally:
        await pool.release(handle)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units-file", required=True)
    ap.add_argument("--batch", default="b001")
    ap.add_argument("--worker", default=os.uname().nodename)
    ap.add_argument("--maker-tool", default=os.environ.get("MAKER_TOOL", "bench-builder"))
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--warm", type=int, default=3)
    ap.add_argument("--artifacts-dir", default="output/maker")
    ap.add_argument("--dataset", default=None)
    args = ap.parse_args()

    for k in ("E2B_DOMAIN", "E2B_API_KEY", "TCR_REGISTRY"):
        if not os.environ.get(k):
            sys.exit(f"缺少环境变量: {k}")

    units = [(u["repo"], u["issue"]) if isinstance(u, dict) else tuple(u)
             for u in json.load(open(args.units_file))]
    print(f"[make] {len(units)} 个单元 | maker={args.maker_tool} | 并发 {args.concurrency}")

    claim = await asyncio.to_thread(
        make_claim_store, None,
        **{"path": os.path.join(args.artifacts_dir, "claims.json"),
           "bucket": os.environ.get("COS_BUCKET", ""),
           "prefix": f"make/{args.batch}/claims"})
    if os.environ.get("CLAIM_BACKEND") == "cos":
        dataset = CosShardWriter(os.environ["COS_BUCKET"], args.batch, args.worker,
                                 prefix=f"make/{args.batch}")
    else:
        dataset = LocalDataset(args.dataset or os.path.join(
            args.artifacts_dir, "dataset.jsonl"))

    tcr_user, tcr_pass = await asyncio.to_thread(refresh_tcr_token)
    concurrency = min(args.concurrency, 40)
    pool = SandboxPool(args.maker_tool, warm_size=min(args.warm, concurrency),
                       max_concurrent=concurrency, instance_timeout=3600)
    await pool.start()
    try:
        outs = await asyncio.gather(*[
            make_unit(pool, claim, dataset, args.artifacts_dir, repo, issue,
                      unit_envs(repo, issue, tcr_user, tcr_pass))
            for repo, issue in units])
    finally:
        await pool.close()

    from collections import Counter
    print(f"\n[make] 完成: {dict(Counter(outs))}")
    print(f"[make] 池指标: {pool.metrics.summary()}")


if __name__ == "__main__":
    asyncio.run(main())
