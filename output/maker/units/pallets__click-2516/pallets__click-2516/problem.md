# 重构选项帮助额外项的计算与渲染

在 Click 中，命令行选项的帮助信息末尾会渲染一些额外项（extra items），它们显示在方括号中，例如 `[default: None]`、`[default: (unlimited)]`、`[env var: COLOR_CLI8_TIME; default: no-time]` 等多种格式。目前，这些额外项的生成逻辑深埋在 `Option.get_help_record()` 方法内部，无法被独立获取，只能依赖脆弱的正则表达式从最终帮助文本中匹配。

请对 `Option.get_help_record()` 进行重构，将“额外项的计算”与“帮助记录的渲染”拆分开来：新增一个方法，用于计算并返回这些额外项的值；同时保留原有的 `get_help_record()` 方法，使其仅负责帮助信息的渲染，不再直接内联生成额外项。重构不应改变现有帮助输出的格式和内容。

涉及文件包括 `CHANGES.rst`、`src/click/core.py`、`src/click/types.py` 与 `tests/test_options.py`。

行为级验收标准：完成修改后，`Option.get_help_record()` 仍能正确渲染选项帮助记录，且新增的计算方法可独立返回上述额外项的值；原有帮助文本中 `[default: None]`、`[default: (unlimited)]`、`[env var: COLOR_CLI8_TIME; default: no-time]` 等格式保持不变。当 `tests/test_options.py` 中的 `test_count_default_type_help`、`test_do_not_show_default_empty_multiple`、`test_do_not_show_no_default`、`test_dynamic_default_help_special_method`、`test_file_type_help_default`、`test_hide_false_default_boolean_flag_value[False]`、`test_hide_false_default_boolean_flag_value[None]`、`test_intrange_default_help_text[type0-1<=x<=32]` 全部通过时，视为修复完成。