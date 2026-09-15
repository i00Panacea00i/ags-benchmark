# 架构设计文档 —— AGS 高并发沙箱 Benchmark 编排架构

| 项 | 值 |
|---|---|
| 版本 | v2.0（2026-09-15 架构修订版） |
| 范围 | agent1（制作）/ agent2（验证）/ 题目镜像 全量部署于 AGS，跨 AGS 验证 |
| 三大设计需求 | 去重检测机制 · 快速横向扩展 · 无状态运行 |
| 数据来源 | 主项目实测：25+ 生产坑位、5→40 并发标定、多单元端到端数据 |

> **v2 修订（项目要求）**：① agent1 直接制作**每题完整镜像**并上传 TCR（撤销内容注入模式）；
> ② agent2 验证时为每题**单独创建包含 benchmark 镜像的临时沙箱工具**，验证后删除；
> ③ **工具创建/销毁由 CVM 上的 tccli 执行**，沙箱只与 CVM 通信（E2B 数据面），
> CAM 凭据零进入沙箱（编排中心化）。v1 的注入式设计见 git 历史。

---

## 1. 架构概述

### 1.1 目标拓扑（v2：CVM 中心化编排）

| 角色 | 位置 | 职责 |
|---|---|---|
| **agent1（maker）** | AGS 实例 `bench-maker-ds`（PUBLIC） | 单元制作：配对→漏斗→F2P→DeepSeek 改写→**每题镜像构建推送 TCR** |
| **agent2（validator）** | **CVM 驱动器**（`src/drivers/validator_driver.py`） | 工具生命周期（tccli）+ Phase A/B 判定 + DeepSeek 解题链 |
| **题目沙箱** | AGS 临时工具实例 `bench-u-*`（SANDBOX 隔离） | 承载每题镜像（内容烧入），验证执行体，用完即删 |

**镜像两层结构**：`benchmark-ds-base`（共享固定层：ubuntu:22.04+py3.11+git+DockerCLI+
pytest+envd，digest 固定）→ 每题镜像 `FROM base + COPY benchmark 内容层`（kaniko 秒级
构建，TCR 仅存内容差异）。内容**物理烧入**每题镜像（非运行时注入）。

---

## 2. 总体架构图

**图 2-1：总体架构（分层与数据流）**

```
┌────────────────────── 编排层（无状态，可多副本）──────────────────────┐
│  maker_driver / validator_driver（本仓库 src/drivers/）                │
│  ┌──────────────┐ ┌───────────────┐ ┌──────────────────────────────┐ │
│  │ SandboxPool   │ │ ClaimStore    │ │ Dataset/ShardWriter          │ │
│  │ 池+信号量背压  │ │ L1 去重互斥    │ │ L2 双键去重 + 分片            │ │
│  │ (src/pool/)   │ │ (src/dedup/) │ │ (src/dedup/)                 │ │
│  └──────┬───────┘ └──────┬────────┘ └──────────┬───────────────────┘ │
└─────────┼────────────────┼─────────────────────┼─────────────────────┘
    E2B 数据面│         状态外置 │                │ 产物/结果
             │(ap-*.tencentags.com)              │
┌────────────▼──────────────── AGS 执行层 ───────▼──────────────────────┐
│                                                                      │
│  ① agent1 池（PUBLIC）          ② agent2 池（PUBLIC）                  │
│  ┌──────────────────┐          ┌──────────────────────────────┐      │
│  │ maker 沙箱 × N    │          │ validator 沙箱 × N            │      │
│  │ 镜像内制作逻辑     │          │  · 接收单元包注入(/work)       │      │
│  │ → TCR 镜像推送    │          │  · 跨 AGS 拉起题目沙箱 ──────┐  │      │
│  │ → 单元产物打包     │          │  · 回读 verdict(/output)    │  │      │
│  └──────────────────┘          └──────────────────────────┼──┘      │
│                                                           │         │
│  ③ 题目沙箱池（SANDBOX 隔离网络）◀── 内容注入(files 控制面) ─┘         │
│  ┌────────────────────────────────────────────────────┐           │
│  │ bench-base 基座 + 注入: repo.tar.gz/tests/golden     │           │
│  │ manifest / harness 协议执行 / 用完即销毁              │           │
│  └────────────────────────────────────────────────────┘           │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌────────────────────── 状态外置层 ──────▼──────────────────────────────┐
│  [TCR 企业版] 基座/工具镜像(digest 固定)   [COS] 单元包/claim/结果分片    │
│  [COS] registry.json 双键缓存   [本地/Redis] flock claim（单机模式）     │
└───────────────────────────────────────────────────────────────────────┘
```

