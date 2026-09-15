#!/bin/bash
# 压测：maker 批（后台运行，日志落盘）
set -euo pipefail
cd /home/ubuntu/ags-benchmark-architecture
set -a; source deploy/.env; set +a
export MAKER_TOOL=bench-maker-ds
mkdir -p output/stress
nohup venv/bin/python src/drivers/maker_driver.py \
    --units-file runs/units-topup.json \
    --batch stressc --worker stress-w1 \
    --concurrency 12 --warm 6 \
    > output/stress/maker-c.log 2>&1 &
echo "$!" > output/stress/maker.pid
echo "[$(date +%T)] maker 批 C 已启动 PID $(cat output/stress/maker.pid)（8 单元 / 并发 12 / 预热 6）"
