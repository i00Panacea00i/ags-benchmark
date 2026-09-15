#!/usr/bin/env python3
"""压测候选补充：修正结构筛选（排除纯测试 PR），从 click/marshmallow 深池补 8 个。"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

TOK = os.environ["GITHUB_TOKEN"]
NEED = int(sys.argv[1]) if len(sys.argv) > 1 else 8

REPOS = ["pypa/packaging", "pallets/click"]
# 压测补充：放宽体量（≤10 文件/700 行）与时间窗（2024-01 起）
SIZE_FILES, SIZE_LINES, SINCE = 10, 700, "2024-01-01"
# 已处理（含本轮 24 个 + 历史）
DONE = {
    "pallets__click": [3572, 3822, 2582, 3740, 3571, 3145, 3360, 3277, 3298, 3242,
                       3237, 3449, 3107, 3105, 3084, 3071, 3059, 2983, 2968, 2906,
                       2897, 2869, 2860, 2836, 2832, 2819],
    "pypa__packaging": [1204, 1333, 1067, 1315, 1318, 1178, 1162, 1154,
                        1066, 945, 909, 885, 859, 831],
    "marshmallow-code__marshmallow": [2985, 2936, 2900, 2870, 2868],
    "python-attrs__attrs": [1575, 1479, 1427, 1416, 1400],
    "Textualize__rich": [3881, 3569, 3517, 3295],
    "psf__requests": [],
    "aio-libs__aiohttp": [],
    "encode__httpx": [],
}


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


def screen(repo, issue):
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
    # ★ 修正：src = 非测试的包内 .py（src/ 布局或 <pkg>/ 布局），排除 tests
    pkg = repo.split("/")[-1]
    srcs = [n for n in names
            if not re.search(r"tests?/|test_.*\.py$", n)
            and (n.startswith("src/") or n.startswith(pkg + "/"))
            and n.endswith(".py")]
    tpatch = "\n".join(f.get("patch") or "" for f in files if f["filename"] in tests)
    adds_test = bool(re.search(r"^\+.*def test_", tpatch, re.M))
    if not (tests and srcs and adds_test):
        return None, "structure"
    if len(names) > SIZE_FILES or lines > SIZE_LINES:
        return None, "size"
    return hit, None


def main():
    picked = []
    for repo in REPOS:
        if len(picked) >= NEED:
            break
        items = search(f"repo:{repo} is:issue is:closed linked:pr")
        pool = [it for it in items if it["created_at"] >= SINCE
                and it["number"] not in DONE[f"{repo.replace('/', '__')}"]]
        print(f"[{repo}] 时间窗内候选 {len(pool)}")
        for it in pool:
            if len(picked) >= NEED:
                break
            try:
                pr, why = screen(repo, it["number"])
                if pr:
                    picked.append({"repo": repo, "issue": it["number"], "pr": pr["number"]})
                    print(f"  PASS {repo}#{it['number']} ← PR#{pr['number']} | {it['title'][:48]}")
            except Exception as e:
                print(f"  #{it['number']} err: {str(e)[:50]}")
            time.sleep(1.5)
    json.dump(picked, open("runs/units-topup.json", "w"), indent=1)
    print(f"补充 {len(picked)}/{NEED}")


if __name__ == "__main__":
    main()
