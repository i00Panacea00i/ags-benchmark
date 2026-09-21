#!/bin/bash
set -euo pipefail
cd /home/ubuntu/ags-benchmark-architecture
set -a; source deploy/.env; set +a
export MAKER_TOOL=bench-maker-ds
setsid venv/bin/python src/drivers/maker_driver.py \
    --units-file runs/units-stress3b.json \
    --batch stress3b --worker stress3-w2 \
    --concurrency 12 --warm 6 \
    > output/stress3/maker-b.log 2>&1 < /dev/null &
echo "$!" > output/stress3/maker-b.pid
echo "[$(date +%T)] 补跑批已启动 PID $(cat output/stress3/maker-b.pid)（27 单元）"
