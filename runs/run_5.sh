#!/bin/bash
# 一键运行：制作并核验 5 个 benchmark（双沙箱核验 + pass@1 + 失败分析）
# 前置：deploy/.env 已配置；工具 bench-maker-ds / bench-solver 均 ACTIVE
# 用法：bash runs/run_5.sh [数量，默认 5]
set -euo pipefail
cd /home/ubuntu/ags-benchmark-architecture
N=${1:-5}
set -a; source deploy/.env; set +a
export MAKER_TOOL=bench-maker-ds AGENT_TOOL=bench-solver

echo "═══ ① 发现 $N 个合格单元（GitHub 配对+结构双筛）═══"
python3 runs/discover_stress.py "$N"

echo "═══ ② agent1 制作（每题镜像 → TCR，~90s/题）═══"
venv/bin/python src/drivers/maker_driver.py \
    --units-file runs/units-stress.json \
    --batch "b$(date +%H%M)" --worker "$(hostname)" \
    --concurrency "$N" --warm 3

echo "═══ ③ 提取本批制作成功的单元（含镜像 digest）═══"
python3 - <<'PY'
import json
made = {f"{u['repo'].replace('/', '__')}-{u['issue']}"
        for u in json.load(open('runs/units-stress.json'))}
recs = [json.loads(l) for l in open('output/maker/dataset.jsonl') if l.strip()]
sel = [r for r in recs
       if r.get('image_digest', '').startswith('sha256:')
       and r['instance_id'] in made]
open('/tmp/units-batch.jsonl', 'w').write(
    '\n'.join(json.dumps(r) for r in sel) + '\n')
open('/tmp/units-batch-ids.json', 'w').write(json.dumps([r['instance_id'] for r in sel]))
print(f"本批带镜像单元: {len(sel)} 个（进入核验）")
if not sel:
    print("⚠ 本批无新制作单元（候选全部重复或被质量漏斗过滤）——核验阶段将跳过")
PY

echo "═══ ④ agent2 核验（双沙箱：agent 解题 pass@1 → 标准答案核验 → 失败分析）═══"
if [ -s /tmp/units-batch.jsonl ] && [ "$(wc -l < /tmp/units-batch.jsonl)" -gt 0 ]; then
    venv/bin/python src/drivers/validator_driver.py \
        --units-file /tmp/units-batch.jsonl \
        --rounds 2 --concurrency "$N"
else
    echo "（跳过：本批 0 个单元）"
fi

echo "═══ ⑤ 结果与 LLM 证据（仅本批）═══"
python3 - <<'PY'
import json, os
ids = set(json.load(open('/tmp/units-batch-ids.json')))
if not ids:
    print("本批无核验结果（0 个单元进入核验）")
else:
    shown = 0
    for l in open('output/validate-results.jsonl'):
        if not l.strip():
            continue
        v = json.loads(l)
        if v['instance_id'] not in ids:
            continue                      # 只展示本批，历史记录不刷屏
        a = v.get('agent', {})
        print(f"{v['instance_id']}: pass@1={'✅' if a.get('pass_at_1') else '❌'} "
              f"({a.get('f2p_passed')}) | Phase A={v.get('phase_a', {}).get('result')}")
        shown += 1
    print(f"（本批展示 {shown}/{len(ids)} 条；全量历史见 output/validate-results.jsonl）")
    print("── LLM 使用证据（本批对话轨迹）──")
    for i in sorted(ids):
        p = f'output/validate-transcripts/{i}.json'
        print(f"  {p}{' ✓' if os.path.exists(p) else '（无）'}")
PY
