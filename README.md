# AGS Benchmark Orchestrator

基于腾讯云 Agent Runtime（AGS / Agent Sandbox，E2B 兼容）的**高并发 benchmark 自动化生产线**：
从 GitHub 真实 issue 出发，全自动制作、构建、验证、入库 benchmark 题目镜像，
全链沙箱化执行，CVM 编排中心化管控。

---

## 一、系统架构（v2：CVM 中心化编排）

### 1.1 架构总览

```
┌───────────────────── CVM 编排中枢（无状态，可多副本）─────────────────────┐
│                                                                        │
│   maker_driver（制作编排）              validator_driver（验证编排）        │
│   · SandboxPool  异步沙箱池（预热+背压）    · tccli 创建/销毁每题临时工具       │
│   · ClaimStore   L1 任务互斥              · AcquireSandboxInstanceToken    │
│   · Dataset      L2 双键去重              · ① agent 解题 → pass@1           │
│                                        · ② 标准答案核验（Phase A）        │
│                                        · ③ agent 答错 → 对比分析          │
└────────┬─────────────────────────────────────────┬─────────────────────┘
   E2B 数据面│（commands / files）          tccli 控制面 + E2B 数据面│
             ▼                                       ▼
┌───────────────────────────┐       ┌────────────────────────────────────┐
│ ① agent1 制作沙箱（固定工具）   │       │ ④ agent 沙箱 bench-solver（固定工具）    │
│    bench-maker-ds × N 并发   │       │    ⑤ 题目沙箱 bench-u-*（每题临时）      │
│    PUBLIC 网络                │       │      SANDBOX 隔离 · 验证后即删           │
│                             │       └──────┬──────────────▲──────────────┘
│    制作漏斗：                 │              │实例Token(sit_)│ 直访（X-Access-Token）
│    issue–PR 配对              │      ┌─────────────────┴──────────────┐
│    → clone + venv            │      │ ③ TCR 镜像仓库（两层结构）           │
│    → F2P 双向验证 ×2 轮       │─────▶│   共享基座 benchmark-ds-base      │
│      + 跨轮稳定性筛选          │ ② 构建 │   + 每题内容层（kaniko 构建          │
│    → DeepSeek 题面改写        │  推送  │     + crane 推送，digest 固定）     │
│    → 镜像构建 + 推送           │      └────────────────────────────────┘
└───────────────────────────┘
┌─────────────────────── ⑤ 数据存储层（状态外置）────────────────────────┐
│  [GitHub 仓库] dataset.jsonl 题目索引 · units/ 单元证据 · claims 互斥账本   │
│  [TCR] 基座与每题镜像（不可变，digest 引用）  [COS] 多副本分片（可选）       │
└─────────────────────────────────────────────────────────────────────────┘
```

> 编排与执行彻底分离：**沙箱只与 CVM 通信**（E2B 数据面），CAM 凭据零进入沙箱。

### 1.2 组成部分详解

**① CVM 编排中枢（`src/drivers/` + `src/pool/` + `src/dedup/`）**

一切控制逻辑的唯一驻地，无状态、可多副本、可横向扩展：

| 组件 | 职责 |
|---|---|
| `maker_driver` | 制作编排：刷新 TCR 令牌 → 逐单元认领 → 池取沙箱 → 注入环境变量下发任务 → 收集产物入库 |
| `validator_driver` | 验证编排：`tccli` 为每题创建临时工具 → 拉起实例 → Phase A 判定（answer ×N 轮一致 + baseline 负向对照）→ （可选）Phase B LLM 解题 → 销毁工具归还配额 |
| `SandboxPool` | 异步沙箱池：预热实例即取即用（**acquire 等待实测 0ms**）、信号量背压、配额退避 |
| `ClaimStore`（L1） | 任务互斥：flock（单机）/ COS 条件写（多副本），防同单元并发执行，含 3h 陈旧锁自愈 |
| `Dataset`（L2） | 双键去重（instance_id + issue_url），保证结果不重复入库 |

**② agent1 制作沙箱（固定工具 `bench-maker-ds`，PUBLIC 网络）**

单个 AGS 实例内完成一道题的完整制作（实测 **≈90 秒/题**）：
配对（GitHub 全套 closing keywords，timeline + 搜索双路）→ 克隆仓库 + venv 环境锁安装 →
F2P 双向验证 ×2 轮 + 跨轮稳定性筛选（防 flaky 误入库）→ DeepSeek 题面改写
（标识符保留率 50–100%，防模型「背答案」）→ kaniko 构建镜像 + crane 推送 TCR。

