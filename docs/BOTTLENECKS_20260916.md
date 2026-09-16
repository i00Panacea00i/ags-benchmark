# 满并发核验攻坚：卡点与解决方案沉淀

> 2026-09-16 满并发（20 对沙箱/批）核验任务全过程卡点记录。
> 每条含：现象 → 根因 → 解决方案 → 验证数据。供后续 300 题批量任务前对照排查。
> 关联代码：`src/drivers/validator_driver.py`、`images/dsharness/agents/maker_agent.py`、
> `runs/discover_stress.py`、`runs/run_5.sh`。

---

## K1 重复发现已制作单元，批次空转

| 项 | 内容 |
|---|---|
| 现象 | `run_5.sh` 两轮运行均重新发现 #2906/#2869/#2860/#2985 等已做单元 → L1 拦截 `blocked: 4` → 制作 0 → 核验 0，全链空转 |
| 根因 | 发现脚本 DONE 集只从 `dataset.jsonl` 加载（**仅成功单元**）；被质量漏斗过滤的单元（untestable/no_code_change/harness_crash）只存在于 `claims.json`，于是被反复重新发现 |
| 解决 | DONE 集改从 **`claims.json` 全终局**（done + failed）加载 + 数据集 + 跨会话历史号段（实测 68 单元生效） |
| 验证 | 修复后用户报告的 4 个重复项全部排除；后续发现仅产新单元 |
| 教训 | **「已处理」的唯一权威来源是任务账本（claims），不是产物集（dataset）**——产物集天然只含成功路径 |

## K2 核验结果展示错乱（全部显示历史单元 -3145）

| 项 | 内容 |
|---|---|
| 现象 | `run_5.sh` ⑤ 步核验结论打印 4 条 `pallets__click-3145`（含 `pass@1=(None)` 旧格式），与本次运行无关 |
| 根因 | 展示脚本直接遍历 `validate-results.jsonl` **全部历史记录**（该文件允许同单元多次追加留痕）+ 一段废代码残留 |
| 解决 | ⑤ 按**本批 instance_id 过滤**展示；③ 步 0 单元时核验自动跳过并给出明确提示 |
| 教训 | 追加式审计文件（results/transcripts）做展示时必须带批次过滤键 |

## K3 并发制作镜像 tag 碰撞（最严重，静默数据损坏）

| 项 | 内容 |
|---|---|
| 现象 | 满并发核验时 3+ 单元「工具创建后 FAILED」**三连败**（含换名重试），同批其他单元正常；本地 `docker run` 冒烟该镜像完全正常（envd /health 204） |
| 根因 | maker 镜像 tag 仅**分钟级精度**（`%Y%m%d-%H%M`）——同仓库并发制作的两单元同分钟完成 → 生成**相同 tag** → crane 后推覆盖先推 → 先完成单元的 tag↔digest 失配 → AGS 平台按 tag 拉取校验稳定失败。实测取证：**16/20 存量单元被 3 个碰撞 tag 覆盖**（压测时代的规模化遗留） |
| 解决 | ① 根治：tag 改**秒级 + 题号**唯一化（`%Y%m%d-%H%M%S-<issue>`，maker v1.1.3）；② 存量修复：20/20 单元按 digest 重打唯一 tag（`fix-<issue>`）并回填 dataset |
| 验证 | #727 重打唯一 tag 后立即恢复正常（Phase A validated）；对照批 20/20 全部就绪无一 FAILED |
| 教训 | **并发产物命名必须含业务唯一键**（题号），时间戳只是辅助；tag 覆盖是静默损坏——必须靠「digest 失配即 FAILED」的平台校验暴露，要主动巡检 |

## K4 makedirs 回归（LLM 证据功能引入）

| 项 | 内容 |
|---|---|
| 现象 | maker 批 3/4 单元死于 `FileExistsError: /output/<iid>/pr...` |
| 根因 | 新增 LLM 证据段在 ⑥ 预建了 `problems` 目录，⑦ 产物落盘的 `os.makedirs`（无 `exist_ok`）随即爆炸 |
| 解决 | ⑦ 全部 `makedirs(..., exist_ok=True)`（maker v1.1.2） |
| 教训 | 功能增强改动后**必须全链重跑一题**再合入——该回归在静态检查下不可见 |

## K5 工具创建偶发 FAILED（平台侧）

| 项 | 内容 |
|---|---|
| 现象 | 个别单元工具创建后 FAILED，同镜像重跑即恢复（区别于 K3 的确定性失败） |
| 根因 | 平台侧调度/节点偶发异常（非镜像问题——本地冒烟正常） |
| 解决 | validator 加**换名重试**（`-rNN` 后缀一次）；仍失败则 verdict 记 error，不阻塞批次 |
| 教训 | 偶发与确定性失败要区分对待：换名重试只对前者有效，后者（K3）必须修根因 |

## K6 满并发实例拉取慢（61-219s/个，核心性能卡点）

