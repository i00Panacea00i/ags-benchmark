# 任务：修复 Metadata 类中可选字段默认值不一致的问题

在 `pypa/packaging` 仓库的 `src/packaging/metadata.py` 中，`Metadata` 类处理可选元数据字段（即 `metadata._RAW_TO_EMAIL_MAPPING.keys` 与 `metadata._REQUIRED_ATTRS` 的差集中的字段）时存在不一致甚至错误的行为。当通过 `metadata.Metadata.from_raw` 创建一个仅包含必填字段（例如 `metadata_version` 取 `metadata._VALID_METADATA_VERSIONS` 中的最后一个版本，`name` 为 `"foo"`，`version` 为 `"1.0"`）的最小元数据对象后，访问任何一个可选字段（如 `field_name`）应返回对应类型的“零值”：字符串类型返回空字符串 `""`，列表类型返回空列表 `[]`，字典类型返回空字典 `{}`。然而，当前实现中，某些可选字段（例如 `description_content_type`）在访问时会导致错误或返回意外的值，使得测试 `test_can_access_omitted_optional_value` 中的多个参数化用例失败。

该测试位于 `tests/test_metadata.py` 中，使用 `mark.parametrize` 对所有可选字段进行参数化，测试函数签名如下：`TestMetadata.test_can_access_omitted_optional_value`。运行该测试时，会在控制台输出类似下方的失败信息：
```
____________________ TestMetadata.test_can_access_omitted_optional_value[description_content_type] _____________________
```
以及对应的断言错误。具体失败的字段包括但不限于 `description_content_type`，目前已知有 3 个错误。

**验收标准**：
- 修复后，执行 `pytest tests/test_metadata.py::TestMetadata::test_can_access_omitted_optional_value` 时，所有由 `mark.parametrize` 生成的测试用例（包括但不限于 `description_content_type` 等字段）均应全部通过。
- 对于每个可选字段，通过 `getattr(meta, field_name)` 获得的值必须严格等于对应类型的零值（字符串为 `""`，列表为 `[]`，字典为 `{}`），且不抛出任何异常。
- 不得破坏 `tests/test_metadata.py` 中现有的其他测试（如 `test_optional_defaults_to_none` 系列测试，对应路径 `tests.test_metadata.TestMetadata` 中的参数化测试）。