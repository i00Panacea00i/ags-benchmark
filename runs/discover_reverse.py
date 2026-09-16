#!/usr/bin/env python3
"""反向 GitHub 发现器（2026-09-16 决策 D1：单 Token + 反向 PR 搜索）。

策略反转：不再「逐 issue 找配对 PR」（O(候选) 次 search），而是
「一次搜索拿全部带 closing keyword 的 merged PR，本地解析配对」
（O(仓库×页) 次 search）——PoC 实测：2 仓库 195 配对仅 6 次 search，
结构筛通过率 ~35%（正向 16.7%）。

过滤规则（决策 D3）：同一 issue 被 >3 个 PR 引用时，要求 PR 与 issue
创建同年才收录（过滤「万能引用」型老 issue，如 pydantic#123）。

缓存：output/discovery-cache.json —— 已检查的 (repo, issue, pr) 结构筛
结论持久化，重复扫描零 API 消耗。

用法：
  python3 runs/discover_reverse.py --target 300            # 全池积累候选
  python3 runs/discover_reverse.py --probe repo1,repo2      # 试制模式（新仓库取 2 个候选）
"""
import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request

TOK = os.environ.get("GITHUB_TOKEN")
# 双 Token 轮换（2026-09-16 用户提供 classic PAT）：search 30/min/token → 合计 60/min
TOKENS = [t for t in (os.environ.get("GITHUB_TOKEN"),
                      os.environ.get("GITHUB_TOKEN_2")) if t]
_tok_cycle = iter(lambda: 0, None)   # 占位，下方初始化
import itertools as _it
_tok_iter = _it.cycle(range(len(TOKENS)))
SEARCH_SLEEP = 2.2 if len(TOKENS) < 2 else 1.1   # 每分钟 search 预算 30×N

