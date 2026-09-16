# 腾讯云 Agent Runtime（AGS）调用教学文档

> 面向第一次接触 AGS 的工程师：两条调用通道、可直接复制的命令与代码、以及
> 本项目实测踩过的坑。所有示例均来自本仓库生产代码（`src/drivers/`、`src/pool/`），
> 可直接运行。
>
> 适用版本：tccli + e2b SDK（E2B 兼容数据面）｜区域以 ap-singapore 为例

---

## 〇、概念模型：两个平面、两类资源

调用 AGS 之前先建立一张地图，后面所有命令都挂在这张图上：

```
┌─ 控制面（tccli，腾讯云 CAM 鉴权）─────────────┐   ┌─ 数据面（E2B SDK，E2B_API_KEY 鉴权）────┐
│                                              │   │                                        │
│  沙箱工具（Tool）= 实例的「镜像模板」            │   │  沙箱实例（Sandbox）= 运行中的容器         │
│  · CreateSandboxTool   注册模板                │──▶│  · Sandbox.create(template=工具名) 拉起   │
│  · DescribeSandboxToolList 查看/轮询           │   │  · sb.commands.run(...)  执行命令         │
│  · CreatePreCacheImageTask 预热               │   │  · sb.files.read/write   读写文件         │
│  · DeleteSandboxTool   注销模板                │   │  · sb.kill()             销毁实例         │
│                                              │   │                                        │
└──────────────────────────────────────────────┘   └────────────────────────────────────────┘
```

三句话记住它：

1. **工具是模板，实例是运行体**——先在控制面注册工具（绑定容器镜像），再从数据面
   按工具名拉起任意多个实例；实例用完即毁，工具可长期复用；
2. **tccli 管生命周期，E2B 管运行时**——创建/删除工具、预热用 tccli；对运行中实例
   下发命令、传文件全部走 E2B SDK（兼容开源 E2B 协议，直接 `pip install e2b` 即用）；
3. **两条平面各自鉴权**——tccli 用 CAM 密钥（`tccli configure`），E2B 用 AGS 控制台
   申请的 `E2B_API_KEY`；互不相通，权限可以分离给不同的人/机器。

---

## 一、准备：三个凭据 + 一个镜像

| 凭据 | 获取方式 | 用在哪 |
|---|---|---|
| CAM 密钥对（SecretId/Key） | 访问管理 CAM → API 密钥 | `tccli configure` 一次性配置 |
| `E2B_API_KEY` | AGS 控制台 → API Keys | E2B SDK 环境变量 |
| `RoleArn` 角色 | AGS 控制台授权（拉取私有镜像用） | CreateSandboxTool 参数 |

```bash
pip install tccli e2b
tccli configure            # 依次填 SecretId / SecretKey / 区域如 ap-singapore / 输出 JSON
```

环境变量（数据面）：

```bash
export E2B_DOMAIN=ap-singapore.tencentags.com   # AGS 数据面网关，区域对应
export E2B_API_KEY=e2b_xxxxxxxx                 # 控制台获取
```

**镜像要求**：linux/amd64；内置官方 envd（AGS 兼容层，监听 49983 端口提供
`/health` 与控制面 API）。推送企业版 TCR 后才能注册为工具（顺序不能反，见坑 1）。

---

## 二、tccli 教程（控制面）

### 2.1 注册沙箱工具：CreateSandboxTool

最核心的一条命令。以本项目 `bench-maker-ds` 为例（完整参数即生产配置）：

