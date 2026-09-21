# Provide Public API to normalize version parts

## 项目上下文
pypa/packaging（Python 项目），涉及模块：src, tests。

## 问题描述
As we push users to only use public APIs in packaging one thing I notice is that hatch needs to use the private function `_parse_letter_version`: 

This is actually reasonable that project management utilities would want to be able to normalize part of a version such as the pre or post-release part without needing or wanting to construct a whole version.

It is even useful for interacting with the `__replace__` API which currently only takes the normalized pre-release parts, so you need to normalize them before passing them in.

I have not thought out what a good public API would look like, we could simply make private functions public, or there may be a better approach.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：77a4f3fe0bcf。