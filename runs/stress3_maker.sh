#!/bin/bash
set -euo pipefail
cd /home/ubuntu/ags-benchmark-architecture
set -a; source deploy/.env; set +a
export MAKER_TOOL=bench-maker-ds
setsid venv/bin/python src/drivers/maker_driver.py \
    --units-file runs/units-stress3.json \
    --batch stress3 --worker stress3-w1 \
    --concurrency 12 --warm 6 \
    > output/stress3/maker.log 2>&1 < /dev/null &
echo "$!" > output/stress3/maker.pid
echo "[$(date +%T)] maker 压测批已启动 PID $(cat output/stress3/maker.pid)（91 单元 / 并发 12 / 预热 6）"
