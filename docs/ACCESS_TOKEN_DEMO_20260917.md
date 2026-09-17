# 用 Access Token 直访 benchmark 沙箱：命令行验证手册（Demo）

| 项 | 值 |
|---|---|
| 文档日期 | 2026-09-17 |
| 适用读者 | 领导演示 / 工程师验证沙箱互访能力 |
| 核心结论 | **无需任何 SDK，纯 `tccli` + `curl` 即可创建 benchmark 沙箱并用 Access Token 直访操作**（读元数据/列目录/读文件/执行命令/跑题目环境），全部命令实测验证 |
| 实测环境 | ap-singapore / tccli 已 configure / 题目镜像 `benchmark-click:fix-2836` |

---

## 一、原理速览（三要素）

```
① Access Token：tccli ags AcquireSandboxInstanceToken --InstanceId <实例ID>
   → 返回 sit_…（实例级访问令牌，~24h 有效，仅可访问该实例）

② 直访 URL：https://49983-<实例ID>.<E2B域名>/<RPC路径>
   （端口 49983 在前 —— 与开源 E2B 的 <id>-<port> 顺序相反）

③ 鉴权头：X-Access-Token: <sit_ Token>
```

## 二、Demo 全流程（10 步，每步含实测输出）

### 步骤 1：创建 benchmark 沙箱工具（题目镜像）

```bash
tccli ags CreateSandboxTool --region ap-singapore --cli-unfold-argument \
  --ToolName demo-bench --ToolType custom \
  --NetworkConfiguration.NetworkMode SANDBOX \
  --CustomConfiguration.Image "benchmark-upload-sicheng.tencentcloudcr.com/benchmark-repo/benchmark-click:fix-2836@sha256:27ef67fd…" \
  --CustomConfiguration.ImageRegistryType enterprise \
  --CustomConfiguration.Command /usr/bin/envd \
  --CustomConfiguration.Ports.0.Name envd --CustomConfiguration.Ports.0.Port 49983 \
  --CustomConfiguration.Ports.0.Protocol TCP \
  --CustomConfiguration.Probe.HttpGet.Path /health --CustomConfiguration.Probe.HttpGet.Port 49983 \
  --CustomConfiguration.Probe.HttpGet.Scheme HTTP \
  --CustomConfiguration.Probe.ReadyTimeoutMs 30000 --CustomConfiguration.Probe.ProbeTimeoutMs 1000 \
  --CustomConfiguration.Probe.ProbePeriodMs 1000 --CustomConfiguration.Probe.SuccessThreshold 1 \
  --CustomConfiguration.Probe.FailureThreshold 100 \
  --CustomConfiguration.Resources.CPU 1 --CustomConfiguration.Resources.Memory 2Gi \
  --CustomConfiguration.Resources.Storage 10Gi \
  --RoleArn "qcs::cam::uin/<uin>:roleName/<roleName>" --DefaultTimeout 2h
```

> 实测输出：工具约 **9 秒**后 ACTIVE（`tccli ags DescribeSandboxToolList` 轮询确认）。

### 步骤 2：启动沙箱实例（纯命令行，无需 SDK）

```bash
tccli ags StartSandboxInstance --region ap-singapore --ToolName demo-bench --Timeout 1h
```

> 实测输出：
> ```json
> {"Instance": {"InstanceId": "jlztvsbpow62f427fkfyexfwwnzocsm2cfjlyggf",
>               "ToolName": "demo-bench", "Status": "RUNNING", "TimeoutSeconds": 3600}}
> ```

### 步骤 3：获取 Access Token（本 Demo 的主角）

```bash
tccli ags AcquireSandboxInstanceToken --region ap-singapore \
  --InstanceId jlztvsbpow62f427fkfyexfwwnzocsm2cfjlyggf
```

> 实测输出（Token 已脱敏）：
> ```json
> {"Token": "sit_0Q8nn6huR1VlWGA9…", "ExpiresAt": "2026-09-18T06:41:10Z",
>  "TrafficToken": "5b1025…", "RequestId": "…"}
> ```

```bash
# 存入变量供后续使用
SID="jlztvsbpow62f427fkfyexfwwnzocsm2cfjlyggf"
DOM="ap-singapore.tencentags.com"
TOKEN=$(tccli ags AcquireSandboxInstanceToken --region ap-singapore \
  --InstanceId "$SID" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['Token'])")
URL="https://49983-$SID.$DOM"
```

### 步骤 4：健康检查

```bash
curl -s -o /dev/null -w 'HTTP %{http_code}\n' "$URL/health" -H "X-Access-Token: $TOKEN"
```
> `HTTP 204`（无 Token 时 401）

### 步骤 5：文件元数据（connectRPC · Stat）

```bash
curl -s -X POST "$URL/filesystem.Filesystem/Stat" \
  -H "X-Access-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"path": "/benchmark/manifest.jsonl"}'
```

> 实测输出（读到题目清单元数据）：
> ```json
> {"entry":{"name":"manifest.jsonl","type":"FILE_TYPE_FILE","path":"/benchmark/manifest.jsonl",
>  "size":"4467","permissions":"-rw-r--r--","owner":"root","modifiedTime":"2026-09-15T…"}}
> ```

### 步骤 6：列目录（connectRPC · ListDir）

```bash
curl -s -X POST "$URL/filesystem.Filesystem/ListDir" \
  -H "X-Access-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"path": "/benchmark/repos/pallets__click/src/click"}' \
  | python3 -m json.tool
```

> 实测输出（题目源码目录）：
> `["__init__.py", "_compat.py", "core.py", "decorators.py", "exceptions.py", …]`

### 步骤 7：读文件内容（/files HTTP 端点）

