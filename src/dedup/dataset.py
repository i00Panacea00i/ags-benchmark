#!/usr/bin/env python3
"""L2 去重：数据集双键去重与无状态分片写入。

双键（与 L1 正交，最后防线）：
  - instance_id 唯一（结构性）
  - issue_url 唯一（防跨实例重复入同一 issue）

两种写入模式（可插拔，协议一致）：
  LocalDataset   —— 单机 JSONL 原子追加（flock + fsync，已验证）
  CosShardWriter —— 无状态分片：每个 driver 副本写独立分片
                    <prefix>/runs/<batch>/<worker>.jsonl，离线合并任务
                    幂等产出 merged/benchmark.jsonl（去重→单行校验→tmp 先行→原子换版）
                    合并前以分片清单（manifest registry）做双键全局去重。
"""
import fcntl
import json
import os


class LocalDataset:
    def __init__(self, path):
        self.path = path
        self.ids, self.urls = set(), set()
        if os.path.isfile(path):
            for line in open(path, encoding="utf-8"):
                if line.strip():
                    r = json.loads(line)
                    self.ids.add(r["instance_id"])
                    self.urls.add(r.get("issue_url"))

    def is_dup(self, record) -> str | None:
        if record["instance_id"] in self.ids:
            return "instance_id 已存在"
        if record.get("issue_url") in self.urls:
            return "issue_url 已存在（跨实例重复）"
        return None

    def append(self, record):
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        json.loads(line)                      # 单行合法性
        with open(self.path, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        self.ids.add(record["instance_id"])
        self.urls.add(record.get("issue_url"))


class CosShardWriter:
    """无状态分片写入器：本副本只写自己的分片，全局去重交给离线合并。

    双键预检：写入前读取 registry（<prefix>/registry.json，每次批量开始时拉取）
    做尽力而为的预检；确定性去重由合并任务兜底（registry 为建议性缓存）。
    """

    def __init__(self, bucket, batch, worker, prefix="dataset",
                 region=None, secret_id=None, secret_key=None):
        from qcloud_cos import CosConfig, CosS3Client
        self.bucket, self.prefix = bucket, prefix.strip("/")
        self.shard_key = f"{self.prefix}/runs/{batch}/{worker}.jsonl"
        self.client = CosS3Client(CosConfig(
            Region=region or os.environ["COS_REGION"],
            SecretId=secret_id or os.environ["COS_SECRET_ID"],
            SecretKey=secret_key or os.environ["COS_SECRET_KEY"], Scheme="https"))
        self.ids, self.urls = set(), set()
        try:
            reg = json.loads(self.client.get_object(
                Bucket=bucket, Key=f"{self.prefix}/registry.json")["Body"].read())
            self.ids, self.urls = set(reg.get("ids", [])), set(reg.get("urls", []))
        except Exception:
            pass

    def is_dup(self, record) -> str | None:
        if record["instance_id"] in self.ids:
            return "instance_id 已在 registry"
        if record.get("issue_url") in self.urls:
            return "issue_url 已在 registry"
        return None

    def append(self, record):
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        json.loads(line)
        # 分片内追加（读-拼-写；分片为副本私有，无并发冲突）
        try:
            old = self.client.get_object(Bucket=self.bucket, Key=self.shard_key)["Body"].read().decode()
        except Exception:
            old = ""
        self.client.put_object(Bucket=self.bucket, Key=self.shard_key,
                               Body=(old + line + "\n").encode())
        self.ids.add(record["instance_id"])
        self.urls.add(record.get("issue_url"))