```bash
tccli ags CreateSandboxTool --region ap-singapore --cli-unfold-argument \
  --ToolName bench-maker-ds \
  --ToolType custom \
  --NetworkConfiguration.NetworkMode PUBLIC \
  --CustomConfiguration.Image benchmark-upload-sicheng.tencentcloudcr.com/benchmark-repo/benchmark-dsharness:1.1.0 \
  --CustomConfiguration.ImageRegistryType enterprise \
  --CustomConfiguration.Command /usr/bin/envd \
  --CustomConfiguration.Args sleep infinity \
  --CustomConfiguration.Ports.0.Name envd \
  --CustomConfiguration.Ports.0.Port 49983 \
  --CustomConfiguration.Ports.0.Protocol TCP \
  --CustomConfiguration.Probe.HttpGet.Path /health \
  --CustomConfiguration.Probe.HttpGet.Port 49983 \
  --CustomConfiguration.Probe.HttpGet.Scheme HTTP \
  --CustomConfiguration.Probe.ReadyTimeoutMs 30000 \
  --CustomConfiguration.Probe.ProbeTimeoutMs 3000 \
  --CustomConfiguration.Probe.ProbePeriodMs 3000 \
  --CustomConfiguration.Probe.SuccessThreshold 1 \
  --CustomConfiguration.Probe.FailureThreshold 100 \
  --CustomConfiguration.Resources.CPU 1 \
  --CustomConfiguration.Resources.Memory 2Gi \
  --CustomConfiguration.Resources.Storage 10Gi \
  --RoleArn "qcs::cam::uin/<uin>:roleName/<roleName>" \
  --DefaultTimeout 2h
```

参数讲解（领导/评审常问的几组）：

| 参数组 | 含义 | 实战建议 |
|---|---|---|
| `NetworkMode` | `PUBLIC`=可出公网；`SANDBOX`=完全隔离（无出网） | 跑不可信代码/离线验证用 SANDBOX；要拉 GitHub/PyPI 用 PUBLIC |
| `Image` + `ImageRegistryType` | 工具的镜像及来源 | 私有 TCR 填 `enterprise`，需配 RoleArn 才能拉取 |
| `Command`/`Args` | 实例入口 | 官方 envd 镜像用 `/usr/bin/envd`；自带 s6 的用 `/init` + `sleep infinity` |
| `Ports` + `Probe` | 健康探针（就绪判定） | 必须指向 envd 的 49983 `/health`，探针不通工具会 FAILED |
| `Resources` | 单实例资源 | 2Gi 内存是舒适值；配额按实例数 × 单实例计 |
| `DefaultTimeout` | 实例最长存活 | 到点自动销毁（兜底防泄漏） |

### 2.2 查看与等待：DescribeSandboxToolList

```bash
tccli ags DescribeSandboxToolList --region ap-singapore
```

返回 `SandboxToolSet` 数组，关注 `ToolName / ToolId / Status`。
**Status 语义**：`CREATING` → `ACTIVE`（可拉实例）；**`FAILED` 不会自愈**
（常见原因：镜像不存在/探针不通——必须删除重建，见坑 1）。

等待 ACTIVE 的标准轮询（本仓库 `validator_driver.py` 的做法）：

```python
import json, subprocess, time

def list_tools():
    r = subprocess.run(["tccli", "ags", "DescribeSandboxToolList",
                        "--region", "ap-singapore"],
                       capture_output=True, text=True, timeout=180)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:])["SandboxToolSet"] if i >= 0 else []

def wait_tool_active(name, deadline_s=300):
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        for t in list_tools():
            if t["ToolName"] == name:
                if t["Status"] == "ACTIVE":
                    return True
                if t["Status"] == "FAILED":
                    raise RuntimeError(f"工具 {name} FAILED（删掉重建，不自愈）")
        time.sleep(8)
    raise TimeoutError(name)
```

### 2.3 预热：CreatePreCacheImageTask（强烈推荐）

```bash
tccli ags CreatePreCacheImageTask --region ap-singapore --cli-unfold-argument \
  --Image benchmark-upload-sicheng.tencentcloudcr.com/benchmark-repo/benchmark-dsharness:1.1.0 \
  --ImageRegistryType enterprise
```

把镜像提前拉到节点池：冷启动从 ~40s 降到 **~4s**。工具创建/镜像更新后各做一次。

### 2.4 删除工具：DeleteSandboxTool

