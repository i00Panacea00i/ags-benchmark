#!/usr/bin/env python3
"""异步沙箱池：AGS（E2B 兼容数据面）批量拉取的去瓶颈层。

实测标定（ap-singapore，2026-09-15）：
  - 创建延迟在 5→40 并发恒定 ~4.2s（网关完全并行）
  - 账号并发实例配额边界 ≈ 50（LimitExceeded.SandboxInstance）
  - 生产参数：max_concurrent=40、warm_size=8~12

能力：预热池（acquire 0ms）+ 信号量背压 + 指数退避 + 配额背压 + 指标。
"""
import asyncio
import os
import random
import time
from dataclasses import dataclass, field

from e2b_code_interpreter import AsyncSandbox


@dataclass
class PoolMetrics:
    created: int = 0
    killed: int = 0
    create_failures: int = 0
    retries: int = 0
    create_latencies: list = field(default_factory=list)
    acquire_waits: list = field(default_factory=list)

    def summary(self):
        lat = sorted(self.create_latencies)

        def pct(p):
            return lat[min(len(lat) - 1, int(len(lat) * p))] if lat else 0.0
        wait = sorted(self.acquire_waits)
        return {"created": self.created, "killed": self.killed,
                "failures": self.create_failures, "retries": self.retries,
                "create_p50_s": round(pct(0.50), 2),
                "create_p90_s": round(pct(0.90), 2),
                "create_max_s": round(lat[-1], 2) if lat else 0,
                "acquire_wait_p50_ms": round(wait[len(wait) // 2] * 1000, 1) if wait else 0}


class SandboxHandle:
    def __init__(self, sb, born_at):
        self.sb = sb
        self.born_at = born_at
        self.uses = 0


class SandboxPool:
    def __init__(self, template, warm_size=8, max_concurrent=40,
                 instance_timeout=3600, max_age_s=2400, max_uses=8,
                 create_timeout_s=180, create_retries=4):
        self.template = template
        self.warm_size = warm_size
        self.instance_timeout = instance_timeout
        self.max_age_s = max_age_s
        self.max_uses = max_uses
        self.create_retries = create_retries
        self._sem = asyncio.Semaphore(max_concurrent)
        self._warm: asyncio.Queue = asyncio.Queue()
        self._alive: set = set()
        self._replenish_task = None
        self._closed = False
        self.metrics = PoolMetrics()

    async def _create_one(self):
        delay = 2.0
        for attempt in range(self.create_retries + 1):
            try:
                t0 = time.monotonic()
                sb = await AsyncSandbox.create(
                    template=self.template, timeout=self.instance_timeout)
                self.metrics.create_latencies.append(time.monotonic() - t0)
                self.metrics.created += 1
                self._alive.add(sb.sandbox_id)
                return sb
            except Exception as e:
                msg = str(e)
                if "LimitExceeded" in msg:      # 配额背压：等待回补而非失败
                    if attempt < self.create_retries:
                        self.metrics.retries += 1
                        await asyncio.sleep(20 + random.uniform(0, 10))
                        continue
                    raise
                transient = any(k in msg for k in
                                ("429", "5xx", "502", "503", "504", "timed out", "Timeout"))
                if attempt < self.create_retries and transient:
                    self.metrics.retries += 1
                    await asyncio.sleep(delay + random.uniform(0, delay / 2))
                    delay = min(delay * 2, 30)
                    continue
                self.metrics.create_failures += 1
                raise

    async def _replenisher(self):
        while not self._closed:
            inflight = len(self._alive) - self._warm.qsize()
            deficit = self.warm_size - self._warm.qsize()
            if deficit > 0 and inflight < self.warm_size * 2:
                try:
                    sb = await self._create_one()
                    await self._warm.put(SandboxHandle(sb, time.monotonic()))
                except Exception:
                    await asyncio.sleep(5)
            else:
                await asyncio.sleep(1)

    async def start(self):
        for _ in range(self.warm_size):
            try:
                sb = await self._create_one()
                await self._warm.put(SandboxHandle(sb, time.monotonic()))
            except Exception:
                break
        self._replenish_task = asyncio.create_task(self._replenisher())

    async def acquire(self) -> SandboxHandle:
        t0 = time.monotonic()
        async with self._sem:
            self.metrics.acquire_waits.append(time.monotonic() - t0)
            try:
                handle = self._warm.get_nowait()
                if (time.monotonic() - handle.born_at > self.max_age_s
                        or handle.uses >= self.max_uses):
                    await self._kill_handle(handle)
                    handle = SandboxHandle(await self._create_one(), time.monotonic())
            except asyncio.QueueEmpty:
                handle = SandboxHandle(await self._create_one(), time.monotonic())
            handle.uses += 1
            return handle

    async def release(self, handle: SandboxHandle, healthy=True):
        if self._closed or not healthy \
                or handle.uses >= self.max_uses \
                or time.monotonic() - handle.born_at > self.max_age_s:
            await self._kill_handle(handle)
        else:
            await self._warm.put(handle)

    async def _kill_handle(self, handle):
        try:
            await handle.sb.kill()
            self._alive.discard(handle.sb.sandbox_id)
            self.metrics.killed += 1
        except Exception:
            pass

    async def close(self):
        self._closed = True
        if self._replenish_task:
            self._replenish_task.cancel()
            try:
                await self._replenish_task
            except asyncio.CancelledError:
                pass
        while not self._warm.empty():
            await self._kill_handle(self._warm.get_nowait())
