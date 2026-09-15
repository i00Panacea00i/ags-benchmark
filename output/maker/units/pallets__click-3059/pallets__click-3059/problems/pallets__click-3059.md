# 修复 Click 中 `invoke_without_command` 时命令未标记为可选的问题

在 Click 库中，`Group` 对象可通过 `invoke_without_command=True` 参数设置，使得在没有子命令被调用时执行默认操作。此时，子命令对于用户而言应是可选的，因此 `--help` 输出的 usage 行中，子命令占位符应被方括号（`[` `]`）包围，表示可选。然而，当前实现中，当 `invoke_without_command=True` 时，usage 行仍将子命令显示为必需（无方括号），与预期不符。

**问题复现示例**：
```python
import click

@click.group(invoke_without_command=True)
def main():
    if click.get_current_context().invoked_subcommand is not None:
        return
    # do something by default

if __name__ == '__main__':
    main()
```
执行 `app.py --help` 当前输出：
```
Usage: app.py [OPTIONS] COMMAND [ARGS]...
```
预期输出应为：
```
Usage: app.py [OPTIONS] [COMMAND] [ARGS]...
```

**环境信息**：Python 3.11.8，Click 8.2.0。

**行为级验收标准**：
1. 当 `Group` 设置了 `invoke_without_command=True` 时，其 `--help` 输出的 usage 行中，子命令占位符必须被方括号包围（即 `[COMMAND]`），而不是 `COMMAND`。当存在多个子命令时，应同样适用，例如 `[COMMAND1] [ARGS]... [COMMAND2 [ARGS]...]...`。
2. 当 `invoke_without_command=False`（默认）时，子命令占位符应保持无方括号（`COMMAND`），即原有行为不变。
3. 所有受影响的自动化测试用例必须通过，包括但不限于 `tests/test_commands.py` 中的 `test_subcommand_metavar_marks_optional`（其参数化组合 `[False-True-[COMMAND] [ARGS]...]` 和 `[True-True-[COMMAND1] [ARGS]... [COMMAND2 [ARGS]...]...]` 应全部变为绿色）。