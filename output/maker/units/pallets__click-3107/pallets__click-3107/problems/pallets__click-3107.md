# 任务描述：为拼写错误的子命令添加"Did you mean"提示

当前 Click 库（Python 3.13.8）在用户拼写命令行选项（如 `--nme`）时，能够给出友好的 `Did you mean --name?` 错误消息。然而，当用户拼写子命令（例如将 `greet` 写为 `gret`）时，仅显示 `Error: No such command 'gret'.`，没有任何 `Did you mean...` 建议。这一缺失降低了 CLI 应用的易用性。

请修改相关逻辑，使得当用户输入不存在的子命令且该输入与某个已注册命令名称相似时，也能输出类似选项拼写错误时的 `Did you mean...` 提示。相似度判定应基于编辑距离或其他合理算法，并与现有选项拼写建议的机制保持一致。

**行为示例**  
考虑以下 CLI 应用：

```python
import click

@click.group()
def cli():
    pass

@cli.command()
@click.option("--name", "-n", default="World")
def greet(name: str) -> None:
    click.echo(f"Hello, {name}")

@cli.command()
@click.option("--name", "-n", default="Friend")
def farewell(name: str) -> None:
    click.echo(f"Goodbye, {name}")

if __name__ == "__main__":
    cli()
```

当前当用户执行 `python main.py gret --name David` 时，输出：

```
Usage: main.py [OPTIONS] COMMAND [ARGS]...
Try 'main.py --help' for help.

Error: No such command 'gret'.
```

期望输出应包含类似 `Did you mean 'greet'?` 的建议。

**验收标准**

1. 若输入的命令名称与某个已注册命令名称相似（例如仅一个字符不同或通过编辑距离算法判定为近似），应输出单个建议，格式为 `Did you mean 'correct_command'?`。例如输入 `pause` 时应提示 `Did you mean 'push'?`。
2. 若输入的命令名称与多个已注册命令名称相似，应列出所有可能选项，格式为 `Did you mean one of: 'command1', 'command2'?`。例如输入 `decline` 时应提示 `Did you mean one of: 'declare', 'refine'?`。
3. 选项拼写错误的现有行为不受影响（仍应输出 `Did you mean` 提示）。例如 `--bounds` 应提示 `Did you mean one of: '--bound', '--count'?`，`--cat` 应提示 `Did you mean '--count'?`。
4. 对于完全不匹配的输入（无近似命令），不应给出建议，仅保留原有错误消息。
5. 所有现有的相关测试（如 `test_suggest_possible_commands`、`test_suggest_possible_options`、`test_unknown_options`）必须继续通过。

请实现此功能，确保 `Did you mean...` 消息的格式与选项建议完全一致（包括标点与大小写），并保留所有代码标识符原样，例如 `__main__`、`__name__`、`click.echo`、`e.g.`、`main.py` 以及 `mean...` 等。