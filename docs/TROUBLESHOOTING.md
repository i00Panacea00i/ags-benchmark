# 问题排查指南

> 全部条目来自本架构组件在真实环境中的实测记录（2026-09 主项目 17+ 坑位库），
> 按现象分类索引：**认证 / 配额 / 工具与镜像 / 沙箱内执行 / 跨 AGS / 去重与性能**。

---

## A. 认证类

### T01 `401 Unauthorized / Invalid API key`（E2B）
- **现象**：`Sandbox.create` 抛 `AuthenticationException`
- **根因**：API Key 失效（过期/轮换）——实测曾隔夜失效
- **处置**：AGS 控制台 → API Keys 重建 → 更新 `deploy/.env`。
  注意 Key 与地域数据面域名需匹配。

### T02 TCR 推送 401（maker 流程）
- **现象**：kaniko/crane push 报 `HEAD .../manifests/: 401`
- **根因**：**TCR 实例令牌实测 ~1.5h 过期**（非文档 24h）
- **处置**：driver 已内置每批自动刷新（`tccli CreateInstanceToken`）；
  手工场景先刷新再 `docker login`。

---

## B. 配额类

### T03 工具创建后状态 `FAILED`，实例创建报 409 `SandboxTool is not active`
- **现象**：`ResourceUnavailable.SandboxTool ... status: FAILED`
- **根因**：创建工具时引用的镜像尚未推送成功——平台校验失败且**不自愈**
- **处置**：先 `docker push` 镜像 → 删除工具重建 → 轮询 ACTIVE。
  红线：**构建链中 push 失败必须中止后续步骤**。

### T04 `400 LimitExceeded.SandboxInstance: quota exceeded`
- **现象**：批量拉起时部分实例创建失败
- **根因**：账号并发实例配额（实测边界 ≈50）
- **处置**：池已内置配额背压（等待 20-30s 重试）；若持续出现则降低
  `--concurrency`；validator 场景记住**实例数 = 并发 × 2**。

### T05 实例创建超时（`FailedOperation.Timeout`）
- **现象**：创建长时间无响应最终超时
- **根因**：镜像未预热（冷启动拉大镜像）或工具配置缺 49983 探针
  （历史案例：缺 envd 端口/健康探针导致永远不就绪）
- **处置**：`CreatePreCacheImageTask` 预热；核对工具配置含
  `envd:49983 + /health 探针`（见 `deploy/create_tools.sh` 标准参数）。

---

## C. 工具与镜像类

### T06 `init command path error`
- **根因**：① 镜像未基于 AGS 官方基座（缺 `/init`/envd）；② 启动命令带参数
  未拆分填写
- **处置**：镜像 `FROM ccr.ccs.tencentyun.com/ags-image/sandbox-code:*`；
  启动命令 `/init`，参数分框 `sleep`、`infinity`。

### T07 自定义镜像规范红线（任一违反即启动异常）
- 不覆盖 `WORKDIR`（须为 `/`）、`USER`（root）、`ENTRYPOINT`（/init）
- 必须暴露 envd TCP 49983 并配 `/health` 探针
- 详见 `images/Dockerfile.*` 头部注释

### T08 镜像 digest 漂移
- **处置**：所有镜像引用一律 `name:tag@sha256:…` 双重固定；
  工具重建时核对 digest 一致。

---

## D. 沙箱内执行类（maker 场景为主）

### T09 构建产物静默缺件（**最隐蔽**）
- **现象**：镜像内 `jq/git: not found` 或 `libjq.so.1` 缺失，但构建本身成功
- **根因**：**kaniko 快照基线污染**——kaniko 在富容器内运行时，沙箱根文件系统
  预置的同版本同路径文件在 RUN 后"无变化"，被 diff 丢弃
- **处置**：kaniko 前 purge 目标包及依赖闭包（`apt-get purge + autoremove
  --purge`）净化基线；构建后 `crane export` 校验关键二进制/库在位。
  （主项目 v2.2.7+ 已内置，本仓库 maker 镜像继承。）

### T10 kaniko 推送阶段 401（构建阶段正常）
- **根因**：社区版 kaniko 多阶段构建的推送阶段凭据链缺陷（file provider 丢失）
- **处置**：**职责拆分**——kaniko 只 `--no-push --tar-path` 出 tar，
  crane 负责推送/组合（`push/append/mutate`）。

### T11 同沙箱第二次 kaniko 构建中断
- **根因**：双次基础镜像解包叠加
- **处置**：组合类产物改 `crane append + mutate` 纯 registry 操作（零解包）。

### T12 files API 报 `unknown user user`
- **根因**：kaniko 解包覆盖沙箱 `/etc/passwd`，envd 默认用户查找失败
- **处置**：files 读写显式 `user="root"`（本仓库 driver 均已带）。

### T13 沙箱 `/tmp` 文件在构建后消失
- **根因**：kaniko 构建过程清理 `/tmp`
- **处置**：运行期文件一律放 `/output` 等非镜像层路径。

### T14 pytest 收集 0 用例（误判 untestable）
- **根因**：① 仓库测试依赖未装（如 pretend）；② pytest 9 对旧式测试构造
   升级为收集错误
- **处置**：安装仓库测试依赖（requirements / PEP 735 `dependency-groups.test`）；
  pytest 固定 `<9`（随 env-lock 流入镜像保持一致）。

---

## E. 跨 AGS 类（validator 场景）

### T15 validator 沙箱内 `Sandbox.create` 失败
- **排查顺序**：① E2B_API_KEY 是否经 `envs` 注入（命令级，非环境全局）；
  ② validator 工具网络模式必须 **PUBLIC**（SANDBOX 模式无法触达数据面域名）；
  ③ BENCH_TOOL 名称存在且 ACTIVE。

### T16 题目沙箱（SANDBOX 模式）files 注入失败？
- **原理确认**：SANDBOX 隔离的是**数据面出网**；`files/commands` 走 envd
  控制面（49983），**不受影响**。若失败，检查题目基座镜像是否含 envd
  （必须 AGS 官方基座）与探针配置。

### T17 verdict 回读为空
- **根因**：agent 非 0 退出但 stdout 未含 `VERDICT {...}`（agent 内异常被吞）
- **处置**：driver 会记 `error` 并保留 stdout 尾部；单测该单元：
  手工在 validator 沙箱执行 `/opt/validator/validator_agent.py` 看完整栈。

---

## F. 去重与性能类

### T18 单元被 L1 拦截但从未成功
- **根因**：上次崩溃残留 `in-flight`
- **处置**：3h 陈旧锁自动回收（两种后端一致）；紧急可手工将 claim 状态
  改为 `failed`（可重抢）。

### T19 多副本出现重复入库
- **前置检查**：`CLAIM_BACKEND` 是否为 `cos`（flock 仅单机有效）；
  CosClaimStore 依赖条件写（`If-None-Match:*`）；L2 双键是最后防线，
  分片模式下由离线合并兜底去重。

### T20 并发上不去但无报错
- **检查**：信号量上限（`--concurrency`）、池预热水位（`--warm`）、
  配额水位（`LimitExceeded` 重试计数在池指标 `retries` 中）。
  扩容配额后重跑 `ramp_test.py` 标定。

---

## 快速分诊表

| 症状 | 首查条目 |
|---|---|
| 创建/认证失败 | T01 / T03 / T05 |
| 推送 401 | T02 / T10 |
| 实例部分失败 | T04 |
| 镜像缺文件/库 | T09 |
| 0 用例收集 | T14 |
| 跨 AGS 不通 | T15 / T16 |
| 重复执行/入库 | T18 / T19 |
