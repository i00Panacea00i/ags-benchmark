#!/bin/bash
set -euo pipefail
cd /home/ubuntu/ags-benchmark-architecture
set -a; source deploy/.env; set +a
setsid venv/bin/python src/drivers/validator_driver.py \
    --units-file runs/units-solve-audit.jsonl \
    --rounds 2 --concurrency 4 --agent-mode full \
    --claims output/solve-claims.json \
    --results output/solve-audit-results.jsonl \
    > output/stress3/solve-audit.log 2>&1 < /dev/null &
echo "$!" > output/stress3/solve-audit.pid
echo "[$(date +%T)] 审计重跑批启动 PID $(cat output/stress3/solve-audit.pid)（4 单元 / 全量日志采集）"
