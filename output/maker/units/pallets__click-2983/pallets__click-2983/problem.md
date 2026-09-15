# 为 Click 的 `argument` 参数添加 `help` 关键字支持

## 任务描述

当前 Click 库中，`@click.argument` 装饰器不支持 `help` 参数，而 `@click.option` 已支持。需要为 `click.argument` 添加 `help` 关键字参数，使用户可以像 `click.option('--count', default=1, help='number of greetings')` 一样，通过 `click.argument('name', help='The name to print')` 为参数指定帮助文本。

实现后，当命令行使用 `--help` 时，如果参数定义了 `help`，则应在帮助信息中显示该文本；如果未定义，则行为保持不变（不显示多余帮助文本）。同时需处理已弃用（deprecated）参数的情况：当 argument 同时设置了 `help` 和 `deprecated` 时，帮助文本应正确附加弃用标记，例如 `(DEPRECATED)` 或 `(DEPRECATED: USE B INSTEAD)`，且不应在 help 文本前出现多余空格。此外，`click.echo` 等现有 API 不应受影响。

需要修改的文件包括 `src/click/core.py`（实现 argument 类的 help 属性及帮助页生成逻辑）、`docs/arguments.md` 和 `docs/documentation.md`（更新文档说明），以及 `CHANGES.rst`（记录变更）。已有测试用例位于 `tests/test_arguments.py` 和 `tests/test_info_dict.py` 中。

## 验收标准

1. 使用 `click.argument('name', help='The name to print')` 定义参数后，运行 `--help` 时帮助信息中应显示 `The name to print`。
2. 未提供 `help` 参数时，帮助信息与之前一致，不显示额外文本。
3. 当 argument 同时指定了 `help` 和 `deprecated` 时，输出格式正确，例如 `(DEPRECATED)` 或 `(DEPRECATED: USE B INSTEAD)` 紧跟在 help 文本后，无多余前导空格。
4. 以下测试函数全部通过（无需编写或修改测试代码）：
   - `test_argument_help`
   - `test_argument_help_optional_metavar`
   - `test_deprecated_empty_help_no_leading_space[-True-(DEPRECATED)]`
   - `test_deprecated_empty_help_no_leading_space[-USE B INSTEAD-(DEPRECATED: USE B INSTEAD)]`
   - `test_deprecated_empty_help_no_leading_space[None-True-(DEPRECATED)]`
   - `test_deprecated_empty_help_no_leading_space[None-USE B INSTEAD-(DEPRECATED: USE B INSTEAD)]`
   - `test_deprecated_usage_help_record[True-(DEPRECATED)]`
   - `test_deprecated_usage_help_record[use g instead-(DEPRECATED: use g instead)]`

注意：不要添加测试代码或修复提示，仅实现功能并更新相关文档。