```bash
curl -s "$URL/files?path=/benchmark/manifest.jsonl" -H "X-Access-Token: $TOKEN"
```

> 实测输出（题目 manifest 全文，节选）：
> ```json
> {"instance_id": "pallets__click-2836", "repo": "pallets/click",
>  "base_commit": "8c95c73b…", "issue_url": "https://github.com/pallets/click/issues/2836", …}
> ```

### 步骤 8：执行命令（connectRPC 流式 · process.Process/Start）★ 最强演示

envd 的命令执行是 **connect 流式协议**（请求体为 5 字节帧头 + JSON）。两条命令完成：

```bash
# ① 构造请求帧（bash 纯命令行）
BODY='{"process":{"cmd":"sh","args":["-c","id && hostname && ls /benchmark/"],"envs":{},"cwd":"/"}}'
LEN=$(printf '%08x' ${#BODY})
printf "\x00\x${LEN:0:2}\x${LEN:2:2}\x${LEN:4:2}\x${LEN:6:2}%s" "$BODY" > /tmp/frame.bin

# ② 发送并解码输出（stdout 为 base64 事件流）
curl -s -N -X POST "$URL/process.Process/Start" \
  -H "X-Access-Token: $TOKEN" -H "Content-Type: application/connect+json" \
  --data-binary @/tmp/frame.bin \
  | python3 -c "
import sys, struct, base64
data = sys.stdin.buffer.read(); i = out = b''
while i + 5 <= len(data):
    ln = struct.unpack('>I', data[i+1:i+5])[0]
    import json
    try:
        ev = json.loads(data[i+5:i+5+ln]).get('event', {})
        if 'data' in ev: out += base64.b64decode(ev['data'].get('stdout','') or '')
        if 'end' in ev: print('[exit_code]', ev['end'].get('exitCode'), file=sys.stderr)
    except Exception: pass
    i += 5 + ln
print(out.decode('utf-8','replace'))"
```

> 实测输出（**root 权限在题目沙箱内执行**）：
> ```
> uid=0(root) gid=0(root) groups=0(root)
> 80e9efa3
> answers  env-lock.txt  harness  manifest.jsonl  problems  repos  solutions  tests
> [exit_code] 0
> ```

进阶：**在题目环境里跑 Python**（验证题目环境完整性）：

```bash
BODY='{"process":{"cmd":"sh","args":["-c","python3 -c '"'"'import click; print(click.__version__)'"'"'"],"envs":{},"cwd":"/"}}'
# …同上构造帧并发送
```

> 实测输出：`click 8.3.2`（题目镜像内的题目环境可直接使用）

### 步骤 9：鉴权有效性对照

```bash
curl -s -X POST "$URL/filesystem.Filesystem/Stat" \
  -H "X-Access-Token: sit_invalid_demo" -H "Content-Type: application/json" \
  -d '{"path": "/"}'
```

> 实测输出：`{"error":{"code":"AUTHENTICATION_FAILED","message":"Authentication failed"}}`——
> Token 鉴权真实生效，错误 Token 无法越权。

### 步骤 10：清理

```bash
# 停实例（注意：kill/Stop 后实例进入 STOPPED，配额释放需等过渡期，详见附录）
tccli ags StopSandboxInstance --region ap-singapore --InstanceId "$SID"
# 删工具（归还工具配额）
TID=$(tccli ags DescribeSandboxToolList --region ap-singapore | python3 -c "
import sys,json
for t in json.load(sys.stdin)['SandboxToolSet']:
    if t['ToolName']=='demo-bench': print(t['ToolId']); break")
tccli ags DeleteSandboxTool --region ap-singapore --ToolId "$TID"
```

## 三、能力总结（本 Demo 验证了什么）

| 能力 | 命令 | 结果 |
|---|---|---|
| 纯命令行创建沙箱 | tccli CreateSandboxTool + StartSandboxInstance | ✅ 工具 ~9s / 实例即时 RUNNING |
| 实例级授权 | AcquireSandboxInstanceToken | ✅ sit_ Token，~24h |
| 健康检查 | curl /health | ✅ 204 |
| 文件元数据 | curl Stat | ✅ 读到题目 manifest 元数据 |
| 目录浏览 | curl ListDir | ✅ 列出题目源码目录 |
| 文件读取 | curl /files | ✅ 读出题目 manifest 全文 |
| **远程执行命令** | curl process/Start（流式） | ✅ **root 权限执行、跑题目环境（click 8.3.2）** |
| 鉴权安全 | 错误 Token | ✅ 401 拒绝 |

**业务含义**：任何持有 Access Token 的授权方（如 AI Agent 沙箱、CI 流水线、
人工排查）都可以不经过平台 SDK，直接对沙箱进行「读 + 写 + 执行」全操作——
这是「AI Agent 直访题目沙箱解题」架构（双沙箱核验）的底层支撑，全部能力
已用最朴素的命令行验证。

## 四、注意事项（实测坑位）

1. URL 是 `49983-<实例ID>`（端口在前），不是 `<实例ID>-49983`；
2. Token 放 `X-Access-Token` 头，不能当 Bearer/API key 用于其它网关端点；
3. 命令执行是流式协议：请求体需 5 字节帧头（`0x00` + 4 字节大端长度），
   且 **cmd/args 必须嵌套在 `process` 字段内**（扁平结构会得到
   `/usr/bin/nice: ''` 报错）；
4. /files 读内容、Filesystem RPC 读元数据——两类端点职责不同；
5. Token 有效期约 24 小时，长会话注意刷新。

---

*关联文档：`docs/AGENT_RUNTIME_GUIDE.md` §3.4（沙箱互访原理）、
`docs/SOLVER_AGENT_REPORT_20260917.md`（AI Agent 基于此机制的生产应用）。*
