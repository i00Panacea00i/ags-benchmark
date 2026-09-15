# [BUG] rich 库中 Panel 的 title 背景颜色丢失

在 rich 库的较新版本（例如 v13.9.4）中，使用 `Panel` 并为其设置 `style` 参数（包含背景色）时，`title` 文本的背景颜色不再与 `Panel` 的背景一致，而是显示为默认暗色背景。而在旧版本（例如 v13.0.1）中，`title` 文本会正确继承 `Panel` 的 `style` 背景色。

请复现并修复此问题，使得 `title` 的渲染效果与旧版本一致。

## 复现代码

```python
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
import os

console = Console()
console.print(Panel(
    str(os.environ),
    title='[bold white]Title[/bold white]',
    style=Style(color="white", bgcolor="blue")
))
```

## 期望行为

运行上述代码后，`Panel` 内部区域、边框以及 `title` 文本的背景均应为蓝色（由 `style` 参数中的 `bgcolor="blue"` 指定），`title` 文本颜色为白色。即整个 `Panel` 及其标题应呈现白字蓝底的效果。

## 实际行为（bug）

运行上述代码后，`Panel` 内部和边框的背景为蓝色，但 `title` 文本的背景变为默认的黑色（或终端暗色），导致标题文本难以阅读（白色文字显示在暗色背景上），不符合用户设置的 `style`。

## 验收标准

1. 使用上述复现代码，`title` 文本的背景应与 `Panel` 的 `style.bgcolor` 一致（即蓝色）。
2. 该修复应适用于所有操作系统（GNU/Linux 和 Windows）。
3. 该修复不应影响 `Panel` 的其他功能（如无 title 时或 title 使用不同样式时的渲染）。