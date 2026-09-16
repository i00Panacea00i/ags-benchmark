# solver agent 镜像：独立 agent 沙箱宿主（经实例 Token 直访 bench 沙箱解题）
# 基座：benchmark-ds-base（digest 由部署时 --build-arg 固定，防 tag 漂移）
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

RUN pip3 install --no-cache-dir e2b-code-interpreter

COPY solver_agent.py /opt/solver/solver_agent.py
COPY deepseek_harness.py /opt/solver/deepseek_harness.py
RUN chmod +x /opt/solver/*.py
