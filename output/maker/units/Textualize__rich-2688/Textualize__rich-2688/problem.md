# 修复 ANSI 转义序列解析错误：\x1b(B\x1b[m

在 `rich` 中，`rich.text` 的 `Text.from_ansi` 解码部分 ANSI 序列时结果不正确。例如 mypy 彩色输出含 `\x1b[1m\x1b[31merror:\x1b(B\x1b[m ... \x1b(B\x1b[m\x1b[33m[misc]\x1b(B\x1b[m` 及结尾 `\x1b(B\x1b[m`。调用 `Text.from_ansi('\x1b[31mFound 4 errors in 2 files (checked 18 source files)\x1b(B\x1b[m\n')` 并用 `richprint` 输出会出现多余 `B`；而 `ansimarkup` 的 `ansiprint` 可正确打印。问题在 `rich/ansi.py` 未正确处理字符集选择序列 `\x1b(B`、`\x1b(J` 与重置序列 `\x1b[m` 的组合，导致 `B`、`J` 被当作普通字符或样式未重置。

请修改 `rich/ansi.py`，使 `Text.from_ansi` 正确忽略 `\x1b(B`、`\x1b(J` 等序列，并在 `\x1b[m` 后正确重置样式且不产生多余字符；可按仓库惯例更新 `CHANGELOG.md` 与 `CONTRIBUTORS.md`。

行为级验收标准：`Text.from_ansi` 对上述输入返回的 `plain` 不得包含多余 `B` 或 `J`，样式重置正确。`tests/test_ansi.py` 中 `test_decode_issue_2688` 参数化用例必须全部通过，包括：
- `test_ansi.py::test_decode_issue_2688[\x1b(BHal\x1b(Jlo-Hallo]`
- `test_ansi.py::test_decode_issue_2688[\x1b(BHallo-Hallo]`
- `test_ansi.py::test_decode_issue_2688[\x1b(JHallo-Hallo]`
- `test_ansi.py::test_decode_issue_2688[\x1b[31mFound 4 errors in 2 files (checked 18 source files)\x1b(B\x1b[m\n-Found 4 errors in 2 files (checked 18 source files)]`

即解码 `\x1b(BHal\x1b(Jlo` 得 `Hallo`，`\x1b(BHallo` 得 `Hallo`，`\x1b(JHallo` 得 `Hallo`，`\x1b[31mFound 4 errors in 2 files (checked 18 source files)\x1b(B\x1b[m\n` 得 `Found 4 errors in 2 files (checked 18 source files)`（无多余 `B`、无多余换行）。修复后 mypy 示例经 `Text.from_ansi` 与 `richprint` 输出不应再有尾随 `B`。