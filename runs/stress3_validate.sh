#!/bin/bash
set -euo pipefail
cd /home/ubuntu/ags-benchmark-architecture
set -a; source deploy/.env; set +a
setsid venv/bin/python src/drivers/validator_driver.py \
    --units-file output/stress3/units-to-validate.jsonl \
    --rounds 2 --concurrency 12 --agent-mode probe \
    > output/stress3/validate.log 2>&1 < /dev/null &
echo "$!" > output/stress3/validate.pid
echo "[$(date +%T)] validator 压测批已启动 PID $(cat output/stress3/validate.pid)（88 单元 / Image Override / 并发 12）"
