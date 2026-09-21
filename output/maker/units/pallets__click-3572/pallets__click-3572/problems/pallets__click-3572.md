# 修复 click.confirm 在 color=False 时未去除 ANSI 转义码的问题

在 pallets/click 仓库中，升级到 click 8.4 后出现回归：click.confirm 在 color=False 时未去除 ANSI 转义码，而 click.echo 表现正常。复现方式为定义使用 .command() 装饰的 cmd 与 cmd_confirm：cmd 调用 click.echo(click.style('Hello World!', fg='green'))，cmd_confirm 调用 click.confirm(click.style('Hello World!', fg='green'), abort=True)。通过 CliRunner 执行 runner.invoke(cmd, color=False) 时，result.output 为 "Hello World!\n"；执行 runner.invoke(cmd_confirm, input="Y", color=False) 时，result.output 应为 "Hello World! [y/N]: Y\n"，但实际包含 ANSI 序列，导致 test_confirm_strips_ansi_with_color_false 失败，而 test_echo_strips_ansi_with_color_false 通过。在 click 8.3.3 中两者均通过；在 click 8.4.0 与 click 8.4.1 中失败。报错消息原文为：

```
>       assert result.output == "Hello World! [y/N]: Y\n"  # FAILS: ANSI codes present
```

期望行为是 "The ansi codes should be stripped"，即 color=False 时 click.confirm 的提示文本不应保留 ANSI 转义码，应与 click.echo 一致。

请在 src/click/termui.py 中修复 click.confirm（以及 click.prompt）对 ANSI 的处理，使 color=False 生效，并在 CHANGES.md 中记录修复。验收标准：tests/test_termui.py::test_prompt_and_confirm_ansi_respects_color[confirm-no-color] 与 tests/test_termui.py::test_prompt_and_confirm_ansi_respects_color[prompt-no-color] 均通过；且上述 cmd_confirm 场景下 result.output 等于 "Hello World! [y/N]: Y\n"，不含任何 ANSI 转义码；click.prompt 在 color=False 时同样去除 ANSI。