| 项 | 内容 |
|---|---|
| 现象 | 20 对沙箱满并发时 bench 实例就绪 61-219s/个，全批 29 分钟；且非均匀排队 |
| 根因（对照实验定位） | 工具注册（CreateSandboxTool）仅 ~0.4-2s 元数据操作，**不是瓶颈**；真瓶颈是 `Sandbox.create` 阶段 N 个实例**并发拉取新内容层抢占节点下载带宽**（每镜像 30-100MB；后期带宽让出降至 ~73s 印证） |
| 解决 | **批次级预热前置**（`preheat_batch`）：启动全部单元前 `CreatePreCacheImageTask` 全部镜像 + `DescribePreCacheImageTask` 轮询 Success，把「镜像分发」与「实例拉起」两阶段解耦；探针周期 3000→1000ms |
| 验证 | 对照批（20 单元满并发 + `--no-agent` 隔离 LLM）：预热 12s + 就绪 **~9.3s/个匀速**，全批 **3 分 22 秒**（29min → 3.4min，**8.6 倍**） |
| 备注 | 对照批镜像已有部分节点缓存；全新镜像场景预热阶段会体现为 2-5 分钟一次性分发，端到端仍显著优于挤带宽模式 |
| 教训 | **平台三个动作的耗时量级**：工具注册 ~1s ｜ 实例拉起（热）~5-9s ｜ 实例拉起（冷×N 并发）60-200s——批量任务的镜像分发必须前置成独立阶段 |

## K7 探针参数平台硬限制

| 项 | 内容 |
|---|---|
| 现象 | `ReadyTimeoutMs=120000` 被 API 拒绝：`Probe: ReadyTimeoutMs must be at most 30000` |
| 根因 | 平台硬限制：`ReadyTimeoutMs` ∈ [1000, 30000]，`ProbeTimeoutMs/ProbePeriodMs` ∈ [100, 30000]，`SuccessThreshold` 固定 1 |
| 解决 | 回退 30000；`ProbePeriodMs/ProbeTimeoutMs` 调 1000（合法下限之上，单工具省 ~2.5s） |
| 教训 | 参数边界以 `agr` CLI 文档字段表为准（与 Cloud API 同源） |

## K8 LLM 配额耗尽（402 Payment Required）

| 项 | 内容 |
|---|---|
| 现象 | 满并发批 12/20 单元 solver 报 `error`，`turns=None`；最早 2 个单元正常（6/17 轮） |
| 根因 | 20 并发 agent 解题烧钱速率超 TokenHub 余额——每单元 10-20 轮 × 2-4k token/轮，约十几分钟耗尽；402 后 solver 降级 error |
| 影响 | 仅影响 agent 解题（pass@1）与失败分析；**Phase A 标准答案核验不依赖 LLM，照常完成**（14 validated + 6 rejected） |
| 解决 | 运维前置：满并发任务前确认 LLM 配额（预估公式：并发数 × 15 轮 × 3k token）；中期可加 402 识别→自动降并发续跑 |
| 教训 | LLM 是全链唯一**按量消耗型**外部依赖，满并发前必须做配额预算，否则指标（pass@1）静默失真 |

## K9 TCR 令牌 ~1.5h 过期（周期性）

| 项 | 内容 |
|---|---|
| 现象 | 本轮攻坚中 3 次 push 401（制作镜像、重打 tag 时） |
| 根因 | TCR 实例令牌实测有效期 ~1.5h（非 24h） |
| 解决 | maker 驱动每批自动刷新（已内置）；**CVM 侧手动 docker 操作**（重打 tag 等）需先 `CreateInstanceToken` 再 login——本次 3 次手动刷新即此场景 |
| 教训 | 长会话运维脚本统一走「用前刷新」模式，不依赖缓存的 `/tmp/tcr_token.json` |

---

## 300 题批量任务前置 Checklist（卡点反推）

- [ ] LLM 配额充值/提额（按 25 并发 × 15 轮 × 3k token 预估，并留 50% 余量）
- [ ] GitHub Token ×2 轮换（300 题 ≈ 6000 调用 > 单 Token 5000/h）
- [ ] 全部镜像 tag 唯一性巡检（防存量碰撞类静默损坏）
- [ ] 批次级预热启用（默认已开；预热失败单元会在日志单独列出）
- [ ] TCR 令牌自动刷新确认（maker 已内置；手动运维用前刷新）
- [ ] 发现池健康度（当前可用仓库：click/rich/requests/packaging/pytest，环境不兼容黑名单：marshmallow/attrs/aiohttp）
- [ ] 工具配额水位监控（30 上限：常驻 2 + 临时 ≤27；实例配额 50 → 并发对数 ≤25）

## 修复版本索引

| 版本 | 内容 |
|---|---|
| maker v1.1.2 | K4 makedirs 回归修复 |
| maker v1.1.3 | K3 tag 秒级+题号唯一化 |
| validator（本轮） | K1 DONE 全终局、K2 本批过滤、K5 换名重试、K6 preheat_batch + 探针 1000ms |
| run_5.sh | K2 ③⑤ 步修正 + 空批提示 |
