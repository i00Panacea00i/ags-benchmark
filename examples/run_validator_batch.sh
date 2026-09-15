#!/bin/bash
# 示例：agent2 跨 AGS 批量验证（每个 validator 实例内部再拉起题目沙箱）
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source deploy/.env; set +a

# bundles-dir = agent1 产物目录（含 <instance_id>/<instance_id>/{manifest.jsonl,
# tests.patch, golden.patch, repo.tar.gz}）
python3 src/drivers/validator_driver.py \
    --bundles-dir output/maker/units \
    --batch b001 --worker "$(hostname)-$$" \
    --concurrency 8 --warm 3 \
    --rounds 2

# 跨 AGS 拓扑（并发 8 时实际实例数 = 8 validator + 8 bench = 16，
# 距配额边界 50 仍有余量；更高并发见 ARCHITECTURE.md §6 容量公式）
