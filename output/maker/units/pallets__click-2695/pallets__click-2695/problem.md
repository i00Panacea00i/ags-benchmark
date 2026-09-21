# show envvar in error hint

## 项目上下文
pallets/click（Python 项目），涉及模块：CHANGES.rst, src, tests。

## 问题描述
```py
.command()
.option('--a', required=True, envvar="b", show_envvar=True)
def f(a): ...
f()
```
Here I would want the error message to show the env var.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：0e0c00324a5a。