> 数据流总纲：`单元清单 →(L1 去重)→ 池 acquire → agent 沙箱执行 →(跨 AGS/
> 镜像构建)→ 产物 →(L2 去重)→ 外置存储`。三条横向流互不共享本地状态。

---

## 3. 跨 AGS 验证设计（核心机制）

### 3.1 时序图

**图 3-1：跨 AGS 验证流（validator_driver → agent2 沙箱 → 题目沙箱）**

```
driver          agent2 沙箱           题目沙箱(bench-base)      外置存储
  │ claim L1 ───────────────────────────────────────────────▶ claims/
  │ pool.acquire() → validator 实例
  │── files.write(单元包 /work/) ──▶
  │── commands.run(validator_agent, envs={E2B_KEY, BENCH_TOOL}) ─▶
  │                                  │ Sandbox.create(bench-base) ──▶ ①拉起
  │                                  │ files.write(内容注入) ───────▶ ②注入
  │                                  │ run_tests answer×N ─────────▶ ③验证
  │                                  │ run_tests baseline ─────────▶ ④负向
  │                                  │ kill() ─────────────────────▶ ⑤销毁
  │◀── files.read(verdict) ──────────│
  │── L2 去重 → 结果分片 ───────────────────────────────────────▶ results/
  │ pool.release()
```

### 3.2 网络模式矩阵

| 沙箱 | 模式 | 出网需求 | 入向控制 |
|---|---|---|---|
| agent1 maker | PUBLIC | GitHub / PyPI / TCR 公网端点 | 仅数据面 API |
| agent2 validator | PUBLIC | **E2B 数据面域名**（拉起题目沙箱） | 仅数据面 API |
| 题目 bench | **SANDBOX** | **无**（内容已注入，验证语义全离线） | 仅 files/commands 控制面 |

关键点：SANDBOX 隔离的是**数据面出网**；`files.write`/`commands.run` 走 envd 控制面
（49983），**不受隔离影响**——这正是内容注入模式在离线验证下可行的原理。

### 3.3 凭据最小化矩阵

| 凭据 | 持有者 | 注入方式 | 生命周期 |
|---|---|---|---|
| E2B_API_KEY | driver → agent2 沙箱 | `commands.run(envs=...)` 命令级 | 随命令进程 |
| TCR 令牌 | driver → agent1 沙箱 | 同上；每批经 `CreateInstanceToken` 刷新 | ~1.5h（实测） |
| GITHUB_TOKEN | driver → agent1 沙箱 | 同上 | PAT 有效期 |
| COS 密钥 | **仅 driver**（多副本模式） | 不入沙箱 | — |
| CAM RoleArn | AGS 平台侧（工具属性） | 工具创建时绑定 | 工具级 |

---

## 4. 三大设计需求实现

### 4.1 去重检测机制（四层防线）

**图 4-1：去重层次**

```
L0 内容指纹   unit 定位键 = repo#issue → instance_id（结构确定性生成）
     │          同一 issue 永远产出同一 instance_id
L1 任务互斥   ClaimStore.claim()：flock（单机）或 COS 条件写（多副本）
     │          in-flight 租约 + 3h 陈旧锁自动回收（崩溃 Worker 自愈）
L2 结果双键   instance_id 唯一 + issue_url 唯一（跨实例重复防线）
     │          分片模式下由 registry 预检 + 离线合并兜底
L3 镜像层复用  内容注入模式下题目镜像唯一（基座 digest 固定），
              天然杜绝「同题多镜像」冗余
```

| 层 | 防什么 | 后端 | 代码 |
|---|---|---|---|
| L0 | 键生成歧义 | 确定性拼接 | manifest 生成协议 |
| L1 | 同单元并发/重复执行 | flock / COS `If-None-Match:*` | `src/dedup/claim.py` |
| L2 | 结果重复入库 | 双键集合 + 原子追加 | `src/dedup/dataset.py` |
| L3 | 镜像冗余 | 基座 digest 固定 | `images/Dockerfile.bench_base` |

多副本语义：L1 切 `CLAIM_BACKEND=cos` 后，N 个 driver 副本对同一单元只有一方
claim 成功，其余立即跳过——**无需任何副本间协调协议**。

### 4.2 快速横向扩展（scale out）

**扩展公式**（实例数）：

```
maker 批量:      实例峰值 = concurrency(maker)
validator 批量:  实例峰值 = concurrency(validator) × 2   ← validator + 其拉起的 bench
                 （例：并发 8 → 16 实例，配额边界 50 内）
```

**扩展操作**（零代码改动）：
1. 单机纵向：调大 `--concurrency`（≤40，标定值）；
2. 多机横向：任意新机器/Pod 跑同一 driver 命令（换 `--worker` 名），
   `CLAIM_BACKEND=cos` 即全局去重；