CACHE_PATH = "output/discovery-cache.json"
CLOSING = re.compile(r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", re.I)

# 仓库池（D2：试制验证准入。verified=已验证可用；probe=待试制；failed=已淘汰）
REPO_POOL = {
    "pallets/click":       "verified",
    "Textualize/rich":     "verified",
    "psf/requests":        "verified",
    "pypa/packaging":      "verified",
    "psf/black":           "verified",
    "pypa/pip":            "verified",
    "pypa/virtualenv":     "verified",
    # failed（试制淘汰）：pydantic/urllib3/poetry/httpx/build（harness/untestable）
    # failed（0 候选）：mypy/sqlalchemy（lib/ 布局不符结构筛）/certifi
    # 环境黑名单（历史实测）：marshmallow/attrs（ImportError）、aiohttp（C 构建）
    # 文化黑名单（0 配对）：werkzeug/jinja/flask/tqdm
}


def gh(path):
    tok = TOKENS[next(_tok_iter)]
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "rev-disc",
        "Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def search(q, page=1, n=100):
    tok = TOKENS[next(_tok_iter)]
    req = urllib.request.Request(
        f"https://api.github.com/search/issues?q={urllib.parse.quote(q)}"
        f"&sort=created&order=desc&per_page={n}&page={page}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "rev-disc",
                 "Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("items", [])


def load_done():
    done = set()
    try:
        for key in json.load(open("output/maker/claims.json")):
            if key.startswith("make/") and "#" in key:
                repo, issue = key[5:].rsplit("#", 1)
                done.add(f"{repo.replace('/', '__')}-{issue}")
    except FileNotFoundError:
        pass
    try:
        for l in open("output/maker/dataset.jsonl"):
            if l.strip():
                done.add(json.loads(l)["instance_id"])
    except FileNotFoundError:
        pass
    return done


def load_cache():
    try:
        return json.load(open(CACHE_PATH))
    except FileNotFoundError:
        return {}


def scan_repo(repo, done, cache, since="2023-01-01", max_files=10, max_lines=700):
    """反向扫描一个仓库：返回新合格候选 [(repo, issue, pr)]，并更新 cache。

    时间窗 2023-01 起（基座 py3.11 兼容窗口）；页深 5×100 PR/仓库。
    """
    pkg = repo.split("/")[-1]
    # ① 5 页 merged PR（每页 100），解析 closing keywords → (issue → [PR])
    refs = {}
    for page in range(1, 9):
        try:
            items = search(f"repo:{repo} is:pr is:merged", page=page)
        except urllib.error.HTTPError as e:
            print(f"  ⚠ search {e.code}（仓库路径/权限问题），跳过该仓库", flush=True)
            return []
        if not items:
            break
        for it in items:
            if it["created_at"] < since:
                continue
            m = CLOSING.search(it.get("body") or "")
            if m:
                refs.setdefault(m.group(1), []).append(
                    (it["number"], it["created_at"][:4]))
        time.sleep(SEARCH_SLEEP)   # search 30/min × token 数
    # ② D3 过滤：引用 >3 次的 issue 要求 PR 与 issue 同年
    hot = {i for i, prs in refs.items() if len(prs) > 3}
    year_cache = {}
    pairs = []
    for issue, prs in refs.items():
        iid = f"{repo.replace('/', '__')}-{issue}"
        if iid in done:
            continue
        if issue in hot:
            if issue not in year_cache:
                try:
                    year_cache[issue] = gh(
                        f"/repos/{repo}/issues/{issue}")["created_at"][:4]
                except Exception:
                    year_cache[issue] = None
            iyear = year_cache[issue]
            if not iyear:
                continue
            prs = [(n, y) for n, y in prs if y == iyear]
            if not prs:
                continue
        pairs.append((issue, max(prs)[0]))   # 取最新 PR
    # ③ 结构筛（缓存命中跳过）
    qualified = []
    for issue, pr in pairs:
        ck = f"{repo}#{issue}@{pr}"
        rec = cache.get(ck)
        if rec is None:
            try:
                files = gh(f"/repos/{repo}/pulls/{pr}/files")
                names = [f["filename"] for f in files]
                lines = sum(len((f.get("patch") or "").splitlines()) for f in files)
                tests = [n for n in names if re.search(r"tests?/|test_.*\.py$", n)]
                srcs = [n for n in names
                        if not re.search(r"tests?/|test_.*\.py$", n)
                        and (n.startswith("src/") or n.startswith(pkg + "/"))
                        and n.endswith(".py")]
                tp = "\n".join(f.get("patch") or "" for f in files
                               if f["filename"] in tests)
                rec = bool(tests and srcs
                           and re.search(r"^\+.*def test_", tp, re.M)
                           and len(names) <= max_files and lines <= max_lines)
            except Exception:
                rec = False
            cache[ck] = rec
            time.sleep(0.4)
        if rec:
            qualified.append({"repo": repo, "issue": int(issue), "pr": int(pr)})
    return qualified


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=0, help="积累候选目标数（0=不限）")
    ap.add_argument("--probe", default="", help="试制模式：逗号分隔仓库，各取最新 2 个候选")
    ap.add_argument("--repos", default="", help="覆盖仓库池（逗号分隔）")
    ap.add_argument("--out", default="runs/units-batch.json")
    args = ap.parse_args()

    done = load_done()
    cache = load_cache()
    pool = args.repos.split(",") if args.repos else list(REPO_POOL)
    if args.probe:
        pool = args.probe.split(",")

    all_units, stats = [], {}
    for repo in pool:
        t0 = time.time()
        q = scan_repo(repo, done, cache)
        stats[repo] = len(q)
        print(f"[{repo}] 新合格候选: {len(q)}（{round(time.time()-t0)}s）", flush=True)
        if args.probe:
            all_units.extend(q[:2])          # 试制：每仓库最新 2 个
        else:
            all_units.extend(q)
        if args.target and len(all_units) >= args.target:
            break

    json.dump(cache, open(CACHE_PATH, "w"), ensure_ascii=False, indent=1)
    # 去重（同 issue 多 PR 已在 scan 内取最新，此处防御性去重）
    seen, uniq = set(), []
    for u in all_units:
        k = f"{u['repo']}#{u['issue']}"
        if k not in seen:
            seen.add(k)
            uniq.append(u)
    json.dump(uniq, open(args.out, "w"), indent=1)
    print(f"\n合计: {len(uniq)} 个候选 → {args.out} | 各仓库: {stats}", flush=True)


if __name__ == "__main__":
    main()
