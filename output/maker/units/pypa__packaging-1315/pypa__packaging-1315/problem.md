# 修复 `str(Marker(...))` 丢失嵌套分组括号的问题

在 `src/packaging/markers.py` 中，`Marker` 的字符串序列化存在缺陷：当带括号的子分组嵌套在更大的 `and`/`or` 表达式中时，`str(Marker(...))` 会丢弃子分组括号，使重新解析后的优先级改变，甚至翻转求值结果。

例如，令 `m = Marker('python_version < "3.10" and ((sys_platform == "linux" or sys_platform == "darwin"))')`，`env = {"python_version": "3.12", "sys_platform": "darwin"}`。当前 `str(m)` 返回 `python_version < "3.10" and sys_platform == "linux" or sys_platform == "darwin"`；`m.evaluate(env)` 为 `False`，而 `Marker(str(m)).evaluate(env)` 为 `True`。原语义是 `A and (B or C)`，重新解析后变成 `(A and B) or C`。

验收标准：修复后，`str(Marker(x))` 必须保留必要括号，使 `Marker(str(Marker(x))).evaluate(env)` 对任意 `env` 和任意标记字符串 `x` 都与 `Marker(x).evaluate(env)` 一致。上例中 `Marker(str(m)).evaluate(env)` 必须为 `False`，且 `str(m)` 应保留 `((sys_platform == "linux" or sys_platform == "darwin"))` 的括号。修改需让 `tests/test_markers.py::test_str_preserves_nested_group_precedence` 通过，且不破坏 `src/packaging/markers.py` 的既有行为。