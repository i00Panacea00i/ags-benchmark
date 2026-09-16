# strip "_command" suffix when generating command name

## 项目上下文
pallets/click（Python 项目），涉及模块：CHANGES.rst, src, tests。

## 问题描述
You often want a command to have the same name as a function it is wrapping. However, this will cause a name collision, if your command is going to call `init_data` its function can't also be called `init_data`. So instead it's written as `init_data_command`, and then the command name has to be specified manually `("init-data")`. Click should remove a `_command` suffix when generating the command name from the function name.

```python
def init_data(external=False):
    ...

.command
.option("--external/--internal")
def init_data_command(external):
    init_data(external=external)

```

Currently this command would be named `init-data-command`. After the change, it would be `init-data`.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：b63ace28d50b。