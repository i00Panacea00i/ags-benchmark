#!/usr/bin/env python3
"""压测单元发现：跨仓库筛选合格工作单元（配对+结构双筛），输出候选清单与统计。

筛选条件（与 maker 漏斗对齐，最大化 F2P 通过率）：
- closed issue + merged PR 配对（GitHub 全套 closing keywords，搜索式配对）
- PR 同时改动 tests 与源码，且新增测试函数
- 体量 ≤8 文件 ≤500 行（F2P 快速收敛）
- 创建时间 ≥2024-06（Python 3.12 兼容窗口）
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

TOK = os.environ["GITHUB_TOKEN"]
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 24

REPOS = ["pallets/click", "pypa/packaging", "marshmallow-code/marshmallow",
         "python-attrs/attrs", "pallets/werkzeug", "pallets/jinja", "tqdm/tqdm"]
DONE = set()   # 从数据集与历史扫描载入


def gh(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "stress-discovery",
        "Authorization": f"Bearer {TOK}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def search(q, n=100):
    req = urllib.request.Request(
        f"https://api.github.com/search/issues?q={urllib.parse.quote(q)}"
        f"&sort=created&order=desc&per_page={n}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "stress-discovery",
                 "Authorization": f"Bearer {TOK}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("items", [])


def load_done():
    try:
        for l in open("output/maker/dataset.jsonl"):
            if l.strip():
                r = json.loads(l)
                DONE.add(r["instance_id"])
    except FileNotFoundError:
        pass
    # 历史已扫描/已制作号段（click / packaging 等）
    for repo, nums in {
        "pallets__click": [3572, 3822, 2582, 3740, 3571, 3145, 3360, 3277, 3298, 3242, 3237, 3449],
        "pypa__packaging": [1204, 1333, 1067, 1315, 1318, 1178, 1162, 1154, 1066, 945, 909, 885, 859, 831],
    }.items():
        for n in nums:
            DONE.add(f"{repo}-{n}")


def screen(repo, issue):
    """返回 (PR dict | None, 淘汰原因)。"""
    closing = re.compile(rf"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#{issue}\b", re.I)
    q = urllib.parse.quote(f"repo:{repo} is:pr is:merged {issue} in:body")
    hit = None
    for it in gh(f"/search/issues?q={q}&per_page=10").get("items", []):
        if closing.search(it.get("body") or ""):
            pr = gh(f"/repos/{repo}/pulls/{it['number']}")
            if pr.get("merged"):
                hit = pr
                break
    if not hit:
        return None, "no_paired_pr"
    files = gh(f"/repos/{repo}/pulls/{hit['number']}/files")
    names = [f["filename"] for f in files]
    lines = sum(len((f.get("patch") or "").splitlines()) for f in files)
    tests = [n for n in names if re.search(r"tests?/|test_.*\.py$", n)]
    pkg = repo.split("/")[-1]
    srcs = [n for n in names if n.startswith("src/") or n.startswith(pkg + "/") or n.endswith(".py")]
    tpatch = "\n".join(f.get("patch") or "" for f in files if f["filename"] in tests)
    adds_test = bool(re.search(r"^\+.*def test_", tpatch, re.M))
    if not (tests and srcs and adds_test):
        return None, "structure"
    if len(names) > 8 or lines > 500:
        return None, "size"
    return hit, None


def main():
    load_done()
    picked, stats = [], {"scanned": 0, "no_paired_pr": 0, "structure": 0, "size": 0, "done": 0}
    t0 = time.time()
    for repo in REPOS:
        if len(picked) >= TARGET:
            break
        try:
            items = search(f"repo:{repo} is:issue is:closed linked:pr")
        except Exception as e:
            print(f"[{repo}] search err: {str(e)[:60]}")
            continue
        pool = [it for it in items
                if it["created_at"] >= "2024-06-01"
                and f"{repo.replace('/', '__')}-{it['number']}" not in DONE]
        stats["done"] += len(items) - len(pool)
        print(f"[{repo}] 池 {len(items)}，时间窗内未做 {len(pool)}")
        for it in pool:
            if len(picked) >= TARGET:
                break
            stats["scanned"] += 1
            try:
                pr, why = screen(repo, it["number"])
                if pr:
                    picked.append({"repo": repo, "issue": it["number"], "pr": pr["number"]})
                    print(f"  PASS {repo}#{it['number']} ← PR#{pr['number']} | {it['title'][:50]}")
                else:
                    stats[why] += 1
            except Exception as e:
                print(f"  #{it['number']} err: {str(e)[:50]}")
            time.sleep(1.5)   # 搜索 API 30/min
    stats["elapsed_s"] = round(time.time() - t0, 1)
    stats["picked"] = len(picked)
    json.dump(picked, open("runs/units-stress.json", "w"), indent=1)
    print(f"\n选定 {len(picked)}/{TARGET} | 统计: {stats}")
    json.dump(stats, open("output/stress/01-discovery-stats.json", "w"), indent=1)


if __name__ == "__main__":
    main()
