# 修复 `Style.clear_meta_and_links` 未清除缓存哈希的问题

在 rich 库的 `rich/style.py` 中，`Style` 类表示终端文本样式。`Style` 实例的哈希值依赖于其内部属性 `_meta` 和 `_link`。当调用方法 `Style.clear_meta_and_links` 清除链接与元数据时，`_meta` 和 `_link` 会被清空；但当前实现没有清除实例已缓存的哈希（cached hash），导致之后再次获取该实例的哈希时仍返回清除前的旧值，出现状态与哈希不一致的问题。

请修复该缺陷，使 `Style.clear_meta_and_links` 在清除 `_meta` 和 `_link` 的同时，也让缓存的哈希（cached hash）失效并被清除，从而在后续需要时重新计算哈希。

行为级验收标准：
- 对已设置 `_meta` 和/或 `_link` 的 `Style` 实例调用 `Style.clear_meta_and_links` 后，`_meta` 与 `_link` 被清空，且不再复用清除前的缓存哈希（cached hash）。
- 清除后再次计算该实例的哈希（如通过 `hash(style)`），结果应与一个从未设置 `_meta` 和 `_link`、其他样式属性均相同的 `Style` 实例的哈希一致，而不是清除前的哈希值。
- `Style.clear_meta_and_links` 对 `_meta` 和 `_link` 的原有清除行为保持不变，其他样式属性的哈希计算不受影响。
- 代码改动位于 `rich/style.py`；按仓库惯例可在 `CHANGELOG.md` 中记录该修复。相关测试位于 `tests/test_style.py`，其中 `test_clear_meta_and_links_clears_hash` 应通过。