# 修复 Requirement pickle 丢失 specifier.prereleases 的问题

在 `src/packaging/requirements.py` 中，`Requirement` 对象经过 `pickle` 序列化与反序列化后，其 `specifier.prereleases` 属性会丢失。复现过程如下：

```python
>>> import pickle
>>> from packaging.requirements import Requirement
>>> r = Requirement("foo>=1.0")
>>> r.specifier.prereleases = True
>>> pickle.loads(pickle.dumps(r)).specifier.prereleases is None
True
```

期望行为：将 `pickle.loads(pickle.dumps(r))` 的结果记为 `loaded`，则 `loaded.specifier.prereleases == True`，而不是 `None`。也就是说，`Requirement` 的 `specifier.prereleases` 在 `pickle.dumps` 与 `pickle.loads` 往返后必须保持原值：显式设置为 `True` 时仍为 `True`，显式设置为 `False` 时仍为 `False`，未显式设置时仍为 `None`。

验收标准：
1. 对 `Requirement("foo>=1.0")` 设置 `r.specifier.prereleases = True` 后，反序列化得到的 `loaded` 满足 `loaded.specifier.prereleases == True`；设置为 `False` 时满足 `loaded.specifier.prereleases == False`；未设置时保持 `None`。
2. `tests/test_requirements.py::test_pickle_requirement_new_format_preserves_prereleases`、`tests/test_requirements.py::test_pickle_requirement_preserves_prereleases[False]` 与 `tests/test_requirements.py::test_pickle_requirement_preserves_prereleases[True]` 均通过。
3. `CHANGELOG.rst` 中已补充该修复的变更记录，且 `Requirement` 的常规解析行为与 `specifier` 的其他语义未发生回归。