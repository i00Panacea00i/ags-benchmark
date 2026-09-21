# (correctness): conflict checks are order-dependent when building the affected package whitelist

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
`pip install`'s post-resolution conflict check builds a whitelist of packages to check: the packages being installed/upgraded and their direct dependents.

That whitelist is currently order-dependent because `_create_whitelist()` checks dependency names against `packages_affected`, which is mutated while iterating over installed packages.

For example:

```text
root -> middle -> leaf
```

If `leaf` is installed/upgraded, `middle` should be included as a direct dependent. `root` should not be included under the current policy, but depending on installed distribution iteration order it may be included after `middle` is added to `packages_affected`.

The check should compare dependencies against the frozen `would_be_installed` set so the whitelist remains direct-only and deterministic.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：c8651d86d2d0。