```bash
tccli ags DeleteSandboxTool --region ap-singapore --ToolId <ToolId>
```

**前置条件：该工具名下无存活实例**，否则报 `ResourceInUse`。标准姿势是先在数据面
杀光实例再删（见 §3.4）。删除通常伴随配额归还——账号工具配额默认 10 个，
长期不删会挤占新工具的名额。

### 2.5 附赠：TCR 实例令牌（推镜像用）

```bash
tccli tcr CreateInstanceToken --region ap-singapore --RegistryId <registryId>
# 返回 {"Username": "...", "Token": "...", "ExpTime": ...}
docker login <registry域名> -u <Username> --password-stdin <<< <Token>
```

**实测有效期 ~1.5 小时**（不是 24h）——长批次必须每批刷新（本仓库驱动内置自动刷新）。

---

## 三、E2B SDK 教程（数据面）

### 3.1 创建实例

```python
from e2b_code_interpreter import Sandbox

sb = Sandbox.create(
    template="bench-maker-ds",   # ← 工具名（不是镜像名！）
    timeout=1800,                # 实例级存活上限（秒）
)
print(sb.sandbox_id)
```

要点：
- `template` 填**工具名**；工具必须处于 ACTIVE；
- 同一工具可并发拉多个实例（账号并发实例配额 ≈50，实测边界）；
- 创建延迟实测 p50 ≈ 4.2s，且 **5→40 并发恒定**（网关完全并行），预热镜像后如此。

### 3.2 执行命令：commands.run（最常用）

```python
from e2b.sandbox.commands.command_handle import CommandExitException

def sh(sb, cmd, timeout=900, envs=None):
    """执行 shell 命令；非零退出码不抛异常，返回结果对象（含 stdout/stderr）。"""
    try:
        return sb.commands.run(cmd, timeout=timeout, user="root", envs=envs)
    except CommandExitException as e:   # e 本身也带 stdout/stderr/exit_code
        return e

r = sh(sb, "git clone --depth 1 https://github.com/pallets/click /work/repo")
print(r.exit_code, r.stdout[-200:])
```

三个关键参数：

| 参数 | 说明 |
|---|---|
| `user="root"` | 默认用户是 `user`；若镜像内改过 `/etc/passwd`，默认用户查找会失败——**统一显式 root** |
| `envs={"K":"V"}` | **命令级**环境变量（仅本条命令进程可见，退出即焚）——实例级 envVars 当前版本不支持，凭据注入的标准姿势 |
| `timeout` | 秒；超时抛异常，注意捕获 |

### 3.3 读写文件：files API

```python
# 写（文本或 bytes）
sb.files.write("/work/hello.txt", "hi", user="root")

# 读 —— 注意返回 bytearray，不是 bytes！
blob = sb.files.read("/work/hello.txt", format="bytes", user="root")
data = bytes(blob)          # 统一转 bytes 再使用
```

适用：小文件（KB 级）。大文件（>10MB）走 `tar + base64` 或对象存储中转更稳。

### 3.4 沙箱互访：实例级 Token（一个沙箱直访另一个沙箱）

官方机制：CVM 调 `AcquireSandboxInstanceToken` 为沙箱 B 签发实例级访问 Token
（`sit_…`，**~24h 有效**），该 Token 即 envd 层 `X-Access-Token` 凭证（实测与 SDK
connect 换回的 envd_access_token 同源）——把它交给沙箱 A，A 就能直访 B：

