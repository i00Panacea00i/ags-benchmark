# 多智能体沙箱镜像（DeepSeek Harness 部署版）
# 运行环境（领导要求）：ubuntu:22.04 + Python 3.11 + Git + Docker CLI
# AGS 兼容：注入官方 envd（数据面守护进程，49983）——自定义镜像红线见 T06/T07
# 一镜像三角色：bench-maker-ds（PUBLIC）/ bench-validator-ds（PUBLIC）/ bench-ds（SANDBOX）
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# ── 基础工具 + Python 3.11（deadsnakes PPA，22.04 默认为 3.10）──
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg git jq unzip xz-utils \
        software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3.11-distutils \
    && rm -rf /var/lib/apt/lists/*

# ── Docker CLI（要求项；沙箱内无 daemon，镜像构建/推送由 kaniko+crane 承担，
#    CLI 供 docker pull/inspect 等检视操作）──
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /usr/share/keyrings/docker.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu jammy stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# ── Python 3.11 默认化 + pip ──
RUN ln -sf /usr/bin/python3.11 /usr/local/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# ── 运行库：跨 AGS SDK + 测试栈（pytest<9：9.x 对旧式测试构造收集报错，实测）
#    常见仓库测试依赖预装（bench 沙箱为离线网络，运行期不可 pip install）──
RUN pip3 install --no-cache-dir e2b-code-interpreter==2.9.2 \
        'pytest<9' pytest-json-report pretend hypothesis flit_core

# ── AGS 数据面守护进程（官方 envd 二进制，监听 49983；勿动 WORKDIR/USER/ENTRYPOINT）──
COPY --from=ccr.ccs.tencentyun.com/ags-image/envd:v0.5.14 /usr/bin/envd /usr/bin/envd
# envd 以系统账户执行命令：裸 ubuntu 无 E2B 约定的 'user' 账户（官方基座由 s6 创建）
# → 必须显式创建，否则 SDK 默认 user 报 invalid username
RUN chmod +x /usr/bin/envd && useradd -m -s /bin/bash user

# ── agents（DeepSeek Harness + maker + validator）与题目 harness 协议 ──
COPY agents/ /opt/agents/
COPY harness/ /benchmark/harness/
COPY kaniko-bin/executor /opt/builder/kaniko/executor
COPY crane-bin/crane /opt/builder/crane/crane
RUN chmod +x /opt/agents/*.py /benchmark/harness/*.sh \
        /opt/builder/kaniko/executor /opt/builder/crane/crane \
    && mkdir -p /benchmark/repos /benchmark/results /work /output \
    && ln -sf /opt/agents/maker_agent.py /opt/builder/builder_agent.py \
    && ln -s /benchmark/harness /opt/builder/harness \
    && rm -rf /opt/agents/__pycache__

# 工具配置（deploy/create_tools_dsharness.sh）：
#   启动命令 /usr/bin/envd，参数留空；端口 envd/TCP/49983；探针 /health→49983
