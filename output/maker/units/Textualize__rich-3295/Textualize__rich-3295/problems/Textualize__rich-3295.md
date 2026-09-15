# 编程任务：修复 Syntax 组件 background_color 覆盖时未包含 padding 区域的问题

## 任务描述

在 `rich` 库的 `Syntax` 类中，允许用户通过构造函数参数 `background_color` 覆盖主题中的背景色。根据文档说明，用户可以通过提供 `background_color` 参数来覆盖主题背景色。然而，当 `Syntax` 设置了 `padding`（例如 `padding=(1, 2)`）时，`background_color` 的覆盖效果并未应用到 padding 区域——只有代码文本区域的背景色被更改，而 padding 区域仍保持主题默认背景色。

此外，当将 `background_color` 设置为特殊值 `"default"` 时，会产生与预期不符的意外结果（例如可能完全未覆盖或导致显示异常）。

相关文件位于仓库的 `rich/syntax.py` 中。请修复此问题，使得：

1. 当通过构造函数指定 `background_color` 参数（非 `None`，非 `"default"`）时，整个 `Syntax` 组件（包括所有由 padding 产生的空白区域）的背景色都应为该指定颜色。
2. 当 `background_color` 设置为 `"default"` 时，应使用主题默认背景色，且 padding 区域也应与代码区域背景色保持一致（即不应用任何覆盖）。

## 验收标准

- 运行以下示例代码，输出中 `Syntax` 的 padding 区域（上下左右各 1 行和 2 列的空白）的背景色应为红色（与代码部分一致），而非默认主题背景色：

```python
from rich.console import Console
from rich.syntax import Syntax

code = """\
def do_something():
    pass\
"""

console = Console()

syntax = Syntax(
    code,
    lexer="python",
    word_wrap=False,
    indent_guides=True,
    padding=(1, 2),
    theme="material",
    background_color="red",
)

console.print(syntax)
```

- 将 `background_color` 改为 `"default"` 时，输出中整个 `Syntax` 组件（包括 padding）应使用 `theme="material"` 的主题默认背景色，且无异常显示（例如不应出现透明或不一致的颜色）。
- 不修改现有测试文件 `tests/test_syntax.py` 中的测试用例，但应确保新增行为不会破坏原有测试，尤其是 `test_background_color_override_includes_padding` 这一测试（预期该测试应通过）。