# 目标版本为 Python 3.14 但运行在 Python 3.12 时出现内部错误

在 Black 代码格式化工具中，使用 Python 3.12.11（CPython）运行，并通过 `-t py314` 将目标版本指定为 Python 3.14 时，格式化含 `except` 子句且异常类型带括号的文件会触发 INTERNAL ERROR。

复现方式：安装 Black 26.1.0，准备 `test.py`，内容如下：
```
try:
 1 / 0
except (a, b):
 pass
```
执行 `black -t py314 test.py`，报错如下：
```
error: cannot format test.py: INTERNAL ERROR:
Black 26.1.0 on Python (CPython) 3.12.11 produced invalid code:
multiple exception types must be parenthesized (<unknown>, line 3).
Please report a bug on 
This invalid output might be helpful: /tmp/blk_t6kdrgtk.log

Oh no! 💥 💔 💥
1 file failed to reformat.
```

期望行为：不出现 INTERNAL ERROR；即便目标 Python 版本与运行时版本不同，即便这意味着需要隐含 `--fast`，也不应生成无效代码或崩溃。

涉及文件包括 `src/black/__init__.py`、`CHANGES.md` 与 `tests/test_black.py`；相关测试标识符为 `tests/test_black.py::TestASTSafety::test_target_version_exceeds_runtime_warning`。

验收标准：
1. 在 Python 3.12.11 下运行 `black -t py314 test.py`，不再输出 INTERNAL ERROR，也不出现 `multiple exception types must be parenthesized (<unknown>, line 3).` 或 `1 file failed to reformat.`；Black 应安全处理（成功格式化，或明确提示/警告并跳过），且绝不生成无效代码。
2. 测试 `tests/test_black.py::TestASTSafety::test_target_version_exceeds_runtime_warning` 通过。
3. 同步更新 `CHANGES.md` 中的变更记录。