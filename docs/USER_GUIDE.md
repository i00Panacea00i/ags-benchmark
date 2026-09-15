# 使用手册

## 1. 前置条件

| 项 | 要求 | 获取方式 |
|---|---|---|
| AGS 服务 | 已开通（目标地域，如 ap-singapore） | 控制台 → Agent Runtime |
| E2B_API_KEY | 1 个（数据面） | AGS 控制台 → API Keys |
| TCR 企业版实例 | 1 个（maker 镜像构建推送） | 容器镜像服务，需开启公网访问端点 |
| CAM 角色 | 1 个（TCR 拉取最小权限，绑定到工具） | 访问管理 → 角色（载体：Agent Runtime） |
| GITHUB_TOKEN | 可选（maker 发现/配对提速至 5000/h） | fine-grained PAT，公开仓库只读 |
| COS 桶 | 可选（多副本去重模式） | 对象存储 |
| 本机 | Python 3.10+、tccli（已配置密钥）、docker、dig | — |

## 2. 部署

### 2.1 配置

```bash
cd ags-benchmark-architecture
cp deploy/env.example deploy/.env && chmod 600 deploy/.env
# 编辑填写 E2B_API_KEY / TCR_REGISTRY / ROLE_ARN 等
```

### 2.2 构建并推送镜像（先推送后建工具——见 T03 红线）

```bash
# agent2 验证沙箱镜像
docker build -t $TCR_REGISTRY/$TCR_NAMESPACE/benchmark-validator:1.0.0 \
    -f images/Dockerfile.validator .
docker push $TCR_REGISTRY/$TCR_NAMESPACE/benchmark-validator:1.0.0

# 题目基座镜像（harness 从主项目复制到构建上下文）
cp -r <主项目>/benchmark-builder-sandbox/harness images/harness_ctx/
docker build -t $TCR_REGISTRY/$TCR_NAMESPACE/benchmark-base:1.0.0 \
    -f images/Dockerfile.bench_base images/
docker push $TCR_REGISTRY/$TCR_NAMESPACE/benchmark-base:1.0.0

# agent1 镜像：直接使用主项目已推送的 benchmark-builder-ags（或按其 Dockerfile 重建）
```

### 2.3 创建工具并预热

```bash
bash deploy/create_tools.sh
# 轮询至三个工具全部 ACTIVE（约 1 分钟）
tccli ags DescribeSandboxToolList --region $TCR_REGION
```

### 2.4 并发标定（首次部署/配额变更后必做）

```bash
set -a; source deploy/.env; set +a
python3 src/pool/ramp_test.py 5 10 20
# 取最高全成功阶梯 × 0.8 作为生产 --concurrency 上限
```

## 3. 运行

### 3.1 agent1 批量制作

```bash
bash examples/run_maker_batch.sh
# 或直接：
python3 src/drivers/maker_driver.py --units-file units.json \
    --batch b001 --worker w1 --concurrency 8 --warm 3
```

产物：`output/maker/units/<instance_id>/<instance_id>/{manifest.jsonl, tests.patch,
golden.patch, repo.tar.gz, …}` + 数据集分片。

### 3.2 agent2 跨 AGS 批量验证

```bash
bash examples/run_validator_batch.sh
# 或直接：
python3 src/drivers/validator_driver.py --bundles-dir output/maker/units \
    --batch b001 --worker w1 --concurrency 8 --warm 3 --rounds 2
```

产物：`output/validate-results.jsonl`（每单元一条 verdict：
`validated / rejected(原因) / error`）。

### 3.3 结果判读

| verdict | 含义 | 动作 |
|---|---|---|
| validated | answer N 轮全过且一致 + baseline 全 FAIL | 入数据集 |
| rejected:answer_not_all_passed | 参考解在该环境不成立 | 剔除（留痕于 claim note） |
| rejected:answer_rounds_inconsistent | 轮间不稳定（flaky） | 剔除 |
| rejected:baseline_leak | 不打 golden 也过 → 测试无法区分 | 剔除 |
| error | 基础设施错误 | 修 claim 后重跑（幂等） |

## 4. 配置参考

全部环境变量见 `deploy/env.example` 注释。关键项：

| 变量 | 默认 | 说明 |
|---|---|---|
| `--concurrency` | 8 | 全局并发；硬上限 40（标定），validator 记得 ×2 实例 |
| `--warm` | 3 | 预热水位；建议并发 × 20-30% |
| `CLAIM_BACKEND` | flock | 多副本部署必切 `cos` |
| `VERIFY_ROUNDS` | 2 | answer 一致性轮数 |

## 5. 横向扩展操作

```bash
# 任一新机器（无共享盘）：
git clone <本仓库> && cp deploy/.env …
export CLAIM_BACKEND=cos
python3 src/drivers/maker_driver.py --units-file units.json \
    --batch b001 --worker $(hostname) --concurrency 8
# 即插即用：L1(COS 条件写) 保证与其它副本零重复，无需注册/协调
```

## 6. 运维速查

```bash
# 工具状态
tccli ags DescribeSandboxToolList --region $TCR_REGION
# 重建单个工具（改镜像后）
tccli ags DeleteSandboxTool --region $TCR_REGION --ToolId sdt-xxx
#   → 改 create_tools.sh 中对应段重跑
# 预热
tccli ags CreatePreCacheImageTask --region $TCR_REGION --cli-unfold-argument \
    --Image <镜像> --ImageRegistryType enterprise
# 重跑失败单元（幂等）
python3 - <<'PY'
import json
p = "output/maker/claims.json"
d = json.load(open(p))
for k, v in d.items():
    if v.get("state") == "failed":
        v["state"] = "failed"   # failed 本就可重抢；此处仅示意清理 done 需人工确认
json.dump(d, open(p, "w"), ensure_ascii=False, indent=1)
PY
```

## 7. 输出物与数据集

- 数据集分片：`<COS>/make/<batch>/<worker>.jsonl`（或本地 `output/maker/dataset.jsonl`）
- 验证结果：`<COS>/validate/<batch>/<worker>.jsonl`
- 离线合并（多副本模式）：拉取全部分片 → 双键去重 → 单行校验 → `.tmp` 先行 →
  原子换版为 `merged/benchmark.jsonl`
