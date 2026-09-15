#!/bin/bash
# 一键部署三个 AGS 沙箱工具（agent1 / agent2 / 题目基座）
# 前置：deploy/.env 已配置；镜像已构建推送（见 docs/USER_GUIDE.md §2）
# 红线：先 push 镜像再创建工具——工具创建时校验镜像，失败态不自愈（实测坑位 T03）
set -euo pipefail
cd "$(dirname "$0")"
source .env

REGION="${TCR_REGION:-ap-singapore}"
ROLE_ARN="${ROLE_ARN:?请在 .env 配置 CAM 角色 ARN（TCR 拉取最小权限）}"

create_tool() {  # $1=名称 $2=镜像 $3=网络模式 $4=描述
  tccli ags CreateSandboxTool --region "$REGION" --cli-unfold-argument \
    --ToolName "$1" --ToolType custom \
    --NetworkConfiguration.NetworkMode "$3" \
    --CustomConfiguration.Image "$2" \
    --CustomConfiguration.ImageRegistryType enterprise \
    --CustomConfiguration.Command /init \
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
    --CustomConfiguration.Resources.CPU 1 --CustomConfiguration.Resources.Memory 2Gi \
    --CustomConfiguration.Resources.Storage 10Gi \
    --RoleArn "$ROLE_ARN" --DefaultTimeout 2h --Description "$4" \
    | python3 -c "import sys,json;t=sys.stdin.read();i=t.find('{');print('  已创建:',json.loads(t[i:]).get('ToolId'))"
}

echo "[1/4] 题目基座（SANDBOX 隔离网络）"
create_tool "$BENCH_TOOL" "$TCR_REGISTRY/$TCR_NAMESPACE/benchmark-base:1.0.0" SANDBOX "bench base + content injection"

echo "[2/4] agent2 验证沙箱（PUBLIC——需跨 AGS 拉起题目沙箱）"
create_tool "$VALIDATOR_TOOL" "$TCR_REGISTRY/$TCR_NAMESPACE/benchmark-validator:1.0.0" PUBLIC "cross-AGS validator"

echo "[3/4] agent1 制作沙箱（PUBLIC——需 GitHub/PyPI/TCR）"
create_tool "$MAKER_TOOL" "$TCR_REGISTRY/$TCR_NAMESPACE/benchmark-builder-ags:2.3.1" PUBLIC "maker agent"

echo "[4/4] 预热（创建实例前的必做项，防冷启动拉镜像超时）"
for img in benchmark-base:1.0.0 benchmark-validator:1.0.0; do
  tccli ags CreatePreCacheImageTask --region "$REGION" --cli-unfold-argument \
    --Image "$TCR_REGISTRY/$TCR_NAMESPACE/$img" --ImageRegistryType enterprise > /dev/null \
    && echo "  预热已提交: $img"
done

echo "完成。轮询工具状态至 ACTIVE 后即可运行（docs/USER_GUIDE.md §3）。"
