# 为 packaging.tags 提供仅获取纯 Python 标签的接口

在 `packaging.tags` 模块中，现有的 `packaging.tags.compatible_tags()` 没有提供忽略 `platform` 参数的方式，因此调用者无法只获取 `py*-none-any` 形式的纯 Python 标签。需要新增一个接口（例如 `pure_python_tags()` 或 `python_only_tags()`，或类似命名）来专门返回纯 Python 标签。

请在 `src/packaging/tags.py` 中实现该接口，并在 `docs/tags.rst` 中补充使用文档。

行为级验收标准：

- 新接口必须只产出 `py*-none-any` 标签，不产出任何与平台绑定的标签；调用过程中不应查询或依赖 `platform` 参数所涉及的平台信息。
- 针对 Python 版本参数的不同情况，接口都应正确生成对应标签：包括默认 Python 版本、空 Python 版本、仅包含主版本号的 Python 版本，以及完整的 Python 版本。
- 当 `tests/test_tags.py` 中 `TestPurePythonTags` 的 `test_default_python_version`、`test_does_not_query_platforms`、`test_empty_python_version`、`test_major_only_python_version`、`test_python_version` 全部通过时，即视为修复完成。