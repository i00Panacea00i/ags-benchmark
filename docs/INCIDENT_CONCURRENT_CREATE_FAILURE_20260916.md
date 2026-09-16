# 事故调查报告：并发创建沙箱实例失败（LimitExceeded.SandboxInstance）

| 项 | 值 |
|---|---|
| 事故编号 | INC-20260916-CCF |
| 版本 | **v2（2026-09-16 21:20 更正版）**——v1 的「STOPPED 终态占配额」结论经复核被推翻，本版为修正后结论 |
| 发生时间 | 2026-09-16 20:40（第一次）/ 20:52（第二次） |
| 影响场景 | 100 题全流程压测·制作阶段（145 候选 / 36 并发） |
| 直接影响 | 制作批两次中断：57 题后崩（A 批）、36 题后崩（B 批，累计 57 题实例生命周期） |
| 状态 | 根因已修正定位；403 已修复；**池补充节流待实施** |

---

## 一、事故概述

100 题压测制作阶段两次崩溃于同一错误：

```
e2b.exceptions.SandboxException: 400: [LimitExceeded.SandboxInstance]
Sandbox instance quota exceeded. Current: 100, Max: 100.
(RequestId: ff054d49… / e7753951…)
```

配额已于当日由 50 提升至 100（工单落地确认），但并发批量创建仍在数分钟内
自耗尽配额。

## 二、时间线

| 时刻 | 事件 |
|---|---|
| 20:36:29 | 制作批 A 启动（145 候选 / 36 并发 + 预热 4） |
| ~20:40 | **批 A 崩溃**：57 题完成（3 成功 / 15 过滤 / 39 error-403） |
| 20:41-20:45 | 初查（v1，含方法缺陷）：E2B 列表 8 RUNNING 清理；平台列表见「20 个 STOPPED」 |
| 20:45 | 循环验证：连续创建 6 实例成功（配额有余量） |
| 20:47:30 | 修复 403 后批 B 启动（v1.1.4：WORK_PR + patch700） |
| ~20:52 | **批 B 再次崩溃**于同一错误（36 题完成：9 成功，403=0） |
| 21:05-21:10 | 循环实验：创建10→kill→30s→创建10→60s→创建10，三轮全成功 |
| 21:15 | **翻页复查：TotalCount=146（141 STOPPED + 5 RUNNING）**——v1 结论被推翻 |

## 三、根因分析（v2 修正版）

### 根因 ①（核心）：kill 异步过渡期占配额，高吞吐下堆积

E2B `Sandbox.kill()` 在 AGS 上映射为 Stop，实例生命周期：

```
RUNNING --kill(异步)--> STOPPING --(~4-5 分钟过渡)--> STOPPED
  ↑ 占配额                ↑ 占配额                     ↑ 不占配额（v2 证实）
```

高并发批次中「单元完成 → kill → 池立即补充新实例」的循环，使
**STOPPING 过渡态堆积**：批 A 完成速率 ~14 题/min × 过渡 ~4.5min ≈ 63 个
STOPPING + RUNNING 池 40 ≈ 100 → 撞顶。与两批崩溃点（57 题实例生命周期）
数学吻合。

### 根因 ②（调查方法缺陷，v1 误判来源）

`DescribeSandboxInstanceList` **默认分页 Limit=20**——v1 调查未翻页，把
第一页的 20 个 STOPPED 当成全部实例，得出「可见 20 vs Current 100 矛盾」
的错误前提，进而误判为「STOPPED 持续占配额」。翻页复核（`--Limit 20
--Offset N` 循环）实得 **TotalCount=146（141 STOPPED + 5 RUNNING）**。

### v1 结论被推翻的铁证

在 146 个实例存在（141 STOPPED）的情况下，循环创建实验（10×3 轮）
**全部成功**——若 STOPPED 占配额，141+5=146 > 100 必然失败。
**故 STOPPED 终态不占配额**；kill 后配额恢复只需等过渡期（~5 分钟），
而非 v1 认为的等待 GC（小时级）。

### 根因 ③（应用侧·伴随发现）：GitHub search 限速打爆（已修复）

批 A 的 39 题 error 全为 `HTTP Error 403`：36 个 maker 沙箱并发执行配对
搜索（search API 单 Token 30/min）瞬间超限。已修复：反向发现器的配对
结果（PR 号）经 `WORK_PR` 环境变量直传 maker，制作端零 search 调用
（批 B 实测 403=0）。

## 四、API 语义测绘（v2 修正）

