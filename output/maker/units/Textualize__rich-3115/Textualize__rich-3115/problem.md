# 修复 Rich 中 Markdown 表格单元格仅渲染最后一个内联链接的问题

在 Rich 中，通过 `console = Console()` 创建实例并调用 `console.print(Markdown(md_table))` 渲染由 `pd.DataFrame(...).to_markdown()` 生成的 Markdown 表格时，若某单元格内含多个内联元素（如 `[page1](#page1), [page2](#page2)`，或多种内联样式），终端只显示最后一个（例如仅 `page2`），而期望按输入顺序完整显示所有文本与样式（例如 `page1, page2`）。将同一 Markdown 写入文件后渲染可得到正确结果，说明终端渲染路径存在缺陷。

请在 `rich/markdown.py` 中修复该问题：修复后，Markdown 表格单元格解析内联内容时应累积并依次渲染所有元素，而非覆盖式地只保留最后一个。相关行为由 `tests/test_markdown.py` 中的 `test_inline_styles_in_table`、`test_inline_styles_with_justification` 和 `test_markdown_table` 覆盖；这些测试应全部通过，并在 `CHANGELOG.md` 补充修复条目。

行为级验收标准：
1. 单元格含多个链接（如 `[page1](#page1), [page2](#page2)`）时，`console.print(Markdown(md_table))` 输出 `page1, page2`，而非仅 `page2`；混合内联样式也全部呈现。
2. 表格内联内容的对齐与样式在 `test_inline_styles_with_justification` 覆盖场景下保持正确，不因累积渲染而破坏对齐或丢失样式。
3. `test_inline_styles_in_table`、`test_inline_styles_with_justification` 与 `test_markdown_table` 均通过。
4. `CHANGELOG.md` 已新增条目，说明修复了 Markdown 表格单元格中多个内联链接/样式只显示最后一个的问题。