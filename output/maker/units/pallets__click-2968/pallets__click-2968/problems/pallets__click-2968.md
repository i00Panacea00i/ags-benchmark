# 修复 click.prompt 在 Linux 上 backspace 与换行异常的问题

## 问题描述
在 Linux 系统下使用 `click.prompt` 时，退格键（backspace）表现异常：按一次退格键会删除两个字符，连续退格至行尾时还会删除整个提示文本（prompt）。同时，控制台返回的输入内容与屏幕上实际显示的文字不一致。该问题在 Python 3.13.3、Click 8.2.1 环境下可复现。

## 根因分析
`src/click/termui.py` 中包含一段针对 Windows 的兼容处理，该处理由 `click` 自行打印 readline 的提示字符串。在 Linux 上，这一动作会干扰 readline 库的内部状态，导致 readline 无法正确管理光标、退格及行换行行为，从而出现删除字符数量错误、提示文本被意外擦除等现象。

## 任务目标
修改 `src/click/termui.py` 中的逻辑，使 Linux 环境下 `click.prompt` 完全交由 readline 库处理提示字符串的显示，移除当前为 Windows 设计的干预代码在 Linux 上的副作用。具体修改须确保 `click.prompt` 在 Linux 终端下的交互行为符合预期。

## 行为级验收标准
- 在 Linux 终端中运行任意使用了 `click.prompt` 的应用，按一次退格键仅删除一个输入字符，不是两个。
- 连续按退格键直至输入为空时，提示文本（prompt 字符串）不会被删除，仍应完整显示在行首。
- 输入内容与屏幕上显示的内容完全一致（例如键入“abc”，屏幕显示“abc”，返回值为“abc”）。
- 使用 Ctrl+Backspace 组合键时应删除一个单词，而非异常行为。
- 当输入内容超出终端宽度触发自动换行时，换行后的行光标位置正确，不会出现文本重叠或错位。
- 原有 Windows 平台的兼容行为不受影响（Windows 下仍需保持现有处理方式）。
- 相关测试用例（如 `tests/test_utils.py` 中的 `test_echo_writing_to_standard_error`、`test_full_prompt_passed_to_readline` 系列以及 `test_prompts_abort`）在 Linux 上应全部通过。

## 约束
- 不修改 `CHANGES.rst` 以外的文档或测试代码。
- 仅调整 `src/click/termui.py` 中与 readline 提示相关的逻辑分支。
- 不得添加新的外部依赖或重写整个 prompt 系统。