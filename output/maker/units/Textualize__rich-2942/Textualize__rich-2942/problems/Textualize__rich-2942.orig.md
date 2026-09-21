# [BUG] Style.clear_meta_and_links should reset hash

The hash of a `Style` instance depends on `_meta` and `_link`:



So, when the link and meta are cleared with the method `Style.clear_meta_and_links`, the cached hash should be cleared: