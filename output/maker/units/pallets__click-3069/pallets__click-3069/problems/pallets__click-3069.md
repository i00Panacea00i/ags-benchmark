# 修复未传值时 `Sentinel` 被传入 `type_cast_value` 的问题

自 click 8.3.0 起，若命令行未提供值，`Parameter` 及其子类（如 `Option`、`Argument`）的 `type_cast_value` 会收到 `Sentinel` 对象，而非 `None` 等未设置值，破坏了自定义子类对 `type_cast_value` 的重写。

复现：在 `cli_bug.py` 中定义 `class CSVOption(click.Option)`，重写 `def type_cast_value(self, ctx, value):`，当 `value` 为真时 `return value.split(",")`，否则 `return value`。用 `@click.command(name="run")` 与 `@click.option("--csv", cls=CSVOption)` 定义 `main(csv)`，并调用 `click.echo(f"{csv!r}")`。不传 `--csv` 运行 `main()` 时，调用链 `make_context` → `parse_args` → `handle_parse_result` → `process_value` 执行 `type_cast_value(ctx, value)`，因 `value` 是 `Sentinel` 而抛出 `AttributeError: 'Sentinel' object has no attribute 'split'`。

需修改 `src/click/core.py` 中 `Parameter`、`Option`、`Argument` 的解析逻辑，并更新 `CHANGES.rst`。修复后，`type_cast_value` 在未传值时不应收到 `Sentinel`，自定义子类应 “never sees unset”，即收到 `None` 或非 `Sentinel` 的未设置值，或不在未设置时被调用。

行为级验收标准：
1. 不传 `--csv` 时不再抛出 `AttributeError: 'Sentinel' object has no attribute 'split'`，正常输出 `None`（或等价未设置表示）。
2. 传 `--csv a,b` 时，`type_cast_value` 收到字符串并返回 `['a', 'b']`，输出 `['a', 'b']`。
3. 自定义 `Option`/`Argument` 子类重写 `type_cast_value` 时，无论是否提供值都不会观测到 `Sentinel`；未设置表现为 `None`/缺失，已设置正常转换。
4. 回归测试 `tests/test_arguments.py::test_argument_custom_class_can_override_type_cast_value_and_never_sees_unset[argument_kwargs1-pass_argv1]`、`tests/test_arguments.py::test_argument_custom_class_can_override_type_cast_value_and_never_sees_unset[argument_kwargs4-pass_argv4]`、`tests/test_options.py::test_option_custom_class_can_override_type_cast_value_and_never_sees_unset[--opt-option_kwargs0-pass_argv0]`、`tests/test_options.py::test_option_custom_class_can_override_type_cast_value_and_never_sees_unset[--opt-option_kwargs1-pass_argv1]` 全部通过。