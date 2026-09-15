#!/bin/bash
# DeepSeek Harness 部署：三工具创建 + 预热（一镜像三角色）
# 前置：镜像已构建推送（见 docs/USER_GUIDE_DSHARNESS.md）
set -euo pipefail
cd "$(dirname "$0")"
source .env

REGION="${TCR_REGION:-ap-singapore}"
ROLE_ARN="${ROLE_ARN:?请在 .env 配置 CAM 角色 ARN}"
IMAGE="$TCR_REGISTRY/$TCR_NAMESPACE/benchmark-dsharness:1.0.1"

create_tool() {  # $1=名称 $2=网络模式 $3=描述
  tccli ags CreateSandboxTool --region "$REGION" --cli-unfold-argument \
    --ToolName "$1" --ToolType custom \
    --NetworkConfiguration.NetworkMode "$2" \
    --CustomConfiguration.Image "$IMAGE" \
    --CustomConfiguration.ImageRegistryType enterprise \
    --CustomConfiguration.Command /usr/bin/envd \
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
    --RoleArn "$ROLE_ARN" --DefaultTimeout 2h --Description "$3" \
    | python3 -c "import sys,json;t=sys.stdin.read();i=t.find('{');print('  已创建:',json.loads(t[i:]).get('ToolId'))"
}

echo "[1/4] agent1 制作沙箱 bench-maker-ds（PUBLIC）"
create_tool bench-maker-ds PUBLIC "maker agent (DeepSeek Harness rewrite)"

echo "[2/4] agent2 验证沙箱 bench-validator-ds（PUBLIC——跨 AGS 拉起题目沙箱）"
create_tool bench-validator-ds PUBLIC "validator agent (Phase A + Phase B solver)"

echo "[3/4] 题目沙箱 bench-ds（SANDBOX 全隔离）"
create_tool bench-ds SANDBOX "bench sandbox (content injection, offline)"

echo "[4/4] 预热"
tccli ags CreatePreCacheImageTask --region "$REGION" --cli-unfold-argument \
    --Image "$IMAGE" --ImageRegistryType enterprise > /dev/null \
    && echo "  预热已提交"

echo "轮询至三个工具 ACTIVE 后即可运行。"
