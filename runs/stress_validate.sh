#!/bin/bash
# 满并发核验（setsid 脱离会话 + 后台日志）
set -euo pipefail
cd /home/ubuntu/ags-benchmark-architecture
set -a; source deploy/.env; set +a
export AGENT_TOOL=bench-solver
mkdir -p output/stress
setsid nohup venv/bin/python src/drivers/validator_driver.py \
    --units-file /tmp/units_all.jsonl \
    --rounds 2 --concurrency 20 \
    > output/stress/validate-20pairs.log 2>&1 &
echo "$!" > output/stress/validate.pid
echo "[$(date +%T)] 满并发核验已启动 PID $(cat output/stress/validate.pid)（20 对沙箱 / 40 实例 / 22 工具）"
