# 压测准备快照（2026-09-15）

## 环境
- CVM: 5.15.0-181-generic | 2 vCPU | 3.6Gi RAM | 磁盘 19G 可用
- AGS 区域: ap-singapore | 工具配额: 1/10 已用（bench-maker-ds ACTIVE）
- 实例并发配额: ≈50（实测边界）
- v2 架构: CVM 中心化编排，agent1=bench-maker-ds(每题镜像)，agent2=validator_driver(tccli 每题临时工具)
- TCR: benchmark-upload-sicheng.tencentcloudcr.com（令牌驱动自动刷新，实测有效期~1.5h）
- LLM: TokenHub → deepseek-v4-flash（题目改写）

## 数据基线
- 既有数据集: 5 条（4 条 v1 shared-carrier + 1 条 v2 镜像）
- 本轮目标: 新发现并制作 ≥20 个每题镜像 + 全量验证