**③ TCR 两层镜像体系**

`benchmark-ds-base` 共享基座（ubuntu:22.04 + py3.11 + git + pytest + envd，**digest 固定**）
+ 每题内容层（完整仓库 + tests/golden patch + harness，仅 30–100 MB）。
同构题共享基座 → 构建秒级、存储不随题数线性膨胀、天然防 tag 漂移。

**④ agent 沙箱 + 题目沙箱（双沙箱核验单元）**

核验每题时 CVM 同时拉起一对沙箱：**agent 沙箱**（固定工具 `bench-solver`，PUBLIC）承载
AI 解题 agent；**题目沙箱**（每题临时工具 `bench-u-*`，SANDBOX 隔离）承载题目镜像。
CVM 经 `tccli AcquireSandboxInstanceToken` 为题目沙箱签发实例级访问 Token（`sit_`，
~24h），注入 agent 沙箱后，agent 通过 e2b SDK **直访并操作题目沙箱**（URL
`https://49983-<实例ID>.<域名>` + `X-Access-Token` 头）。核验流程：
**① agent 解题 → 记录 pass@1**（在 agent 修复后的仓库状态上裸判定）→
**② 按原流程核验标准答案**（answer ×N 轮一致 + baseline 负向对照）→
**③ agent 答错时对比分析**（agent 修改 vs golden patch diff + 失败测试清单 +
LLM 归因：根因定位/差距本质/难度评级）。实测单题周期 ≈2.5 分钟。

**⑤ 数据存储层（关键数据文件，全部在 GitHub 仓库版本控制内）**

| 数据文件 | 位置 | 存储目标 |
|---|---|---|
| **核心数据集** `dataset.jsonl` | `output/maker/dataset.jsonl` | **题目库主索引**：每条记录含题面、F2P/P2P 测试清单、镜像地址 + 不可变 digest、答案摘要、配对置信度（当前 17 条可用镜像题，F2P 68 / P2P 278） |
| **单元证据包** `units/<题号>/` | `output/maker/units/` | 每题完整可审计证据：`problem.md` 题面、`tests.patch` 测试补丁、`golden.patch` 标准答案、`manifest.jsonl` 镜像清单、`build-report.md`——任意一题可独立复现/审计/重放 |
| **互斥账本** `claims.json` | `output/maker/claims.json` | L1 去重运行凭证（防重复制作，含陈旧锁自愈） |
| **压测档案** | `output/stress/` | 环境快照、发现统计、时间线、终态数据（报告数字可溯源） |

存储分工设计：**Git 管可演化的文本数据**（索引 + 证据，共 ~1.3 MB，可 code review、
历史可回溯）；**TCR 管二进制制品**（镜像，由数据集中的 digest 字段指针引用，不可变）；
**密钥永不入库**（`.env` 经 .gitignore 隔离，已验证仓库零密钥；沙箱凭据命令级注入即焚）。
三层数据任何一环丢失均可由其余两环重建。

**状态外置原则**：互斥、数据集、产物、镜像全部落在 TCR/COS/本地文件，
沙箱内存即焚——任意环节崩溃重跑即恢复（幂等协议），无人工介入。

---

## 二、压测运行情况（2026-09-15，12 并发满载）

### 2.1 关键指标

| 指标 | 实测值 |
|---|---|
| 制作批墙钟 | **25 单元 / 114 秒**（并发 12 + 预热 6） |
| 单单元周期 | **≈90 秒**（v1 架构 ~11 分钟，**提速 7 倍**） |
| 镜像产出 | **17 个入库**（click 11 / rich 4 / requests 2，F2P 68 / P2P 278，digest 三重验证） |
| 池性能 | 实例创建 p50 4.25s，acquire 等待 **0ms** |
| 吞吐推算 | 制作端 ≈400 题/小时 |
| 详细报告 | [docs/STRESS_TEST_REPORT_20260915.md](docs/STRESS_TEST_REPORT_20260915.md) |

### 2.2 压测中发现的问题

