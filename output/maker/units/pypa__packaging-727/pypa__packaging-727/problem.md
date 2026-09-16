# 支持 `--disable-gil` 构建（PEP 703）的标签生成

## 任务描述

在 `packaging.tags` 模块中，需要添加对 Python 解释器使用 `--disable-gil`（PEP 703）编译的实验性构建的支持。当前该模块生成的标签未考虑禁用全局解释器锁的变体，导致生成的 ABI 标签和标签序列不正确。具体需要修改以下两个函数的行为：

### 1. `packaging.tags._cpython_abis()` 函数

该函数当前返回 CPython 的 ABI 标签列表。对于启用了 `--disable-gil` 的构建，CPython 会在 ABI 字符串中附加字符 `"t"`（例如 `"cp312t"`）。因此，函数需要检测当前解释器是否使用了 `--disable-gil` 编译（可通过 `sys.abiflags` 或 `sysconfig` 等机制判断），如果检测到，则应在原有的 ABI 标签中加入 `"t"`。例如，对于 Python 3.12 的 `--disable-gil` 构建，对应的 ABI 应为 `"cp312t"`，而非 `"cp312"`。

### 2. `packaging.tags.cpython_tags()` 函数

该函数生成 CPython 的标签序列，其中包含 `"abi3"` 作为稳定的 ABI 标签。然而，在 `--disable-gil` 构建中，稳定 ABI（即 `abi3`）不适用（因为稳定 ABI 尚未支持自由线程模式），因此需要从生成的标签序列中**排除** `"abi3"` 标签。当前该函数会在内部调用 `_cpython_abis()` 并可能添加 `"abi3"`，需要确保当解释器为 `--disable-gil` 构建时，`"abi3"` 不会出现在最终输出的标签列表中。

## 验收标准

- 在 `--disable-gil` 构建的 CPython 解释器上，调用 `packaging.tags.sys_tags()` 生成的标签中，应包含形如 `"cp312t"` 的 ABI 标签（版本号与实际一致），且**不应**包含 `"abi3"` 标签。
- 在常规（非 `--disable-gil`）的 CPython 解释器上，原有行为完全不变：生成的标签中不包含 `"t"`，且 `"abi3"` 正常出现。
- 修改后需确保 `tags` 模块的所有已有文档字符串和公共接口签名不变（返回值类型仍为 `Iterator[Tag]` 或 `List[str]`）。
- 仅修改 `src/packaging/tags.py` 文件中的上述两个函数，无需修改其他文件或添加新测试。