# 修复 Click 中 `is_flag=False` 与 `flag_value` 组合的 Bug

## 任务描述
在 Click 库中，当为一个选项设置 `is_flag=False` 和 `flag_value` 时，该选项应该可以接受一个可选的参数值：若只提供标志（例如 `--name`）而不提供具体参数，则选项的值应自动取为 `flag_value`；若显式提供参数，则取实际传入的值。该行为在 8.3.0 版本中被破坏：当前当只提供标志时，Click 会抛出 `SystemExit` 并显示错误信息 `"Error: Option '--xyz' requires an argument."`，导致程序异常退出。

重现示例（来自官方文档）：
```python
@click.command()
@click.option("--name", is_flag=False, flag_value="Flag", default="Default")
def hello(name):
    click.echo(f"Hello, {name}!")
```
运行 `hello --name` 时，期望输出 `Hello, Flag!`，但实际输出错误 `Error: Option '--name' requires an argument.`。

需要恢复该功能，使 `is_flag=False` 且提供了 `flag_value` 的选项在仅使用标志时自动取 `flag_value`，而不要求用户提供额外参数。

## 验收标准
- 对于上述示例代码，执行 `hello --name` 应输出 `Hello, Flag!`，不再抛出异常。
- 当显式提供参数时（例如 `hello --name World`），应输出 `Hello, World!`，行为不变。
- 当不提供该选项时（例如 `hello`），应使用 `default` 值，输出 `Hello, Default!`。
- 上述三种情况应兼容于所有选项类型（包括字符串、整数等），并保证 `flag_value` 与选项类型匹配时正常工作。
- 现有测试套件中 `tests/test_options.py::test_flag_value_on_option_with_zero_or_one_args` 的两个测试用例（含 `int` 和 `str` 参数的变体）应全部通过。