| # | 问题 | 影响 | 状态 |
|---|---|---|---|
| P1 | **claim() 并发竞态**：flock 解锁早于缓冲落盘，并发读者读到空文件 → 驱动崩溃 | 首批 24 单元 30 秒全灭 + 15 陈旧锁 | ✅ 压测中热修复（解锁前 flush） |
| P2 | **环境配方缺陷**：env-lock 仅含运行时依赖，缺测试依赖 → attrs/marshmallow 全灭 `ImportError`；aiohttp 全灭 C 扩展构建失败 | **43.6% 漏斗损失**（最大瓶颈） | 待修（O1：依赖组纳入 + 沙箱探针预检） |
| P3 | nohup 驱动随命令会话结束被杀 | 1 单元孤儿实例 + claim 残留 | 待修（O4：setsid + finalizer） |
| P4 | 孤儿实例清理仅 3/12 成功 | 9 实例靠 2h 超时自灭 | 待修（并入 O4） |
| P5 | 补丁 500 行上限误杀 2 个合法单元 | 池子缩水 | 待修（O6：上限调 700） |

---

## 三、Scale Up 路径与瓶颈

### 3.1 三段扩展模型

```
产出上限 = min(发现端, 制作端, 验证端)

发现端（CVM，GitHub API）：Token 5000 次/h ≈ 500 题/h        ← 不是瓶颈
制作端（AGS 实例并发）：  12 并发 ≈ 400 题/h（40 并发 ≈ 1300 题/h）← 次瓶颈
验证端（双沙箱对并发）：  25 对 × 2.5 min/题 ≈ 600 题/h      ★ 受实例配额 50 封顶
```

**横向扩展（多副本）零代码改动**：任意新机器跑同一驱动命令（`--worker` 换名）+
`CLAIM_BACKEND=cos`，即全局去重、无需副本间协调协议——这是无状态设计直接兑现的扩展能力。

### 3.2 瓶颈所在（按优先级）

| 层级 | 瓶颈 | 现状 | 突破路径 |
|---|---|---|---|
| **★1** | **实例并发配额 ≈50**（验证端顶格 25 对） | 工具配额已提升至 30（2026-09-16 工单落地），验证吞吐 ≈600 题/h 由实例数封顶 | 商务提升实例配额（50→100 即验证 1200/h）；或 maker/solver 规格瘦身降单题周期 |
| 2 | 环境配方损耗 | 43.6% 候选死于测试依赖缺失/C 扩展构建 | O1 修复后制作端有效吞吐近乎翻倍（成本极低） |
| 3 | 制作端并发 | 当前 12 并发仅用配额 1/4 | 配额内即可扩至 40（已标定：5→40 并发线性，30.4x 加速） |
| 4 | 发现产出率 16.7% | 优质池易枯竭（仓库文化差异） | 候选池常驻服务 + GraphQL 批量 + 多 Token |

### 3.3 容量对照（当前配额 vs 配额提升后）

| 场景 | 当前（50 实例/30 工具） | 提升后（预估） |
|---|---|---|
| 制作 | ≈400 题/h（12 并发） | ≈1300 题/h（40 并发，配额内） |
| 验证 | **≈600 题/h**（25 对满并发） | ≈1200 题/h（实例配额 100） |
| 全链 | **≈400 题/h（受制作端限制）** | ≈1200 题/h |

---

## 文档

- **AGS 调用教学文档：[docs/AGENT_RUNTIME_GUIDE.md](docs/AGENT_RUNTIME_GUIDE.md)**（tccli 控制面 + E2B 数据面，含 17 条实测坑位速查表）
- **卡点与解决方案：[docs/BOTTLENECKS_20260916.md](docs/BOTTLENECKS_20260916.md)**（满并发攻坚 9 项卡点 + 300 题任务前置 Checklist）
- **Access Token 直访沙箱 Demo：[docs/ACCESS_TOKEN_DEMO_20260917.md](docs/ACCESS_TOKEN_DEMO_20260917.md)**（纯 tccli+curl 命令行直访 benchmark 沙箱，10 步实测手册）
- **AI Agent 工作汇报：[docs/SOLVER_AGENT_REPORT_20260917.md](docs/SOLVER_AGENT_REPORT_20260917.md)**（bench-solver 沙箱 AI Agent：源码/运用方式/运行证据/产出）
- **压测报告：[docs/STRESS_TEST_REPORT_20260915.md](docs/STRESS_TEST_REPORT_20260915.md)**
- 架构设计详档：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 零基础入门：[docs/BEGINNER_GUIDE.md](docs/BEGINNER_GUIDE.md)
- 使用手册：[docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- 排查指南：[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
