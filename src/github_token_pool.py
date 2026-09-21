"""GitHub Token 轮换池（限额感知）。

实测（2026-09-21）：同一 GitHub 账号的多个 PAT 共享同一 core 限额池
（按用户计，非按 token）——同账号轮换无增益。本池设计为「限额感知」：
解析每次响应的 X-RateLimit-Remaining 实时余量（/rate_limit 端点有滞后，
不可用），优先分配余量最富的 token；未来接入异账号 token 即自动扩容
（每异账号 +5000/h）。

用法：
    from github_token_pool import GhTokenPool
    pool = GhTokenPool.from_env()          # GITHUB_TOKENS 逗号分隔，缺省回落 GITHUB_TOKEN
    tok = pool.acquire()                    # 取余量最富的 token
    pool.observe(remaining)                 # 响应头观察上报（选传）
"""

import os
import threading
import time


class _TokenState:
    __slots__ = ("token", "remaining", "reset_ts", "last_used")

    def __init__(self, token: str):
        self.token = token
        self.remaining = None    # None = 未知（视为满额优先试）
        self.reset_ts = 0
        self.last_used = 0.0


class GhTokenPool:
    def __init__(self, tokens):
        if not tokens:
            raise ValueError("token 池为空")
        self._states = [_TokenState(t) for t in dict.fromkeys(tokens)]  # 去重保序
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls) -> "GhTokenPool":
        raw = os.environ.get("GITHUB_TOKENS", "")
        toks = [t.strip() for t in raw.split(",") if t.strip()]
        if not toks and os.environ.get("GITHUB_TOKEN"):
            toks = [os.environ["GITHUB_TOKEN"].strip()]
        return cls(toks)

    def acquire(self) -> str:
        """取当前最优 token：余量未知 > 余量高；全部耗尽时取最先重置的。"""
        with self._lock:
            now = time.time()
            unknown = [s for s in self._states if s.remaining is None]
            if unknown:
                s = min(unknown, key=lambda x: x.last_used)   # 未知者轮询
            else:
                alive = [s for s in self._states
                         if s.remaining and (s.reset_ts or now + 3600) <= now + 5]
                if alive:
                    s = max(alive, key=lambda x: x.remaining)
                else:   # 全部耗尽 → 等最先重置者（同账号池等价单 token）
                    s = min(self._states, key=lambda x: x.reset_ts or 1e18)
                    wait = max(0.0, (s.reset_ts or now) - now)
                    time.sleep(min(wait, 60.0))
            s.last_used = now
            return s.token

    def observe(self, remaining, reset_ts=None, token=None):
        """上报响应头 X-RateLimit-Remaining（+Reset）；token 缺省记到最近使用的。"""
        with self._lock:
            cands = ([s for s in self._states if s.token == token]
                     if token else sorted(self._states, key=lambda x: -x.last_used))
            if cands:
                cands[0].remaining = remaining
                if reset_ts:
                    cands[0].reset_ts = reset_ts

    @property
    def size(self) -> int:
        return len(self._states)
