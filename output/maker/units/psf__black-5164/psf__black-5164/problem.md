# Unexpected version warning

## 项目上下文
psf/black（Python 项目），涉及模块：CHANGES.md, src, tests。

## 问题描述
I'm getting 
```
Warning: Python 3.14 cannot parse code formatted for Python 3.15. To fix this: run Black with Python 3.15, set --target-version to py314, or use --fast to skip the safety check. Black's safety check verifies equivalence by parsing the AST, which fails when the running Python is older than the target version.
```
when running on 3.14, with `-t py310 -t py311 -t py312 -t py313 -t py314 -t py315`.

(the warning was introduced in #4983)

I would expect that warning if I only had `-t py315`, but why does it appear when I've asked it to make code formatted for 3.10->3.15 (which includes 3.14)? Should black always be run on the highest version it is formatting for?

BTW, there are no changes in output with and without `-t py315` for my use case.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：ce1897a8f20d。