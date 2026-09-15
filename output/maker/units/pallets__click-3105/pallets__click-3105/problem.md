# 修复 `FuncParamType` 中 `ValueError` 消息传递逻辑

## 问题描述

在 `click` 库的 `FuncParamType` 类（位于 `src/click/types.py`）中，当 `self.func(value)` 抛出 `ValueError` 时，当前实现直接调用 `self.fail(value, ...)`，将原始输入值作为失败信息传递给用户。这丢失了 `ValueError` 中携带的具体错误说明（例如 `"input was  input=..., should be works"`），导致用户收到的错误消息缺乏语义，无法定位问题。

期望的行为是：当 `self.func(value)` 抛出 `ValueError` 时，应该捕获该异常，将异常的消息字符串（通过 `str(e)`）传递给 `self.fail(message, param, ctx)`，从而向用户展示有意义的错误描述，而非原始输入值。

## 涉及的关键标识符

- `FuncParamType` 类，继承自 `ParamType`
- `__init__(self, func: t.Callable[[t.Any], t.Any])` 方法，将 `self.name` 设为 `func.__name__`
- `to_info_dict(self)` 方法，返回包含键 `"func"` 的字典
- `convert(self, value, param, ctx)` 方法，其中应处理 `ValueError`
- `self.fail(message, param, ctx)` 方法（来自父类）
- 异常类型 `ValueError`
- 类型别名：`t.Any`，`t.Callable`
- 使用场景：`typer.Argument(parser=MyClass.from_str)` 中的自定义解析器

## 验收标准

1. 当 `self.func(value)` 抛出 `ValueError` 时，`convert` 方法必须调用 `self.fail(str(e), param, ctx)`，其中 `e` 是捕获到的异常实例。
2. 用户看到的错误消息应为异常中的字符串内容（例如 `"input was  input=..., should be works"`），而非原始输入值 `value`。
3. 其他正常路径（`self.func` 不抛出异常）的行为保持不变。
4. 现有测试 `tests/test_types.py::test_func_param_type_uses_value_error_message` 在修复后应通过。