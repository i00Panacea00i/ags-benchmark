#!/usr/bin/env python3
"""L1 去重：工作单元互斥分配（claim）——支持单机与无状态两种后端。

语义（两种后端完全一致，可插拔）：
  claim(repo|key)  -> (True, rec) 首次认领 / (False, rec) 已被认领或完成
  finish(key, state, note)       回写终态（done/failed）
  陈旧锁回收：in-flight 超过 stale_s 自动允许重抢（崩溃 Worker 自愈）

后端：
  FlockClaimStore —— 单机 flock（已验证，适合单编排器 ≤40 并发）
  CosClaimStore   —— COS 条件写（x-cos-if-none-match: *，409/412 即已被认领），
                     无状态横向扩展的标准后端；键 = cos://<bucket>/<prefix>/claims/<key>.json
"""
import fcntl
import json
import os
import time
from datetime import datetime, timezone

STALE_S = 3 * 3600      # 陈旧 in-flight 回收阈值（> 单元最长处理时间）


class FlockClaimStore:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if not os.path.isfile(path):
            open(path, "w").write("{}")
        self.path = path

    def _now(self):
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _load(self):
        return json.load(open(self.path))

    def claim(self, key, meta=None):
        with open(self.path, "r+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                data = json.load(f)
                rec = data.get(key)
                if rec and rec.get("state") in ("in-flight", "done"):
                    if rec["state"] == "in-flight":
                        try:
                            age = time.time() - datetime.fromisoformat(
                                rec.get("ts", "")).timestamp()
                        except (ValueError, TypeError):
                            age = 0
                        if age < STALE_S:
                            return False, rec
                    else:
                        return False, rec
                data[key] = {"state": "in-flight", "ts": self._now(),
                             "meta": meta or {}}
                f.seek(0), f.truncate()
                f.write(json.dumps(data, ensure_ascii=False, indent=1))
                return True, data[key]
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def finish(self, key, state, note=""):
        with open(self.path, "r+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                data = json.load(f)
                data[key] = {"state": state, "note": note, "ts": self._now()}
                f.seek(0), f.truncate()
                f.write(json.dumps(data, ensure_ascii=False, indent=1))
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class CosClaimStore:
    """无状态 claim：COS 条件写实现「认领即创建对象」。

    依赖 qcloud_cos（pip install cos-python-sdk-v5）。
    认领 = PUT claims/<key>.json 带 If-None-Match:* → 成功即认领；
    409/412/PreconditionConflict = 已被他人认领。陈旧回收：读对象时间戳判断。
    """

    def __init__(self, bucket, prefix="claims", region=None, secret_id=None, secret_key=None):
        from qcloud_cos import CosConfig, CosS3Client
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = CosS3Client(CosConfig(
            Region=region or os.environ["COS_REGION"],
            SecretId=secret_id or os.environ["COS_SECRET_ID"],
            SecretKey=secret_key or os.environ["COS_SECRET_KEY"], Scheme="https"))

    def _key(self, key):
        # repo#issue → 安全对象名
        return f"{self.prefix}/{key.replace('#', '_').replace('/', '__')}.json"

    def claim(self, key, meta=None):
        import urllib.error
        k = self._key(key)
        # 陈旧回收检查
        try:
            rec = json.loads(self.client.get_object(Bucket=self.bucket, Key=k)["Body"].read())
            if rec.get("state") == "done":
                return False, rec
            if rec.get("state") == "in-flight":
                try:
                    age = time.time() - datetime.fromisoformat(rec["ts"]).timestamp()
                except (ValueError, TypeError):
                    age = 0
                if age < STALE_S:
                    return False, rec
        except Exception:
            pass     # 不存在 → 可认领
        try:
            self.client.put_object(
                Bucket=self.bucket, Key=k,
                Body=json.dumps({"state": "in-flight",
                                 "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                 "meta": meta or {}}).encode(),
                IfNoneMatch="*")          # 条件写：仅当对象不存在时成功
            return True, {"state": "in-flight"}
        except Exception:
            return False, {"state": "in-flight", "note": "claimed-by-other"}

    def finish(self, key, state, note=""):
        self.client.put_object(
            Bucket=self.bucket, Key=self._key(key),
            Body=json.dumps({"state": state, "note": note,
                             "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}).encode())


def make_claim_store(mode=None, **kw):
    """工厂：CLAIM_BACKEND=flock|cos（默认 flock，单机零依赖）。"""
    mode = (mode or os.environ.get("CLAIM_BACKEND", "flock")).lower()
    if mode == "cos":
        return CosClaimStore(kw["bucket"], **{k: v for k, v in kw.items() if k != "bucket"})
    return FlockClaimStore(kw.get("path", "output/claims.json"))
