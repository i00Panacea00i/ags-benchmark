# 修复 Click 库中 Boolean flags 总是 False 的问题

在 Click 8.2.0 版本中，使用 `type=click.BOOL` 且 `is_flag=True` 定义的布尔选项在命令行中被错误解析：无论用户是否传递该标志，该选项的值始终为 `False`，而不会像 8.1.8 版本那样正确切换为 `True`。

## 重现步骤

1. 创建一个 Click 命令，包含以下选项：
   - `-v` / `--version`，类型 `click.BOOL`，默认值 `False`，设置 `is_flag=True`
   - `-h` / `--help`，类型 `click.BOOL`，默认值 `False`，设置 `is_flag=True`
   - `-n` / `--name`，类型 `click.STRING`，默认值 `"John Doe"`
2. 定义回调函数 `main(help, version, name)`，打印三个参数的值。
3. 从命令行运行：`python main.py --help --name Robert`

## 预期行为

`help` 应为 `True`，`version` 应为 `False`，`name` 应为 `"Robert"`（类似 Click 8.1.8 的行为）。

## 实际行为

输出：`help=False, version=False, name='Robert'`，所有布尔标志均未被识别，始终为默认值 `False`。

## 验收标准

- 当在命令行中提供 `--help` 或 `--version` 时，对应的 `help` 或 `version` 参数值必须为 `True`，而非默认的 `False`。
- 未提供的布尔标志保持默认值 `False`。
- 其他非布尔选项（如字符串选项）解析不受影响。
- 修复应覆盖所有使用 `type=click.BOOL` 且 `is_flag=True` 的情形，不限于示例中给出的三个选项。
- 通过以下测试用例（来自 `tests/test_options.py`）：
  - `test_flag_value_is_correctly_set[opts1-True-True]`
  - `test_flag_value_is_correctly_set[opts3-True-False]`
  - `test_flag_value_is_correctly_set[opts5-True-True]`
  - `test_flag_value_is_correctly_set[opts7-True-False]`
  - `test_flag_value_is_correctly_set[opts9-True-True]`