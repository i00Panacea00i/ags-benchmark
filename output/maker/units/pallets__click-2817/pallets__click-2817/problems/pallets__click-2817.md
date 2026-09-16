# Set the `catch_exceptions` value for the whole runner

## 项目上下文
pallets/click（Python 项目），涉及模块：CHANGES.rst, src, tests。

## 问题描述
I always pass `catch_exceptions=False` for all my test suites.
It would be convenient to configure this value once for all in `CLIRunner` for example.

For example, we could add a `CLIRunner.catch_exceptions` parameter, and make `invoke` use that value if not directly passed in parameter of `invoke`. Then I would just have to put the runner in a pytest fixture and that would do the thing for me.

If that is OK, I can open a PR for this.

What do you think?

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：5961d31fb566。