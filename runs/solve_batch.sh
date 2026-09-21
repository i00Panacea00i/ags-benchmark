#!/bin/bash
set -euo pipefail
cd /home/ubuntu/ags-benchmark-architecture
set -a; source deploy/.env; set +a
setsid venv/bin/python src/drivers/validator_driver.py \
    --units-file runs/units-solve-easy.jsonl \
    --rounds 2 --concurrency 4 --agent-mode full \
    --claims output/solve-claims.json \
    --results output/solve-results.jsonl \
    > output/stress3/solve-easy.log 2>&1 < /dev/null &
echo "$!" > output/stress3/solve-easy.pid
echo "[$(date +%T)] 解题批启动 PID $(cat output/stress3/solve-easy.pid)（8 单元 / 校准协议 / 并发 4）"
