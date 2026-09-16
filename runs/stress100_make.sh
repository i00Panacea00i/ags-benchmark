#!/bin/bash
# 100 题压测：制作批（setsid 脱离会话）
set -euo pipefail
cd /home/ubuntu/ags-benchmark-architecture
set -a; source deploy/.env; set +a
export MAKER_TOOL=bench-maker-ds
mkdir -p output/stress100
setsid nohup venv/bin/python src/drivers/maker_driver.py \
    --units-file runs/units-batch.json \
    --batch stress100 --worker stress100 \
    --concurrency 30 --warm 4 \
    > output/stress100/maker-b.log 2>&1 &
echo "$!" > output/stress100/maker.pid
echo "[$(date +%T)] 制作批已启动 PID $(cat output/stress100/maker.pid)（145 候选 / 并发 36）"
