# AGS Benchmark Orchestrator

基于腾讯云 Agent Runtime（AGS / Agent Sandbox，E2B 兼容）的**高并发 benchmark 编排架构**：
agent1（题目制作）、agent2（跨 AGS 验证）与题目沙箱**全量部署于 AGS 实例**，
编排器无状态、可横向扩展。

## 三大设计需求 → 实现映射

| 需求 | 实现 | 代码 |
|---|---|---|
| **去重检测机制** | 四层防线：L0 确定性键 → L1 任务互斥（flock/COS 条件写）→ L2 双键去重 → L3 镜像层复用 | `src/dedup/` |
| **快速横向扩展** | 异步预热池（acquire 0ms）+ 信号量背压 + 配额背压；实测 40 并发 30.4x 加速；多副本零协调 | `src/pool/` |
| **无状态运行** | 全部状态外置（COS/TCR/claim），沙箱用完即毁，重试即恢复 | 架构见 docs |

## 核心拓扑

```
编排器(无状态, N 副本) ── E2B 数据面 ──┬─ agent1 池(PUBLIC)  ─ 制作 → TCR/COS
                                       ├─ agent2 池(PUBLIC)  ─ 跨AGS ─┐
                                       └─ 题目沙箱(SANDBOX隔离) ◀─内容注入─┘
```

agent2 沙箱通过 E2B API 在**另一个 AGS 实例**拉起题目沙箱并完成 Phase A 双向验证
（answer ×N 轮一致 + baseline 负向对照）——凭据最小化：沙箱内仅 E2B key。

## 快速开始

```bash
cp deploy/env.example deploy/.env   # 填写 E2B_API_KEY / TCR / ROLE_ARN
bash deploy/create_tools.sh         # 三工具创建 + 预热（先 push 镜像，见手册 §2）
python3 src/pool/ramp_test.py 5 10 20      # 并发标定
bash examples/run_maker_batch.sh           # agent1 批量制作
bash examples/run_validator_batch.sh       # agent2 跨 AGS 批量验证
```

## 目录结构

```
├── docs/
│   ├── ARCHITECTURE.md        # 架构设计（图 2-1/3-1/4-1 与正文对应）
│   ├── USER_GUIDE.md          # 使用手册（部署/运行/扩容/判读）
│   └── TROUBLESHOOTING.md     # 排查指南（T01-T20，全部实测坑位）
├── src/
│   ├── pool/sandbox_pool.py   # 异步沙箱池（预热+背压+退避+指标）
│   ├── pool/ramp_test.py      # 并发标定
│   ├── dedup/claim.py         # L1：flock / COS 条件写
│   ├── dedup/dataset.py       # L2：本地 / COS 分片
│   ├── agents/validator_agent.py  # agent2：跨 AGS 验证（沙箱内运行）
│   └── drivers/               # maker/validator 无状态批量驱动
├── images/                     # agent2 与题目基座镜像 Dockerfile
├── deploy/                     # env 模板 / 工具创建 / 预热
└── examples/                   # 批量运行示例
```

## 关键实测数据（标定于 ap-singapore）

- 创建延迟 5→40 并发**恒定 ~4.2s**（数据面网关完全并行）
- 账号并发实例配额边界 ≈ 50（`LimitExceeded.SandboxInstance`）
- 池化 acquire 等待 **0ms**（预热点火即取）
- 生产参数：maker 并发 ≤40；validator 并发 ≤25（实例数 = 并发 × 2）

## 文档

- **零基础入门：[docs/BEGINNER_GUIDE.md](docs/BEGINNER_GUIDE.md)（小白先读这篇）**
- 架构设计：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 使用手册：[docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- 排查指南：[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)（20 条实测坑位）
