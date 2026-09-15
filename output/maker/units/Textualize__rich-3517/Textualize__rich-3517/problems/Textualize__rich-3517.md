# 修复 Table 自动高亮功能在 v13.8.1 后的回归问题

## 问题描述
在 rich 库 v13.8.1 版本之后，`Table` 对象的 `highlight=True` 参数不再生效，单元格内容无法被自动高亮显示。该功能在 v13.7.1 版本中正常工作。用户通过 `python -m rich.diagnose` 获取的诊断信息包含以下属性：`color_system`, `is_alt_screen`, `is_dumb_terminal`, `is_interactive`, `rich.console.Console`, `_io`, `_io.TextIOWrapper`。

## 重现步骤
1. 安装 rich 版本 >=13.8.1。
2. 运行以下 Python 代码：
   ```python
   from rich import print
   from rich.table import Table

   t = Table(highlight=True, show_header=False)
   t.add_row("1", repr("FOO"))
   print(t)
   ```
3. 观察输出：单元格内容（例如 `'FOO'` 的 repr 值）应被自动高亮（通常为特定颜色），但实际输出为普通文本，没有高亮效果。

## 期望行为
当 `Table(highlight=True)` 时，通过 `add_row` 添加的单元格内容应自动应用 rich 的渲染高亮规则（例如字符串字面量、数字等被着色）。该行为应与 v13.7.1 一致。

## 验收标准
- 运行上述重现代码，输出的表格中单元格文本应包含 ANSI 转义序列或 rich 样式，即自动高亮效果可见（例如字符串 `'FOO'` 显示为绿色或其他高亮颜色）。
- 该修复不应影响 `highlight=False` 的默认行为（即不应用自动高亮）。
- 所有涉及的文件（如 `CHANGELOG.md`, `rich/table.py`, `tests/test_table.py`）应保持一致性，但无需新增测试。
- 修复后，用户通过 `python -m rich.diagnose` 获取的诊断信息中，`color_system` 等属性应正常显示（不要求更改，仅确保不影响诊断输出）。