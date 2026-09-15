#!/usr/bin/env python3
"""并发标定：阶梯压测 AGS 数据面的真实吞吐/延迟/配额边界。

用法：
  set -a; source deploy/.env; set +a
  python3 src/pool/ramp_test.py 5 10 20 40
扩容（配额提升）后必须重新标定，据此更新池的 max_concurrent。
"""
import asyncio
import os
import sys
import time

from e2b_code_interpreter import AsyncSandbox

TEMPLATE = os.environ.get("VALIDATOR_TOOL", "bench-validator")
CREATE_TIMEOUT_S = 180


async def create_and_ping(idx):
    t0 = time.monotonic()
    try:
        sb = await AsyncSandbox.create(template=TEMPLATE, timeout=900)
        lat = time.monotonic() - t0
        r = await sb.commands.run(f"echo ok-{idx}", timeout=60)
        status = "ok" if f"ok-{idx}" in (r.stdout or "") else "unresponsive"
        await sb.kill()
        return lat, status
    except Exception as e:
        return time.monotonic() - t0, f"fail:{type(e).__name__}:{str(e)[:100]}"


async def run_level(n):
    print(f"\n────── 并发 {n} ──────")
    t0 = time.monotonic()
    results = await asyncio.gather(*[create_and_ping(i) for i in range(n)])
    wall = time.monotonic() - t0
    lats = sorted(l for l, s in results if s == "ok")
    fails = [s for _, s in results if s not in ("ok", "unresponsive")]

    def pct(p):
        return lats[min(len(lats) - 1, int(len(lats) * p))] if lats else 0

    print(f"成功 {len(lats)}/{n} | 串行等效 {sum(lats):.0f}s → 并发墙钟 {wall:.1f}s"
          f"（加速比 {sum(lats) / wall:.1f}x）")
    if lats:
        print(f"创建延迟 P50={pct(0.5):.1f}s P90={pct(0.9):.1f}s max={lats[-1]:.1f}s")
    print(f"吞吐 {n / wall:.1f} 实例/s")
    if fails:
        print(f"❌ 失败 {len(fails)}: {fails[:2]}")
    return len(fails)


async def main():
    levels = [int(x) for x in sys.argv[1:]] or [5, 10, 20]
    print(f"AGS 并发标定：template={TEMPLATE} domain={os.environ.get('E2B_DOMAIN', '?')}")
    for n in levels:
        if await run_level(n):
            print(f"\n⚠️ 并发 {n} 触达限额边界。生产建议 max_concurrent = 上一阶梯 × 0.8。")
            break
    else:
        print("\n全部阶梯通过。生产建议 max_concurrent = 最高成功阶梯。")


if __name__ == "__main__":
    asyncio.run(main())
