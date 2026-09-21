# 修复 zsh 补全在值包含冒号时的错误截断

在 `pallets/click` 仓库中，zsh 补全功能在补全项的 `value` 包含冒号 `:` 时行为不正确。需要修改 `src/click/shell_completion.py` 中 zsh 补全的生成/格式化逻辑，并按仓库惯例在 `CHANGES.rst` 中记录修复。

复现方式：编写脚本 `foo`：

```python
#!/usr/bin/env python3
from click.shell_completion import CompletionItem
import click

class Foo(click.ParamType):
    def convert(self, value, param, ctx):
        return value

    def shell_complete(self, ctx, param, incomplete):
        return [
            CompletionItem(value=value, help="adsf") for value in
            ["baz:quux", "spam:eggs"]
        ]

@click.command()
@click.argument("foo", type=Foo())
def main(foo):
    print(foo)
```

在 shell 中执行 `eval "$(_FOO_COMPLETE=zsh_source ./foo)"` 加载补全，然后输入 `foo <Tab>`。当前错误输出为：

```
baz   -- quux:adsf
spam  -- eggs:adsf
```

即 zsh 将 `value` 中的冒号当作值与帮助信息的分隔符，导致 `baz:quux` 被截断为 `baz`，剩余部分 `quux` 与 `help="adsf"` 拼接成 `quux:adsf`。

期望输出为：

```
baz:quux   -- adsf
spam:eggs -- adsf
```

验收标准：
1. 当 `CompletionItem` 的 `value` 含 `:` 时，zsh 补全必须把完整 `value`（如 `baz:quux`、`spam:eggs`）作为单个候选展示，帮助文本 `adsf` 独立显示在 `--` 之后，不得按冒号拆分或截断。
2. 选中候选后，实际补全/插入到命令行的应是完整的 `baz:quux` 或 `spam:eggs`，冒号保留。
3. 修复应位于 `src/click/shell_completion.py` 的 zsh 补全代码路径；不得通过修改 `tests/test_shell_completion.py` 或测试来规避。相关既有 zsh 补全测试应通过。