| API | 实测语义 | 备注 |
|---|---|---|
| E2B `Sandbox.kill()` | 异步停止：RUNNING→STOPPING→STOPPED | **过渡期 ~4-5 分钟占配额；STOPPED 不占** |
| `DescribeSandboxInstanceList` | **默认分页 Limit=20**，需 `--Offset` 翻页 + `TotalCount` 核实 | v1 误判的直接原因 |
| `StartSandboxInstance` | **创建新实例**（参数为 ToolId/ToolName/Timeout） | 名不副实，勿用于恢复 |
| `StopSandboxInstance` | RUNNING→STOPPED | STOPPED 上调用被拒（终态） |
| `DeleteSandboxInstance` | **不存在** | STOPPED 靠平台 GC（实测 2-6 小时） |

## 五、影响评估（修正）

- 压测中断两批，100 题目标当前完成 45/145 候选（12 成功 + 33 过滤）；
- **恢复成本远低于 v1 判断**：kill 后 ~5 分钟过渡期结束配额即回，无需
  等待小时级 GC——「池补充节流」一项改造即可支持单波连续跑完；
- STOPPED 僵尸 GC 慢（2-6h）是独立的资源卫生问题，不阻塞压测。

## 六、修复与缓解（v2 更新）

**已实施**：
1. `WORK_PR` 预配对——制作端零 search（403 根治，批 B 验证）；
2. maker patch 上限 500→700；崩溃残留 claim 重置（88 个）。

**待实施（驱动侧，本周）**：
3. **池补充节流**：单元完成 kill 后延迟 ~5 分钟再补充新实例，或轮询该
   实例脱离 RUNNING 后再补充——消除 STOPPING 堆积，支持单波连续批量；
4. **配额水位背压**：Pool 创建前以翻页 TotalCount 核算活跃实例（RUNNING+
   STOPPING）水位，动态降速；
5. 验证 STOPPING 过渡期的精确时长（当前 ~4-5min 为数学反推，未直测）。

**平台工单建议（降级为非紧急）**：
6. STOPPED 僵尸 GC 周期承诺（2-6h 偏慢，影响资源卫生不影响配额）；
7. ~~DeleteSandboxInstance / 计数一致性诉求~~（v2 结论下不再必要）。

## 七、证据附录

- 崩溃堆栈：`output/stress100/maker.log` / `maker-b.log`（RequestId ff054d49 / e7753951）
- 39×403 明细：`grep '"result": "error"' output/stress100/maker.log`
- **146 复核命令**：`tccli ags DescribeSandboxInstanceList --region ap-singapore
  --cli-unfold-argument --Limit 20`（看 TotalCount）+ `--Offset` 翻页
- 循环实验：创建10→kill→30s→10→60s→10 三轮全成功（21:05-21:10）
- v1 误判现场：默认分页首页 20 个 STOPPED（20:41 / 20:57 两次查询均为 20）

## 七之二、因果链澄清（常见疑问）

**Q：39 个 error-403 是撞顶导致的吗？3+15+39=57 < 100 为何撞顶？**

A：两者是不同系统、不同层级的错误（403=沙箱内 GitHub search 被限流；
撞顶=CVM 侧 E2B SDK 创建实例被 AGS 拒绝），且因果方向相反——
**403 失败风暴加速了撞顶**：

```
403（单 Token search 30/min 被 36 并发打爆）
 → 单元 ~60s 即失败（正常 90-150s）→ kill 速率飙升（~15/min）
 → kill 异步过渡 ~4-5min 才释放配额 → STOPPING 堆积（窗口内 kill 的
   ~50 个全部未释放，270s 过渡 > 240s 批次时长）
 → 配额占用 = RUNNING 36 + STOPPING ~55 + warm 4 ≈ 100 → 撞顶
```

「57 题」是完成计数口径，「100」是实例存量口径（RUNNING+STOPPING）——
实例真实创建数 ≈ 61（57 单元 + warm/补充），叠加过渡期滞留即触顶。
403 时间分布佐证：39 个全部集中于批次前 2/3 时段，后段为 0（配额崩溃
时已无新单元）。

## 八、复盘教训

1. **分页接口必须翻页 + TotalCount**——「列表数量」≠「资源总量」，本次
   20 条默认页直接导致根因误判（v1→v2 修正花了一轮实验成本）；
2. **小样本循环实验只能证明「有余量」，不能证明「全释放」**——配额类
   问题要在接近上限处做实验；
3. 异步生命周期（kill/停止/删除）要按**状态机**建模：占不占配额按状态
   逐态验证，不能笼统归因「终态占配额」。

---

*关联：`docs/BOTTLENECKS_20260916.md`、`docs/AGENT_RUNTIME_GUIDE.md` 坑位表。*
