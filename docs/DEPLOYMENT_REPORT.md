# DS Harness 多智能体架构部署验证报告

| 项 | 值 |
|---|---|
| 日期 | 2026-09-15（v2 架构修订） |
| 版本 | benchmark-dsharness **1.1.0** + benchmark-ds-base 1.0.0（共享基座） |
| v2 架构 | **CVM 中心化编排**：tccli 建删每题临时工具；agent1 每题镜像烧入 TCR；agent2 逻辑在 CVM |
| 运行环境 | ubuntu:22.04 + Python 3.11 + Git + Docker CLI + 官方 envd（AGS 兼容层） |
| LLM | TokenHub → deepseek-v4-flash（改写 85-100% 标识符保留；Phase B 文本协议解题） |

---

## 〇、v2 架构修订（应项目要求）

| 修订 | 内容 | 动机 |
|---|---|---|
| 撤销内容注入 | agent1 直接制作每题完整镜像并上传 TCR（两层：共享基座+内容层） | 项目要求 |
| 每题临时工具 | agent2 验证时为每题创建 `bench-u-*` 沙箱工具（含题目镜像），验证后删除 | 项目要求 |
| 编排中心化 | 工具创建/销毁由 CVM 上的 tccli 执行，沙箱只与 CVM 通信（E2B 数据面） | 凭据零进入沙箱 |

**v2 E2E 实证**：click#3145 全链（DeepSeek 改写 85% → 每题镜像构建推送 → CVM 建临时
工具 → Phase A validated → Phase B solver 10 轮 → 工具删除，配额归还 1/10）。

**v2 吞吐约束（实测标定，须汇报）**：工具配额 10/账号 → 固定 1 + 临时 ≤8 并发；
单题周期 ≈4-5min → **≈90 题/小时上限**（v1 注入模式无此限）。孤儿工具清扫已内置。

---

## 一、端到端验证结果

| 链路 | 结果 | 证据 |
|---|---|---|
| **agent1 制作（确定性）** | ✅ | click#3360(F2P 7)/#3277/#3298、packaging#831 等 5 单元入库，DS_HARNESS_MODE 内容注入包（repo.tar.gz + 扁平补丁） |
| **agent1 改写（DeepSeek）** | ✅ | click#3242：`rewrite_method: deepseek-harness(deepseek-v4-flash,标识符保留100%)`（含反馈重试机制） |
| **agent2 Phase A（跨 AGS）** | ✅ | click#3242：`phase_a: validated, rounds: 2`——validator 沙箱内经 E2B API 拉起 bench-ds（SANDBOX 隔离）注入内容并完成双向判定 |
| **agent2 Phase B（DeepSeek 解题）** | ✅ 链路/⏳ 解题率 | solver 15 轮真实解题（探索→复现→定位 `_SkipClose` flush 委托根因），本单元 0/1（G2 闸门正确拒收）；解题率为 prompt/模型调优项，非架构缺陷 |
| **漏斗与去重** | ✅ | L1 claim / L2 双键全周期生效；正确过滤无区分度单元（#3449 等 0-F2P） |

## 二、本次部署发现并修复的问题（新增 8 项，累计 25+）

| # | 问题 | 根因 | 修复 |
|---|---|---|---|
| N1 | `invalid username: 'user'` | 裸 ubuntu 无 E2B 约定的 user 账户（官方基座由 s6 创建） | Dockerfile `useradd -m user`；agent 显式 user="root" |
| N2 | 工具指向旧 digest（symlink/useradd 不生效） | **tag 缓存漂移**：同 tag 重推不保证实例取新 | 一版本一 tag（1.0.x 递增），工具重建指向新 tag |
| N3 | click 单元 4 连灭（0 F2P） | **pip 26 的 `pip install -e 'path[test]'` 将项目重装为非可编辑副本**→golden 补丁改源码而测试 import site-packages 副本 | 测试依赖列表直装（tomllib 解析，绝不让 pip 触碰项目）+ 安装后**可编辑链接验证与自愈** |
| N4 | bench 内 import 错误的包 | pip 依赖遮蔽（pytest 依赖的同名包在 dist-packages 优先于 .pth） | 注入时 `pip3 uninstall -y <repo_name>` + .pth 站点链接 |
| N5 | harness `no tests ran` | `run_tests.sh` 对绝对路径双拼接（`$ROOT/` + `/benchmark/…`）→ git apply 静默失败 | harness 兼容相对/绝对两种补丁路径 |
| N6 | verdict 恒 harness_crash | **解析器嵌套括号 bug**：`rfind("{")` 抓到 fail_to_pass 内层 `{` | 「最后一个行首 `{`」定位汇总 JSON |
| N7 | LLM 改写空内容 | deepseek-v4-flash 为推理型模型，reasoning 耗尽 token 预算 | finish_reason=length 时预算 ×4 重试 |
| N8 | LLM 改写忠实性误拒（40%） | 普通英文单词纳入标识符统计 | 仅校验核心标识符（`.`/`_` 复合词）+ 缺失清单反馈重试 |
| N9 | Phase B 一轮即"完成" | deepseek-v4-flash 不支持原生 function-calling，输出伪 XML | harness **文本协议兜底**：解析 `<execute command="…"/>` 并执行 |

另：TCR 实例令牌 ~1.5h 过期（驱动自动刷新已内置）、工具删除需先清实例（`ResourceInUse`，`Sandbox.connect(id).kill()` 清理）。

## 三、当前资产

- **镜像**：`benchmark-dsharness:1.0.8`（digest `sha256:9b0ac24e…`，一镜像三角色）
- **工具**：bench-maker-ds(1.0.5) / bench-validator-ds(1.0.8) / bench-ds(1.0.6) 均 ACTIVE
- **数据集**：`output/maker/dataset.jsonl`（DS 模式单元，含 LLM 改写题）
- **验证结果**：`output/validate-results.jsonl`（Phase A verdict）
- **代码**：DeepSeek Harness（双协议 agent 循环）+ maker/validator agents + 池化驱动

## 四、待办与建议

1. **Phase B 解题率调优**：prompt 强化「先应用修复再解释」；可试更强调模型；
2. maker/validator 工具版本对齐 1.0.8（当前 maker 1.0.5 功能完备，对齐仅为整洁）；
3. GitHub 推送待提供仓库地址与写权限凭据；
4. 批量运行：`examples/run_maker_batch.sh` + `run_validator_batch.sh`（池化并发 ≤40）。
