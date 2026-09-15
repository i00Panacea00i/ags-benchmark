#!/bin/bash
# 示例：agent1 批量制作（无状态池化驱动，可多副本并行）
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source deploy/.env; set +a

# 单元清单（可由发现服务产出，或手工列出）
cat > /tmp/units.json <<'EOF'
[{"repo": "pypa/packaging", "issue": 1204},
 {"repo": "pallets/click", "issue": 3571}]
EOF

# 并发 8 = 配额边界(50)内安全值；预热 3 摊薄冷启动（见 ARCHITECTURE.md §6 标定）
python3 src/drivers/maker_driver.py \
    --units-file /tmp/units.json \
    --batch b001 --worker "$(hostname)-$$" \
    --concurrency 8 --warm 3

# 多副本横向扩展：在另一台机器/Pod 重复执行同命令即可——
# L1 claim（flock→cos 切换）保证单元全局只做一次，无需协调。
