# pip show command builds the installed-files list even without --files

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
`pip show <pkg>` only prints installed files when `--files` is passed, but `search_packages_info()` always calls `iter_declared_entries()` and sorts the result for every matched distribution. that work is discarded in the default output.

the cost isn't a fixed per-package overhead; it scales with the number of entries in each package's `RECORD`, so it's most visible for large packages or when showing several at once.

`pip show` could gather installed files only when `--files` is set, while direct callers of `search_packages_info()` keep today's behavior by default.

**Benchmark**

same venv for both runs, switching only the pip source via PYTHONPATH. 2 warmups, 11 measured runs, median.

```text
# single
pip show Django
    baseline=0.1291s patched=0.1062s delta=0.0228s

# 3 dist
pip show Django scikit-learn scipy
    baseline=0.1447s patched=0.1141s delta=0.0305s

# 5 dist
pip show Django scikit-learn scipy numpy sympy
    baseline=0.1521s patched=0.1144s delta=0.0377s
```

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：6b0011b49a06。