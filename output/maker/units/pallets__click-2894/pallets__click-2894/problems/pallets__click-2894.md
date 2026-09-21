# 修复 Click 中带 type 的 is_flag 选项被忽略的问题

在 `pallets/click` 仓库中，涉及 `src/click/core.py`、`CHANGES.rst` 与 `tests/test_options.py`。在 `Click 8.2.0` 中，使用 `is_flag=True` 且指定 `type=str` 定义的选项会被错误处理：值未被设置，保持为 `None`。而在 `Click 8.1.8` 中，`type=str` 被忽略，选项按 `is_flag` 正常处理，传入标志时值为 `True`。

复现：在 `main.py` 中定义 `cli`，使用 `.group(invoke_without_command=True)` 与 `.option('-x', '--transpose', type=str, is_flag=True, help='Transpose the output table.')`，参数为 `transpose`，并调用 `print(f"Debug: transpose={transpose}")`。在 `Click 8.2.0` 下执行 `python -c "import main,sys; sys.argv=['cli', '--transpose']; main.cli()"` 输出 `Debug: transpose=None`；期望输出 `Debug: transpose=True`（与 `Click 8.1.8` 一致）。

问题源于 `src/click/core.py` 中 `is_flag` 与 `type` 的处理逻辑：当 `is_flag` 为真且 `type` 不为 `None` 时，未正确推导 `flag_value` 与 `self.type`。相关标识符包括 `flag_value`、`self.default`、`self.type`、`types.ParamType`、`types.convert_type`，以及 `if flag_value is None:`、`flag_value = not self.default`、`if is_flag and type is None:`、`self.type = types.convert_type(None, flag_value)`。

验收标准：修复后，同时声明 `is_flag=True` 和 `type` 的选项必须优先按标志处理；传入标志时值应被正确设置为对应标志值（如 `True`），而非 `None`。需使以下测试全部通过：`tests/test_options.py::test_flag_value_is_correctly_set[opts1-True-True]`、`tests/test_options.py::test_flag_value_is_correctly_set[opts3-True-False]`、`tests/test_options.py::test_flag_value_is_correctly_set[opts5-True-True]`、`tests/test_options.py::test_flag_value_is_correctly_set[opts7-True-False]`、`tests/test_options.py::test_flag_value_is_correctly_set[opts9-True-True]`。同时应在 `CHANGES.rst` 补充变更说明，且不得破坏原有 `is_flag` 与 `type` 的正常组合行为。