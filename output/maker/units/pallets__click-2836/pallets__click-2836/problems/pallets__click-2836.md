# 任务：修复 `click.Option` 中 `show_default` 为字符串时在 prompt 中未正确显示的问题

在 `pallets/click` 仓库（版本 `8.1.6`，Python `3.11.6`）中，`click.Option` 的 `show_default` 参数支持传入字符串，用于在帮助文本中自定义默认值的显示方式。当 `show_default` 设为字符串时，帮助文本会正确显示 `[default: (show_default)]`，但在交互式 prompt 中（当同时设置 `prompt=True` 时），prompt 仍然只显示实际的默认值，而非 `show_default` 指定的字符串。

例如，定义如下选项：

```python
@click.option("--name", default="default", show_default="show_default", prompt=True)
```

预期在帮助文本中显示：
```
--name TEXT  [default: (show_default)]
```
实际在 prompt 中显示：
```
Name [default]:
```
期望 prompt 也应显示 `show_default` 字符串，即：
```
Name [show_default]:
```

**涉及文件**：`src/click/core.py`、`src/click/termui.py`，以及相关的测试文件 `tests/test_options.py`、`tests/test_termui.py` 和更新日志 `CHANGES.rst`。

**验收标准**：
- 当 `show_default` 为字符串时，prompt 中应显示该字符串，而非 `default` 参数的原始值。
- 当 `show_default` 为 `True` 时，prompt 行为保持不变（仍显示 `default` 参数值）。
- 当 `show_default` 为 `None` 或 `False` 时，prompt 不应显示任何默认值（保持现有行为）。
- 所有现有相关测试（如 `test_string_show_default_shows_custom_string_in_prompt` 和 `test_string_show_default_in_prompt` 下的多个子用例）应全部通过，且新增或修改的代码不应破坏已有功能。
- 修复后，使用 `foo.py` 运行示例应输出预期的 prompt 文本。