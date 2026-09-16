# 事故调查报告：并发创建沙箱实例失败（LimitExceeded.SandboxInstance）

| 项 | 值 |
|---|---|
| 事故编号 | INC-20260916-CCF |
| 发生时间 | 2026-09-16 20:40（第一次）/ 20:52（第二次） |
| 影响场景 | 100 题全流程压测·制作阶段（145 候选 / 36 并发） |
| 直接影响 | 制作批两次中断：57 题后崩（A 批）、36 题后崩（B 批） |
| 状态 | 根因已定位；部分已修复；**平台侧缺陷需工单跟进** |

---

## 一、事故概述

100 题压测制作阶段两次崩溃于同一错误：

```
e2b.exceptions.SandboxException: 400: [LimitExceeded.SandboxInstance]
Sandbox instance quota exceeded. Current: 100, Max: 100.
(RequestId: ff054d49… / e7753951…)
```

配额已于当日由 50 提升至 100（工单落地确认），但并发批量创建仍在数分钟内
自耗尽配额，且崩溃时**平台可见实例数与配额计数严重不符**。

## 二、时间线

| 时刻 | 事件 |
|---|---|
| 20:36:29 | 制作批 A 启动（145 候选 / 36 并发 + 预热 4） |
| ~20:40 | **批 A 崩溃**：57 题完成（3 成功 / 15 过滤 / 39 error），池创建实例时配额 100/100 |
| 20:41-20:45 | 泄漏清查：E2B `Sandbox.list` 仅见 8 个 RUNNING（已清）；平台侧 `DescribeSandboxInstanceList` 见 **20 个 STOPPED** |
| 20:45 | 配额验证：清理后**连续创建 6 个实例全部成功**（配额部分可用） |
| 20:47:30 | 修复 GitHub 403 后批 B 启动（v1.1.4，36 并发） |
| ~20:52 | **批 B 再次崩溃**于同一配额错误（首批 36 题完成：9 成功，403=0） |
| 20:53-20:57 | 二次调查：实例面仍 20 STOPPED；Start/Stop 语义试验；API 能力测绘 |

## 三、根因分析（三层）

### 根因 ①（平台侧·核心）：`kill` 语义陷阱——停止 ≠ 销毁

E2B SDK 的 `Sandbox.kill()` 在 AGS 数据面上映射为 **Stop（停止）而非销毁**：

```
kill() → StopSandboxInstance → Status=STOPPED（终态）
```

证据（STOPPED 僵尸样本字段）：
- `Persistent: false`（非持久实例）
- `ExpiresAt: 2026-09-16T15:55`（**过期 5 小时仍未被 GC 回收**）
- 对 STOPPED 调 `StopSandboxInstance` 被拒：*only RUNNING/PAUSING/PAUSED… can be stopped*
- **平台无 `DeleteSandboxInstance` 接口**（tccli ags 全 API 清单核对）→ STOPPED 无法主动清除，只能等 GC

### 根因 ②（平台侧）：配额计数滞留

崩溃时三方数据不一致：配额计数 Current=100，平台实例列表仅 20 STOPPED +
0 RUNNING，E2B 列表仅 8 RUNNING。即**已 kill 实例的配额计数长时间不释放**
（GC 周期 ≥ 数小时）。高并发批次内「完成→kill→池补充创建」的循环使计数
**单调累积**，约 60-70 个实例生命周期后即自耗尽 100 配额——与两批崩溃点
（57 题、36+21=57 题累计）吻合。

### 根因 ③（应用侧·伴随发现）：GitHub search 限速打爆（已修复）

批 A 的 39 题 error 全为 `HTTP Error 403`：36 个 maker 沙箱并发执行
**配对搜索**（search API 单 Token 30/min）瞬间超限。已修复：反向发现器的
配对结果（PR 号）经 `WORK_PR` 环境变量直传 maker，**制作端零 search 调用**
（批 B 实测 403=0）。

## 四、API 语义测绘（本次调查修正的认知）

| API | 实测语义 | 备注 |
|---|---|---|
| E2B `Sandbox.kill()` | 停止（→STOPPED），**非销毁** | 占配额直至 GC |
| `StartSandboxInstance` | **创建新实例**（参数为 ToolId/ToolName/Timeout） | 名不副实，勿用于恢复 |
| `StopSandboxInstance` | RUNNING→STOPPED | STOPPED 上调用被拒（终态） |
| `Pause/ResumeSandboxInstance` | 暂停/恢复（未试验） | 疑似不占 RUNNING 配额，待验证 |
| `DeleteSandboxInstance` | **不存在** | 平台能力缺口 |

## 五、影响评估

- 压测中断两批，100 题目标当前完成 45/145 候选（12 成功 + 33 过滤）；
- **不改代码的情况下**，任何 ≥60 实例生命周期的批量任务都会撞同一堵墙；
- GC 周期实测 >5h——白天连续压测不可行，需分波等待或平台介入。

## 六、修复与缓解

**已实施（应用侧）**：
1. `WORK_PR` 预配对——制作端零 search（403 根治，批 B 验证）；
2. maker patch 上限 500→700（对齐发现端，消除误杀）；
3. 崩溃残留 claim 全量重置（88 个 in-flight 恢复）。

**建议实施（驱动侧，本周）**：
4. **配额水位背压**：Pool 创建实例前轮询 `DescribeSandboxInstanceList`
   计数 + 配额余量，动态降速/暂停补充（防单调累积撞墙）；
5. **分波调度**：单波实例生命周期预算 ≤ 配额×60%（当前 ≤60），波间等待
   GC 释放（以 InstanceSet 计数回升为信号）；
6. Pause/Resume 语义验证：若 PAUSED 不占配额，长等待资源可 Pause 代 kill。

**需平台工单（请您决策提交）**：
7. 诉求 A：提供 `DeleteSandboxInstance`（或 STOPPED 手动清除）接口；
8. 诉求 B：确认 STOPPED 僵尸的 GC 承诺周期（实测 ExpiresAt 过期 5h+ 未回收）；
9. 诉求 C：配额计数与实例列表的一致性（Current=100 vs 可见 20）。

## 七、证据附录

- 崩溃堆栈：`output/stress100/maker.log` / `maker-b.log` 尾部（含 RequestId）
- 39×403 明细：`grep '"result": "error"' output/stress100/maker.log`
- STOPPED 僵尸字段：`tccli ags DescribeSandboxInstanceList`（Persistent/ExpiresAt/StopReason）
- StopSandboxInstance 拒绝报文、StartSandboxInstance 参数表（本报告 §四）
- 配额恢复验证：连续创建 6 实例成功记录（20:45）

---

*关联文档：`docs/BOTTLENECKS_20260916.md`（K 系列）、
`docs/AGENT_RUNTIME_GUIDE.md`（坑位表将补充 kill 语义条目）。*
