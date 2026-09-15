# `lookup_default` 返回 `Sentinel.UNSET` 而非 `None`

在 click 8.3.0 或 8.3.1 中，`Context.lookup_default` 方法出现回归：当参数名在默认映射中无对应值时，该方法返回 `Sentinel.UNSET` 而非预期的 `None`。这一变化导致继承 `click.Context` 并重写 `lookup_default` 的子类（如示例中的 `CustomClickContext`）行为异常——子类中调用 `super().lookup_default(name, call=False)` 本来期望得到 `None` 以便执行自定义回退逻辑，但现在收到 `Sentinel.UNSET`，从而错误地将其视为有效默认值返回。

## 具体表现

以下场景可复现该回归：
- 设置 `default_map = {"app": {"email": "prefix-param-level.com"}}`。
- 创建 `click.Command("get-views")` 实例，并用 `CustomClickContext(cmd, info_name=None)` 构造上下文。
- 将 `ctx.default_map` 赋值为上述映射。
- 调用 `ctx.lookup_default("email", False)`。

在 8.2.1 及之前版本中，`super().lookup_default` 返回 `None`，子类随后检查 `default_map` 中 `"email"` 对应的键（通过 `prefix = name.split("_", 1)[0]` 得到 `"email"`），但 `"email"` 并不存在于 `default_map` 顶层键中，因此最终返回 `None`。而在 8.3.0+ 版本中，`super().lookup_default` 直接返回 `Sentinel.UNSET`，子类中 `if default is not None` 条件成立，直接返回该 `Sentinel.UNSET` 对象，导致调用方得到非 `None` 值。

该 `Sentinel.UNSET` 对象的类型为内部哨兵类，通过 `describe(val)` 可观察到其属性：`__class__`, `__module__`, `__qualname__`、`cls.__module__`, `cls.__qualname__`、`has_name_attr`（`False`）、`name_attr` 等。

## 验收标准

修复后，应满足以下行为级条件：
1. 当 `ctx.lookup_default("email", False)` 被调用，且 `ctx.default_map` 中不存在对应值时，返回值必须为 `None`，而非 `Sentinel.UNSET`。
2. 使用 `importlib.metadata`（即 `importlib.metadata.version('click')`）确认版本为 8.3.1 时，上述断言不再失败。
3. 仓库中已有的测试用例 `tests/test_defaults.py::test_unset_in_default_map` 应通过，以验证默认映射中未设置项的行为正确。