3. 配额提升后：`ramp_test.py` 重新标定 → 更新并发上限常量。

**标定数据**（实测，ap-singapore / 预热镜像）：

| 并发 | 成功率 | 加速比 | 吞吐 | 创建延迟 P50 |
|---|---|---|---|---|
| 5 | 5/5 | 4.6x | 1.1/s | 4.2s |
| 10 | 10/10 | 9.0x | 2.2/s | 4.2s |
| 20 | 20/20 | 17.8x | 4.2/s | 4.2s |
| 40 | 40/40 | 30.4x | 7.2/s | 4.3s |
| 60 | 50/60 | — | — | 配额边界（LimitExceeded） |

池化后 acquire 等待 **0ms**（预热实例即取即用）——拉取延迟已从关键路径剔除。

### 4.3 无状态运行

**状态外置清单**：

| 状态 | 存放 | 本地是否有副本 | 恢复方式 |
|---|---|---|---|
| 单元互斥（L1） | flock 文件 / COS 对象 | flock 模式有 | 陈旧锁 3h 自动回收 |
| 数据集（L2） | 本地 JSONL / COS 分片 | 分片为本副本私有 | 离线合并幂等 |
| 单元包（产物） | COS / artifacts 目录 | 临时 | manifest 可重放 |
| 镜像 | TCR（digest 固定） | 无 | 不可变 |
| 沙箱内一切 | 实例内存/临时盘 | **无**（用完即毁） | 无需恢复 |

**幂等协议**：任意环节崩溃 → 重跑同命令即可。L1 租约过期自动回池；L2 双键保证
不重复入库；TCR push 以 digest 幂等。**"重试即恢复"，无人工介入。**

---

## 5. 组件与代码映射

| 组件 | 文件 | 说明 |
|---|---|---|
| 异步沙箱池 | `src/pool/sandbox_pool.py` | 预热+信号量+退避+配额背压+指标 |
| 并发标定 | `src/pool/ramp_test.py` | 阶梯压测（扩容后复用） |
| L1 去重 | `src/dedup/claim.py` | FlockClaimStore / CosClaimStore |
| L2 去重 | `src/dedup/dataset.py` | LocalDataset / CosShardWriter |
| agent2 验证器 | `src/agents/validator_agent.py` | 跨 AGS Phase A 判定（沙箱内运行） |
| agent1 驱动 | `src/drivers/maker_driver.py` | 池化制作编排（无状态） |
| agent2 驱动 | `src/drivers/validator_driver.py` | 池化跨 AGS 验证编排（无状态） |
| agent2 镜像 | `images/Dockerfile.validator` | 基座 + e2b SDK + 验证 agent |
| 题目基座镜像 | `images/Dockerfile.bench_base` | 基座 + 工具链 + harness（内容注入） |
| 工具部署 | `deploy/create_tools.sh` | 三工具一键创建 + 预热 |
| 配置模板 | `deploy/env.example` | 全量环境变量 |

---

## 6. 容量规划

| 场景 | 公式 | 当前配额（50 并发实例）下 |
|---|---|---|
| maker 吞吐 | 40 并发 ÷ 10min/单元 | ~240 单元/小时 |
| validator 吞吐 | C 并发 → 2C 实例 → C≤25 | ~300 单元/小时（5min/单元） |
| 更高目标 | 商务提升并发实例配额 → 重标定 | ramp_test.py 复用即可 |

---

## 7. 安全边界

- 沙箱凭据面：agent2 仅 E2B key；agent1 另持 TCR/GitHub；**COS 永不进沙箱**；
- 所有凭据经 `commands.run(envs=...)` 命令级注入，随进程生命周期销毁，不落盘；
- 题目沙箱（不可信内容执行体）运行于 SANDBOX 隔离网络，无出网能力；
- TCR 镜像一律 digest 固定引用，防 tag 漂移。

---

## 8. 演进路径

| 阶段 | 内容 | 状态 |
|---|---|---|
| P0 | 单机 flock + 单元制作管线全链验证 | ✅（主项目） |
| P1（本仓库） | 全 AGS 化 + 跨 AGS 验证 + 池化编排 | ✅ 设计+组件 |
| P2 | CLAIM_BACKEND=cos 多副本生产化 + K8s Operator 化 | 待实施 |
| P3 | 预热池常驻服务 + 配额扩容后重标定至 40+ | 商务依赖 |

---

*维护说明：图表（图 2-1/3-1/4-1）与正文 §2/§3/§4.1 一一对应；组件变更需同步
§5 映射表与 docs/TROUBLESHOOTING.md。*
