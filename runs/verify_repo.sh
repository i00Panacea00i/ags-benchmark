#!/bin/bash
# 仓库试制准入（D2 标准流程）：新仓库 → 反向发现取 2 候选 → maker 试制
# → ≥1 成功则入池（repo-pool.json 标 verified），否则记 failed 原因。
# 用法：bash runs/verify_repo.sh owner/repo [owner/repo2 ...]
set -euo pipefail
cd /home/ubuntu/ags-benchmark-architecture
set -a; source deploy/.env; set +a
export MAKER_TOOL=bench-maker-ds
REPOS="$*"

echo "═══ ① 反向发现（试制模式：每仓库最新 2 候选）═══"
python3 runs/discover_reverse.py --probe "$(echo $REPOS | tr ' ' ',')" --out runs/units-probe.json
N=$(python3 -c "import json; print(len(json.load(open('runs/units-probe.json'))))")
if [ "$N" -eq 0 ]; then
    echo "⚠ 候选为 0：仓库无合格单元（配对/结构筛未过）——不入池"
    exit 1
fi

echo "═══ ② maker 试制（$N 个单元）═══"
set +e
venv/bin/python src/drivers/maker_driver.py \
    --units-file runs/units-probe.json \
    --batch "probe-$(date +%H%M)" --worker "$(hostname)" \
    --concurrency "$N" --warm 2 2>&1 | tee /tmp/probe_make.log | tail -5
set -e

echo "═══ ③ 判定入库 ═══"
python3 - <<'PY'
import json, time
units = json.load(open('runs/units-probe.json'))
made = {f"{u['repo']}#{u['issue']}" for u in units}
recs = [json.loads(l) for l in open('output/maker/dataset.jsonl') if l.strip()]
new_ok = [r for r in recs if f"{r['repo']}#{r['instance_id'].rsplit('-',1)[0].replace('__','/')}" == '' or True]
# 直接按 instance_id 匹配
iid_ok = {r['instance_id'] for r in recs
          if r.get('image_digest', '').startswith('sha256:')}
succ, fail = [], []
for u in units:
    iid = f"{u['repo'].replace('/', '__')}-{u['issue']}"
    (succ if iid in iid_ok else fail).append(u['repo'])
repos = sorted({u['repo'] for u in units})
for repo in repos:
    n_ok = len([r for r in succ if r == repo])
    n_try = len([r for r in succ + fail if r == repo])
    pool_path = 'output/repo-pool.json'
    try:
        pool = json.load(open(pool_path))
    except FileNotFoundError:
        pool = {}
    pool[repo] = {
        'status': 'verified' if n_ok >= 1 else 'failed',
        'probe': f'{n_ok}/{n_try} 试制成功',
        'verified_at': time.strftime('%F %T') if n_ok >= 1 else None,
    }
    json.dump(pool, open(pool_path, 'w'), ensure_ascii=False, indent=1)
    print(f"  {repo}: {pool[repo]['status']}（{pool[repo]['probe']}）")
PY
echo "═══ 完成（repo-pool.json 已更新）═══"