```python
# ① CVM：拉起 B 并签发实例 Token
b = Sandbox.create(template="bench-tool", timeout=3600)
r = subprocess.run(["tccli", "ags", "AcquireSandboxInstanceToken",
                    "--region", "ap-singapore", "--InstanceId", b.sandbox_id],
                   capture_output=True, text=True, timeout=60)
sit = json.loads(r.stdout)["Token"]        # 返回平铺结构（无 Response 包装）

# ② A 内（envs 注入 sit + b.sandbox_id）：三件套直连 B
import e2b.envd.client_sync as cs
import e2b.envd.client_async as ca
from e2b.envd.interceptors import DefaultHeadersInterceptor

def _with_token(orig):
    def patched(config, base_url):
        lst = orig(config, base_url)
        lst.insert(0, DefaultHeadersInterceptor({"X-Access-Token": SIT}))
        return lst
    return patched
cs.build_interceptors = _with_token(cs.build_interceptors)
ca.build_interceptors = _with_token(ca.build_interceptors)

from e2b_code_interpreter import Sandbox
b = Sandbox.connect(BENCH_ID, debug=True, domain=DOMAIN,
                    sandbox_url=f"https://49983-{BENCH_ID}.{DOMAIN}")
b.commands.run("echo hello", user="root")     # ← A 直达 B
```

三条实测铁律（逆向验证所得）：

| # | 规则 | 说明 |
|---|---|---|
| 1 | **URL 格式 `https://49983-<sandbox_id>.<domain>`**（端口在前） | 与开源 E2B 的 `<id>-<port>` **相反**；`sandbox.<domain>`、`<id>.<domain>` 均报 invalid host format |
| 2 | **Token 放 `X-Access-Token` 头** | 不能作为 SDK `api_key` 传 `Sandbox.connect`（API 网关 connect 端点只认账号级 e2b key，报 401 Invalid API key） |
| 3 | **files API 不走拦截器** | `files.read/write` 走独立 `/files` HTTP 端点，Token 头不生效（401）→ 跨沙箱文件操作用命令封装（`base64 -d > path` 写、`base64 -w0 path` 读），commands 通道完全可用 |

> 必须用 `debug=True` + `sandbox_url` 覆盖：debug 分支跳过 API 网关换票
> （connect 需要账号级 key，agent 沙箱没有也不该有）；`sandbox_url` 指定
> AGS 的 `49983-<id>` 路由格式。Token 头经 monkey-patch `build_interceptors`
> 在构造期注入（拦截器构造时求值，connect 后再改 config 无效）。
> 生产实现：`images/dsharness/agents/solver_agent.py`（已 E2E 验证）。

### 3.5 实例管理：list / connect / kill（清理三件套）

```python
from e2b_code_interpreter import Sandbox

def kill_all_instances():
    """列出并杀掉账号下全部存活实例（删工具前必做，否则 ResourceInUse）。"""
    pag = Sandbox.list()                # 分页迭代器
    while True:
        items = pag.next_items()
        if not items:
            break
        for info in items:
            try:
                Sandbox.connect(info.sandbox_id).kill()
            except Exception:
                pass                    # 已死/网络抖动，忽略即可
        if not pag.has_next:
            break
```

单实例销毁就是 `sb.kill()`——**务必放在 `finally` 里**，否则异常路径会漏杀，
实例要等到 DefaultTimeout（最长 2h）才自动回收。

### 3.6 把两个平面串起来：标准生命周期五步

```python
# ① 控制面：建工具（镜像必须已推送！）→ 等 ACTIVE
create_unit_tool(image_ref, "my-tool")
wait_tool_active("my-tool")

# ② 数据面：拉实例 → 干活
sb = Sandbox.create(template="my-tool", timeout=1800)
try:
    sh(sb, "python3 /app/workload.py")
    data = bytes(sb.files.read("/output/result.json", format="bytes", user="root"))
finally:
    sb.kill()                           # ③ 数据面：杀实例

# ④ 控制面：删工具（归还配额）
delete_unit_tool("my-tool")             # 内部：失败时先 kill_all_instances 再重试
```

---

## 四、实测坑位速查表（17 条，全部踩过）

