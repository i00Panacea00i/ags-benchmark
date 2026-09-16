# Allow `Pylock.select` to prefer source distributions

## 项目上下文
pypa/packaging（Python 项目），涉及模块：src, tests。

## 问题描述
The recommended pylock installation algorithm gives priority to wheels.

Pip has a `--no-binary` option to force installation from source on some packages.

To support that use case, I propose to add a `prefer_sdist_predicate: Callable[[NormalizedName], bool] | None = None` argument to `Pylock.select()`.

When the predicate returns True for a given package name, the algorithm will yield a PackageSdist if one exists, or a compatible PackageWheel if not, and raise if no sdist is present and no compatible wheel is available.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：9d0ec47b36a1。