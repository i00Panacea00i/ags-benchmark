#!/bin/bash
# 示例：agent2 批量验证（v2 架构：CVM 中心化编排）
#   CVM: tccli 创建每题临时工具 bench-u-* → E2B 实例 → Phase A(/B) → tccli 删除
# 用法前确保 output/maker/dataset.jsonl 中单元含 image_digest（每题镜像模式产物）
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source deploy/.env; set +a

python3 venv/bin/python src/drivers/validator_driver.py \
    --units-file output/maker/dataset.jsonl \
    --rounds 2 \
    --phase-b \
    --concurrency 3    # 并发临时工具 ≤8（配额 10 − 固定工具 1 − 余量）

# 吞吐约束（实测标定）：单题周期 ≈4-5min（建工具~25s+预热~60s+验证~2-3min+清理），
# 8 并发槽 ≈ 90 题/小时。孤儿工具由驱动启动时自动清扫（bench-u-* 前缀回收）。
