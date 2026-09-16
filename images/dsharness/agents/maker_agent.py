#!/usr/bin/env python3
"""AGS 沙箱内 benchmark 题目制作 agent（SKILL1 管线的无状态单单元执行体）。

运行环境：AGS 联网沙箱（PUBLIC 网络），镜像含 python3/git/jq。
输入（环境变量）：
  WORK_REPO   目标仓库（owner/name）
  WORK_ISSUE  issue 编号
  GITHUB_TOKEN 可选（无则匿名调用，受 60 次/小时限制）
  LLM 端点可选（OPENAI_BASE_URL/OPENAI_API_KEY/HERMES_MODEL），缺省走模板改写
输出：
  /output/<instance_id>/{manifest.jsonl, problems/, answers/, solutions/, tests/, build-report.md}
  stdout 末行打印 RESULT JSON（供 CVM 驱动解析）
无状态约束：不读不写任何全局状态；同单元重跑结果一致。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

WORK_REPO = os.environ["WORK_REPO"]
WORK_ISSUE = int(os.environ["WORK_ISSUE"])
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/output")
WORKDIR = os.environ.get("WORKDIR", "/tmp/build")
MAX_PATCH_LINES = 700
P2P_CAP = 20
INSTANCE_ID = f"{WORK_REPO.replace('/', '__')}-{WORK_ISSUE}"
OUT = os.path.join(OUTPUT_DIR, INSTANCE_ID)

GH_API = "https://api.github.com"


def gh(path):
    """GitHub REST GET（可选 token），带限流退避。"""
    for attempt in range(3):
        req = urllib.request.Request(GH_API + path, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "benchmark-builder-agent",
            **({"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {})})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < 2:  # 限流退避
                time.sleep(20 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"GitHub API 多次失败: {path}")


def sh(cmd, cwd=None, timeout=600, check=False):
    r = subprocess.run(cmd, shell=isinstance(cmd, str), cwd=cwd,
                       capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"命令失败({r.returncode}): {cmd}\n{r.stderr[:800]}")
    return r


def fail(stage, reason):
    """过滤漏斗淘汰：非错误，是业务结果——打印 RESULT 并退出 3（区别于崩溃）。"""
    print(json.dumps({"result": "filtered", "stage": stage, "reason": reason,
                      "instance_id": INSTANCE_ID}, ensure_ascii=False))
    sys.exit(3)


def split_patch(files):
    """按文件路径拆分 PR diff：测试文件 → test_patch，其余 → golden_patch。"""
    test_re = re.compile(r"(^|/)(tests?)/|(^|/)test_[^/]+\.py$|(^|/)conftest\.py$")
    golden, tests = [], []
    for f in files:
        h = f"--- a/{f['filename']}\n+++ b/{f['filename']}\n"
        if f.get("patch") is None:
            continue
        body = f["patch"]
        if not body.endswith("\n"):
            body += "\n"
        (tests if test_re.search(f["filename"]) else golden).append(h + body)
    return "".join(golden), "".join(tests), [f["filename"] for f in files if f.get("patch")]


def run_pytest(repo_dir, test_args, venv_py, seq):
    """在指定仓库状态下跑 pytest，返回 {nodeid: outcome}。"""
    out = f"/tmp/report_{seq}.json"
    cmd = (f"{venv_py} -m pytest {' '.join(test_args)} -q --tb=no "
           f"--json-report --json-report-file={out}")
    r = sh(cmd, cwd=repo_dir, timeout=900)
    try:
        with open(out) as f:
            data = json.load(f)
        return {t["nodeid"]: t["outcome"] for t in data.get("tests", [])}
    except Exception:
        return {"__harness__": "crash", "__stderr__": (r.stderr or r.stdout)[-400:]}


def build_images(manifest, repo_dir):
    """第 ⑧ 步：沙箱内 kaniko 构建双镜像并推送 TCR，digest 回填 manifest。

    实测配方（2026-09-14 沙箱验证通过）：
    - 沙箱不在 VPC → 腾讯 DNS 将 TCR 域名解析到内网 IP 不可达，需 TCR_PUBLIC_IP
      （CVM 侧 dig @8.8.8.8 解析）写入 /etc/hosts 强制公网端点；
    - DOCKER_CONFIG=/kaniko/.docker 激活社区版 kaniko 的 file 凭据 provider
      （默认凭据链不含 file，会以匿名身份请求 → push 401）；
    - 不使用 --cleanup：kaniko 会把基础镜像解包到自身根文件系统，cleanup 阶段的
      删除会破坏沙箱（/bin/sh、/run/s6 被删）；不清理则仅覆盖不删除，envd/s6
      进程不受影响（沙箱单次使用，磁盘代价可接受）；
    - digest 从 kaniko 输出的 "Pushed ...@sha256:..." 或 "digest: sha256:..." 解析。
    - TCR 推送凭据经环境变量注入（TCR_PUSH_USER/TCR_PUSH_PASS），落 /kaniko/.docker。
    - 未配置凭据时跳过（产物为构建上下文，由 CVM 兜底打包），不影响单元成功。
    """
    import base64
    registry = os.environ.get("TCR_REGISTRY", "")
    user, passwd = os.environ.get("TCR_PUSH_USER", ""), os.environ.get("TCR_PUSH_PASS", "")
    if not (registry and user and passwd):
        print("[builder] 未配置 TCR 推送凭据 → 跳过镜像构建（产物=构建上下文）")
        return manifest, None
    ns = os.environ.get("TCR_NAMESPACE", "benchmark-repo")
    repo_short = WORK_REPO.split("/")[-1].replace(".", "-")
    # ★ tag 唯一化（回归修复）：秒级时间 + 题号后缀——分钟级 tag 在同仓库并发
    #   制作时会碰撞，后推覆盖先推 → 先完成单元的 tag↔digest 失配 → 其验证
    #   工具创建稳定 FAILED（实测 packaging#727/#733 同分钟碰撞）
    tag = f"{datetime.now():%Y%m%d-%H%M%S}-{WORK_ISSUE}"
    bench_dst = f"{registry}/{ns}/benchmark-{repo_short}:{tag}"

    # TCR 公网端点强制（沙箱 DNS 解析到 VPC 内网 IP，不可达）
    pub_ip = os.environ.get("TCR_PUBLIC_IP", "")
    if pub_ip:
        sh(f"echo '{pub_ip} {registry}' >> /etc/hosts")

    # 构建上下文：pkg/benchmark = 完整 /benchmark 布局
    pkg = os.path.join(WORKDIR, "pkg")
    ctx = os.path.join(pkg, "benchmark")
    shutil.rmtree(pkg, ignore_errors=True)
    os.makedirs(ctx)
    for item in ("problems", "answers", "solutions", "tests"):
        shutil.copytree(os.path.join(OUT, item), os.path.join(ctx, item))
    shutil.copy(os.path.join(OUT, "env-lock.txt"), os.path.join(ctx, "env-lock.txt"))
    shutil.copytree("/opt/builder/harness", os.path.join(ctx, "harness"))
    shutil.copytree(repo_dir, os.path.join(ctx, "repos", WORK_REPO.replace("/", "__")),
                    symlinks=True)
    open(os.path.join(ctx, "manifest.jsonl"), "w").write(
        json.dumps(manifest, ensure_ascii=False) + "\n")

    # 模板：每题单元镜像（内容烧入，AGS 可启动——基座含 envd）
    # 两层结构：benchmark-ds-base（共享固定层，digest 固定）+ 本题内容层。
    # 构建即 COPY + 依赖固化（env-lock 环境复现契约）+ 仓库可编辑安装。
    base_image = os.environ.get("BASE_IMAGE", "")
    if not base_image:
        raise RuntimeError("未配置 BASE_IMAGE（benchmark-ds-base 的 digest 引用）")
    open(os.path.join(pkg, "Dockerfile.unit"), "w").write(
        "ARG BASE_IMAGE=" + base_image + "\n"
        "FROM ${BASE_IMAGE}\n"
        "COPY benchmark /benchmark\n"
        "RUN pip3 install --no-cache-dir -r /benchmark/env-lock.txt \\\n"
        f" && pip3 install --no-cache-dir -e /benchmark/repos/{WORK_REPO.replace('/', '__')} \\\n"
        " && chmod +x /benchmark/harness/*.sh\n")

    # 凭据落盘 /root/.docker（kaniko 拉取阶段读取；勿放 /kaniko——社区版 kaniko
    # 把它用作自身快照工作区，且 /tmp 会被其构建过程清理，均不安全）
    os.makedirs("/root/.docker", exist_ok=True)
    os.environ["DOCKER_CONFIG"] = "/root/.docker"
    auth = base64.b64encode(f"{user}:{passwd}".encode()).decode()
    open("/root/.docker/config.json", "w").write(
        json.dumps({"auths": {registry: {"auth": auth}}}))

    # 推送用 crane（凭据链独立可靠）：社区版 kaniko 多阶段构建的推送阶段凭据链
    # 存在缺陷（file provider 丢失 → 401，实测三种注入方式均不生效），
    # 故 kaniko 只负责构建出 tar（--no-push --tar-path，拉取凭据已验证可用），
    # 由 crane 完成 auth login + push + digest 查询。
    sh(f"/opt/builder/crane/crane auth login {registry} "
       f"-u \"$TCR_PUSH_USER\" -p \"$TCR_PUSH_PASS\"", check=True)

    def build_and_push(dockerfile, tar_path, dst, build_args=()):
        cmd = ["/opt/builder/kaniko/executor", "--context", f"dir://{pkg}",
               "--dockerfile", dockerfile, "--destination", dst,
               "--no-push", "--tar-path", tar_path]
        for kv in build_args:
            cmd += ["--build-arg", kv]
        r = sh(cmd, timeout=1500)
        if r.returncode != 0 or not os.path.exists(tar_path):
            raise RuntimeError(f"kaniko 构建失败({dst}): {(r.stderr or r.stdout)[-400:]}")
        sh(f"/opt/builder/crane/crane push {tar_path} {dst}", timeout=1500, check=True)
        d = sh(f"/opt/builder/crane/crane digest {dst}").stdout.strip()
        if not d.startswith("sha256:"):
            raise RuntimeError(f"crane digest 查询失败: {d[:120]}")
        os.remove(tar_path)   # 推送成功后清理（避免进入单元归档 tar）
        return d

    d1 = build_and_push(os.path.join(pkg, "Dockerfile.unit"), "/output/bench.tar", bench_dst)

    # ★ 产物自检：题目内容必须在镜像内（防快照基线污染类静默漏件）
    sh(f"/opt/builder/crane/crane export {bench_dst} /tmp/fs.tar", timeout=600, check=True)
    safe = WORK_REPO.replace("/", "__")
    n = int(sh(f"tar -tf /tmp/fs.tar | grep -cE "
               f"'^benchmark/repos/{safe}/.*\\.py$|^benchmark/manifest\\.jsonl$'").stdout.strip() or 0)
    os.path.exists("/tmp/fs.tar") and os.remove("/tmp/fs.tar")
    if n < 2:   # 仓库源码 + manifest ≥2 命中
        raise RuntimeError(f"镜像自检失败：内容命中 {n}/2（快照基线污染？）")
    print(f"[builder] 镜像自检通过：内容命中 {n}")

    manifest["image"], manifest["image_digest"] = bench_dst, d1
    return manifest, {"bench": bench_dst + "@" + d1[:19]}


def main():
    t_start = time.time()
    os.makedirs(OUT, exist_ok=True)

    # ⓪ 预检：网络与工具链
    sh("git --version && python3 --version", check=True)

    # ① issue 检索
    issue = gh(f"/repos/{WORK_REPO}/issues/{WORK_ISSUE}")
    if "pull_request" in issue:
        fail("not_an_issue", f"{WORK_ISSUE} 是 PR 不是 issue")
    if issue["state"] != "closed":
        fail("issue_not_closed", f"state={issue['state']}")
    labels = " ".join(l["name"].lower() for l in issue.get("labels", []))
    title = (issue.get("title") or "").lower()
    is_bug = bool(re.search(r"\bbug\b|🐛|crash|error|fails|broken|regression", labels + " " + title))
    issue_type = "bug" if is_bug else "feature_request"

    # ② solution 配对（三级优先）：
    #    ⓪ WORK_PR 预配对（反向发现器已确定 PR 号，零 search 调用——36 沙箱
    #       并发时 search API 30/min 会被打爆，实测 39 题死于 403）
    #    ① timeline 找 cross-referenced merged PR
    #    ② 搜索式回退（closing keywords 对齐 GitHub 官方全集）
    closing_re = re.compile(
        rf"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#{WORK_ISSUE}\b", re.I)
    pr = None
    work_pr = os.environ.get("WORK_PR")
    if work_pr:
        cand = gh(f"/repos/{WORK_REPO}/pulls/{work_pr}")
        if cand.get("merged") and closing_re.search(cand.get("body") or ""):
            pr = cand
    if pr is None:
        timeline = gh(f"/repos/{WORK_REPO}/issues/{WORK_ISSUE}/timeline?per_page=100")
        for ev in timeline:
            if ev.get("event") == "cross-referenced":
                src = ev.get("source", {}).get("issue", {})
                if "pull_request" in src:
                    cand = gh(f"/repos/{WORK_REPO}/pulls/{src['number']}")
                    if cand.get("merged") and closing_re.search(cand.get("body") or ""):
                        pr = cand
                        break
    if pr is None:
        # 回退：搜索式配对（在已合并 PR body 中检索 issue 号 + closing keywords）。
        # fine-grained PAT 的 timeline 会过滤 cross-referenced 事件（仓库访问范围
        # 未覆盖来源仓库时被隐藏，实测 5 事件→4 事件），搜索式在任何认证模式下可用。
        q = urllib.parse.quote(f"repo:{WORK_REPO} is:pr is:merged {WORK_ISSUE} in:body")
        for it in gh(f"/search/issues?q={q}&per_page=10").get("items", []):
            if closing_re.search(it.get("body") or ""):
                cand = gh(f"/repos/{WORK_REPO}/pulls/{it['number']}")
                if cand.get("merged"):
                    pr = cand
                    break
    if pr is None:
        fail("no_linked_solution", "timeline/搜索均无 closing keywords 的 merged PR")
    if pr["changed_files"] == 0:
        fail("empty_pr", "PR 无改动")

    # ③ 过滤漏斗
    files = gh(f"/repos/{WORK_REPO}/pulls/{pr['number']}/files?per_page=100")
    golden_patch, test_patch, touched = split_patch(files)
    if not golden_patch:
        fail("no_code_change", "PR 不触碰源码（纯文档/配置/依赖）")
    if not test_patch:
        fail("no_test_change", "PR 不含测试改动，无法构造 F2P")
    total_lines = sum(len((f.get("patch") or "").splitlines()) for f in files)
    if total_lines > MAX_PATCH_LINES:
        fail("patch_too_large", f"{total_lines} > {MAX_PATCH_LINES} 行")
    if re.search(r"security|cve|漏洞", labels + " " + title, re.I):
        fail("security_sensitive", "安全敏感题材剔除")

    # ④ 本地复现环境
    if os.path.exists(WORKDIR):
        shutil.rmtree(WORKDIR)
    os.makedirs(WORKDIR)
    repo_dir = os.path.join(WORKDIR, WORK_REPO.replace("/", "__"))   # 与 harness REPO_DIR 约定一致
    sh(f"git clone --quiet https://github.com/{WORK_REPO}.git {repo_dir}", timeout=600, check=True)
    base_commit = pr["base"]["sha"]
    sh(f"git -C {repo_dir} checkout --quiet {base_commit}", check=True)
    venv = os.path.join(WORKDIR, "venv")
    sh(f"python3 -m venv {venv}", timeout=300, check=True)
    venv_py = os.path.join(venv, "bin", "python")
    sh(f"{venv_py} -m pip install --quiet --upgrade pip", timeout=300, check=True)
    # pytest 固定 <9：pytest 9 将部分旧式测试构造升级为收集错误（PytestRemovedIn10Warning
    # × 仓库 filterwarnings=error → 0 收集），26.x 时代的仓库测试均写于 pytest 6-8 时代。
    # 经 env-lock 流入镜像，保证镜像内 harness 与验证环境一致。
    sh(f"{venv_py} -m pip install --quiet -e {repo_dir} 'pytest<9' pytest-json-report",
       timeout=900, check=True)

    # 仓库测试依赖（关键漏装修复）：packaging 等库的测试文件 import pretend/hypothesis，
    # 缺失时 pytest 收集 0 用例（0/0）→ 误判 untestable。
    # ★ 实测坑（pip 26）：`pip install -e 'path[test]'` 在项目无该 extra/组时会把
    #   项目重装为【非可编辑副本】→ golden 补丁改仓库源码而测试 import site-packages
    #   副本 → F2P 全灭（click 4 单元连灭根因）。故依赖一律【列表直装】，
    #   绝不通过 path[extra] 语法让 pip 触碰项目本身；装完验证可编辑链接并自愈。
    def install_test_deps():
        import tomllib as _toml
        groups = extras = {}
        pp = os.path.join(repo_dir, "pyproject.toml")
        if os.path.isfile(pp):
            try:
                with open(pp, "rb") as f:
                    _cfg = _toml.load(f)
                groups = _cfg.get("dependency-groups", {})
                extras = _cfg.get("project", {}).get("optional-dependencies", {})
            except Exception:
                pass
        for req in ("tests/requirements.txt", "requirements-test.txt"):
            p = os.path.join(repo_dir, req)
            if os.path.isfile(p):
                sh(f"{venv_py} -m pip install --quiet -r {p}", timeout=900, check=True)
                print(f"[builder] 测试依赖: {req}")
                return
        deps = groups.get("test") or extras.get("test") or []
        if deps:
            import shlex
            quoted = " ".join(shlex.quote(str(d)) for d in deps)
            sh(f"{venv_py} -m pip install --quiet {quoted}", timeout=900, check=True)
            print(f"[builder] 测试依赖: 列表直装（{len(deps)} 项）")
    install_test_deps()

    # ★ 可编辑链接验证与自愈：import 必须解析到仓库源码
    repo_import = WORK_REPO.split("/")[-1]
    r = sh(f"{venv_py} -c 'import {repo_import} as m; print(m.__file__)'")
    if repo_dir not in (r.stdout or ""):
        sh(f"{venv_py} -m pip install --quiet --force-reinstall --no-deps "
           f"-e {repo_dir}", timeout=900, check=True)
        print(f"[builder] ⚠️ 可编辑链接曾被破坏，已强制恢复（import 原指向: "
              f"{(r.stdout or '').strip()[:70]}）")

    # 补丁严格适用检查
    gp, tp = os.path.join(WORKDIR, "golden.patch"), os.path.join(WORKDIR, "tests.patch")
    open(gp, "w").write(golden_patch)
    open(tp, "w").write(test_patch)
    if sh(f"git -C {repo_dir} apply --check {gp} && git -C {repo_dir} apply --check {tp}").returncode != 0:
        fail("patch_conflict", "补丁在 base_commit 上不干净适用")

    # 测试目标 = test_patch 触碰的测试文件
    test_files = sorted({f for f in touched if re.search(r"(^|/)(tests?)/|(^|/)test_.*\.py$", f)})

    # ⑤ F2P 双向验证（动态计算 F2P/P2P + 一致性 2 轮）
    rounds = []
    for seq in range(2):
        # baseline：仅 test_patch
        sh(f"git -C {repo_dir} checkout --quiet -- . && git -C {repo_dir} clean -qfd && "
           f"git -C {repo_dir} checkout --quiet {base_commit} && git -C {repo_dir} apply {tp}", check=True)
        before = run_pytest(repo_dir, test_files, venv_py, f"b{seq}")
        # answer：+ golden
        sh(f"git -C {repo_dir} apply {gp}", check=True)
        after = run_pytest(repo_dir, test_files, venv_py, f"a{seq}")
        rounds.append((before, after))
    b0, a0 = rounds[0]
    if b0.get("__harness__") or a0.get("__harness__"):
        fail("harness_crash", f"pytest 异常: {str(b0)[:200]}")
    # 跨轮稳定性筛选：仅两轮结果一致的用例可进入 F2P/P2P；
    # 不稳定用例（时序敏感/测试间共享状态泄漏）剔除并留痕，不废弃整个单元
    # （实证：click#3740 既有参数化用例轮间互换失败，而 4 个新 F2P 用例跨轮稳定）
    sb = {k: b0[k] for k in b0 if all(r[0].get(k) == b0.get(k) for r in rounds)}
    sa = {k: a0[k] for k in a0 if all(r[1].get(k) == a0.get(k) for r in rounds)}
    unstable = sorted((set(b0) - set(sb)) | (set(a0) - set(sa)))
    if unstable:
        print(f"[builder] 剔除跨轮不稳定用例 {len(unstable)} 个: "
              f"{[u.split('::')[-1][:40] for u in unstable][:5]}")
    f2p = sorted(k for k in sb if sb[k] != "passed" and sa.get(k) == "passed")
    p2p = sorted(k for k in sb if sb[k] == "passed" and sa.get(k) == "passed")[:P2P_CAP]
    if not f2p:
        fail("untestable", f"无跨轮稳定 F2P（不稳定 {len(unstable)}/{len(b0)} 用例）")

    # 环境复现契约：固化「验证通过时的依赖集」——镜像构建必须复刻同一环境
    # （实证教训：缺 hypothesis → 收集失败 total=0；pytest 版本漂移 → 行为差异）
    freeze = sh(f"{venv_py} -m pip freeze --exclude-editable", cwd=repo_dir).stdout
    open(f"{os.path.join(OUT, 'env-lock.txt')}", "w").write(freeze)

    # ⑥ 问题改写（LLM 可选，缺省模板降级——语义自包含、剥离出处）
    body = re.sub(r"https?://\S+|@[A-Za-z0-9_-]+|!\[[^\]]*\]\([^)]*\)", "",
                  issue.get("body") or "")
    body = re.sub(r"\n{3,}", "\n\n", body).strip()[:2000]
    rewrite_method = "template"
    problem = (f"# {issue['title']}\n\n"
               f"## 项目上下文\n{WORK_REPO}（Python 项目），涉及模块：{', '.join(sorted(set(f.split('/')[0] for f in touched)))}。\n\n"
               f"## 问题描述\n{body}\n\n"
               f"## 期望行为\n上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。\n\n"
               f"## 环境信息\n仓库分支基准 commit：{base_commit[:12]}。")
    llm_base = os.environ.get("OPENAI_BASE_URL")
    if llm_base and os.environ.get("OPENAI_API_KEY"):
        # DeepSeek Harness 改写链（agent1 的 LLM 路径）：改写 + 忠实性代码校验；
        # 失败（含忠实性不过）自动降级模板，制作流水线永不因 LLM 中断
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from deepseek_harness import DeepSeekHarness, rewrite_problem
            h = DeepSeekHarness()
            problem, keep_ratio = rewrite_problem(
                h, issue["title"], body, WORK_REPO, touched, f2p)
            rewrite_method = f"deepseek-harness({h.model},标识符保留{keep_ratio:.0%})"
            print(f"[builder] DeepSeek Harness 改写完成: {rewrite_method}")
            # ★ LLM 使用证据留痕：原始/改写题面双留存 + 结构化调用档案
            import hashlib
            os.makedirs(f"{OUT}/problems", exist_ok=True)
            open(f"{OUT}/problems/{INSTANCE_ID}.orig.md", "w").write(
                f"# {issue['title']}\n\n{body}")
            json.dump({
                "purpose": "题面改写（防模型背答案）", "model": h.model,
                "base_url": llm_base, "identifier_keep_ratio": round(keep_ratio, 4),
                "orig_sha256": hashlib.sha256(body.encode()).hexdigest()[:16],
                "rewritten_sha256": hashlib.sha256(problem.encode()).hexdigest()[:16],
                "evidence_files": [f"problems/{INSTANCE_ID}.orig.md",
                                   f"problems/{INSTANCE_ID}.md"],
            }, open(f"{OUT}/llm-evidence.json", "w"), ensure_ascii=False, indent=1)
        except Exception as e:
            print(f"[builder][WARN] LLM 改写失败，模板降级: {e}")

    # ⑦ 产物落盘（目录布局对齐 DATA_CONTRACT §2）
    # exist_ok：⑥ LLM 证据段可能已预建 problems 目录（回归修复）
    os.makedirs(f"{OUT}/problems", exist_ok=True), os.makedirs(f"{OUT}/answers", exist_ok=True)
    os.makedirs(f"{OUT}/solutions", exist_ok=True), os.makedirs(f"{OUT}/tests/{INSTANCE_ID}", exist_ok=True)
    open(f"{OUT}/problems/{INSTANCE_ID}.md", "w").write(problem)
    open(f"{OUT}/answers/{INSTANCE_ID}.patch", "w").write(golden_patch)
    open(f"{OUT}/tests/{INSTANCE_ID}/tests.patch", "w").write(test_patch)
    # 扁平副本：validator 内容注入协议（inject_bundle 直接读取）
    open(f"{OUT}/problem.md", "w").write(problem)
    open(f"{OUT}/tests.patch", "w").write(test_patch)
    open(f"{OUT}/golden.patch", "w").write(golden_patch)
    open(f"{OUT}/solutions/{INSTANCE_ID}.md", "w").write(
        f"# {INSTANCE_ID}\n\n- issue: {issue['html_url']}\n- PR: {pr['html_url']}"
        f"（merge_commit {pr['merge_commit_sha'][:12]}）\n"
        f"- 修复摘要: {pr.get('title')}\n- 触碰文件: {', '.join(touched[:10])}"
        f"{'…' if len(touched) > 10 else ''}\n")

    import hashlib
    sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
    manifest = {
        "instance_id": INSTANCE_ID, "repo": WORK_REPO,
        "base_commit": base_commit, "merge_commit": pr["merge_commit_sha"],
        "issue_url": issue["html_url"], "pr_url": pr["html_url"],
        "pairing_confidence": "P1", "issue_type": issue_type, "language": "python",
        "problem": f"problems/{INSTANCE_ID}.md", "solution": f"solutions/{INSTANCE_ID}.md",
        "answer_summary": pr.get("title", ""),
        "golden_patch": f"answers/{INSTANCE_ID}.patch",
        "test_patch": f"tests/{INSTANCE_ID}/tests.patch",
        "FAIL_TO_PASS": f2p, "PASS_TO_PASS": p2p,
        "rewrite_method": rewrite_method,
        "image": "", "image_digest": "",   # 由 CVM 打包阶段回填
        "sha256": {k: sha(f"{OUT}/{v}") for k, v in [
            ("problem", f"problems/{INSTANCE_ID}.md"),
            ("golden_patch", f"answers/{INSTANCE_ID}.patch"),
            ("test_patch", f"tests/{INSTANCE_ID}/tests.patch"),
            ("solution", f"solutions/{INSTANCE_ID}.md")]},
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    # ⑧ 产物模式：每题单元镜像（内容烧入，AGS 可启动）——镜像构建推送 TCR + digest 回填
    manifest, images = build_images(manifest, repo_dir)

    with open(f"{OUT}/manifest.jsonl", "w") as f:
        f.write(json.dumps(manifest, ensure_ascii=False) + "\n")
    with open(f"{OUT}/build-report.md", "w") as f:
        f.write(f"# {INSTANCE_ID} 制作报告\n\n- 阶段耗时: {time.time()-t_start:.0f}s\n"
                f"- issue_type: {issue_type}｜配对: P1 (PR #{pr['number']})\n"
                f"- 补丁: {len(golden_patch.splitlines())} 行 golden + "
                f"{len(test_patch.splitlines())} 行 tests（共 {total_lines} 行）\n"
                f"- F2P: {len(f2p)} 项｜P2P: {len(p2p)} 项（cap {P2P_CAP}）｜"
                f"稳定性: 跨轮稳定 {len(sb)}/{len(b0)}（剔除不稳定 {len(unstable)}）\n"
                f"- 改写方式: {rewrite_method}\n"
                f"- 镜像: {images if images else '未构建（无推送凭据，产物为构建上下文）'}\n")

    print(json.dumps({"result": "success", "instance_id": INSTANCE_ID,
                      "f2p": len(f2p), "p2p": len(p2p), "rewrite": rewrite_method,
                      "images": images,
                      "duration_s": int(time.time() - t_start)}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        raise
    except Exception as e:
        print(json.dumps({"result": "error", "instance_id": INSTANCE_ID,
                          "error": f"{type(e).__name__}: {str(e)[:300]}"}, ensure_ascii=False))
        sys.exit(1)