| # | 坑 | 现象 | 对策 |
|---|---|---|---|
| 1 | **先建工具后推镜像** | 工具 FAILED 且**不自愈**，后续 Sandbox.create 报 409 | 铁律：push 镜像 → 再 CreateSandboxTool |
| 2 | 工具名下残留实例就删工具 | `ResourceInUse` 删除失败 | 删除前数据面杀光实例，失败重试 6 次 |
| 3 | TCR 令牌当 24h 用 | 批次中途 push 全部 401 | 实测 ~1.5h，每批 `CreateInstanceToken` 刷新 |
| 4 | 实例级 envVars | SDK 不支持，TypeError | 用 `commands.run(envs=...)` 命令级注入（安全性等同） |
| 5 | files.read 返回值当 bytes 用 | bytearray 无 `.encode()` 等方法 | `bytes(blob)` 统一转换 |
| 6 | 镜像内改了 /etc/passwd 后用 files API | `unknown user user` | 读写都显式 `user="root"` |
| 7 | 不预热直接拉实例 | 冷启动 ~40s | CreatePreCacheImageTask 后 ~4s |
| 8 | 探针配错端口/路径 | 工具永远 CREATING→FAILED | 必须是 49983 端口 `/health`（官方 envd） |
| 9 | NetworkMode 选错 | SANDBOX 里 pip install 卡死 | 要出网选 PUBLIC；不可信代码才用 SANDBOX |
| 10 | 忘了 DefaultTimeout 兜底 | 异常路径实例泄漏 2h+ | 创建时设合理超时 + finally kill |
| 11 | commands.run 非零码当崩溃 | 业务上非零是正常结果（如 grep 无命中） | 捕获 CommandExitException，e 即结果 |
| 12 | 并发拉实例怕限流 | 实测网关完全并行 | 5→40 并发创建延迟恒定 ~4.2s，放心并发 |
| 13 | 工具配额当无限用 | CreateSandboxTool 报配额超限 | 账号默认 10 个：常驻工具少注册，临时的用完即删 |
| 14 | 用镜像名当 template | Sandbox.create 找不到模板 | template 填**工具名**（ToolName） |
| 15 | 长任务无心跳 | commands.run 偶发超时 | 命令内后台化 + 轮询产出文件 |
| 16 | 在沙箱里再跑 kaniko 之类重活 | 覆盖根文件系统关键文件 | 重活独立成镜像/工具，别在运行实例上做 |
| 17 | nohup 跑驱动随会话死 | 后台任务被杀留孤儿实例 | `setsid`/systemd-run 脱离会话 |
| 18 | 沙箱互访用开源 URL 格式 `<id>-49983.<domain>` | invalid host format | AGS 格式是 **`49983-<id>.<domain>`**（端口在前） |
| 19 | sit_ Token 当 SDK api_key 传 connect | 401 Invalid API key（connect 端点只认账号级 e2b key） | Token 放 `X-Access-Token` 头，经 monkey-patch 拦截器注入 |
| 20 | 跨沙箱用 files API 读写 | `/files` 独立端点不吃拦截器头 → 401 | 命令封装：`base64 -d` 写 / `base64 -w0` 读 |

---

## 五、本仓库代码映射（学完去看哪里）

| 教学点 | 生产实现 |
|---|---|
| 工具生命周期五步 | `src/drivers/validator_driver.py`（tccli 封装 + 临时工具编排） |
| **沙箱互访（实例 Token）** | `images/dsharness/agents/solver_agent.py`（solver agent，已 E2E 验证） |
| 沙箱池（预热 + 背压 + 指标） | `src/pool/sandbox_pool.py`（AsyncSandbox 批量管理） |
| 并发标定方法 | `src/pool/ramp_test.py`（5→40 阶梯压测） |
| 命令级凭据注入 | `src/drivers/maker_driver.py`（envs 下发 TCR/GitHub 令牌） |
| 镜像内 agent 写法 | `images/dsharness/agents/maker_agent.py`（沙箱内视角） |
| 沙箱内构建镜像的深坑 | `docs/AGS_IN_SANDBOX_IMAGE_BUILD.md`（17 坑位专册） |

---

*维护说明：坑位表与 §五 映射需随架构演进同步更新；教学示例取自生产代码，
改动生产代码时若影响示例语义，请同步本文。*
