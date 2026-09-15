# Click 帮助参数自动解析失败：当自定义参数名为“help”时

## 问题描述

在 Click 库（版本 8.1.7，Python 3.10.15）中，根据文档说明，`--help` 参数由 Click 自动为每个命令添加，并具备自动冲突解决能力：如果命令自身定义了一个同名参数，则默认的帮助参数会停止接受该名称。然而，实际行为与此不符。

当命令的 `argument` 或 `option` 使用名称 `help` 时，自动帮助参数并未正确解析冲突，导致以下异常：

- 定义一个 argument 名为 `help` 的命令（例如 `this_does_not_work`），执行 `python help.py somevalue` 时，Click 错误地将 `somevalue` 解释为 `--help` 选项的值，报错：“Invalid value for '--help': 'somevalue' is not a valid boolean.” 而正确的行为应该是将 `somevalue` 传给 argument `help`，并显示帮助信息当使用 `--help` 时。
- 定义一个 option 名为 `--help` 且带有默认值的命令（例如 `this_does_not_work_also`），执行 `python help.py` 时输出 `None`（预期输出默认值 `'this_2'`），且执行 `python help.py --help` 时错误提示“Option '--help' requires an argument.” 正确的行为应该是 `--help` 被视为自定义选项，而非触发帮助显示。

参考代码（仅示意问题，不要求复现）：

```python
import click

@click.command()
@click.argument('help')
def this_does_not_work(help):
    print(help)

@click.command()
@click.option('--help', default='this_2')
def this_does_not_work_also(help):
    print(help)
```

作为对比，若参数名为 `helps`（例如 `this_works`），一切正常。

## 验收标准

修复后应满足以下所有行为：

1. 当命令定义了一个名为 `help` 的 `argument` 时（如 `this_does_not_work`），执行 `python help.py somevalue` 应输出 `somevalue`，且 `python help.py --help` 应正常显示帮助信息。
2. 当命令定义了一个名为 `--help` 的 `option` 且带有默认值时（如 `this_does_not_work_also`），执行 `python help.py` 应输出该默认值（例如 `'this_2'`），执行 `python help.py --help` 应将该 `--help` 视为自定义选项（要求提供值或使用默认值），而不是触发内置帮助显示。同时，用户仍可通过 `help_option_names` 配置的其他名称（如 `-h`）访问内置帮助（若已配置）。
3. 原有的自动帮助冲突解决机制应适用于所有参数名称，包括 `help`，且不破坏其他正常功能（如 `this_works` 等示例仍正常工作）。