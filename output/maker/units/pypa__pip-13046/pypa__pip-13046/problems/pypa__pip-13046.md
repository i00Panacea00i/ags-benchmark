# 修复 pip 误报 requirements 文件递归引用

在 pip 24.3（Python 3.9、Linux）中，requirements 文件的包含检测存在误判。存在以下文件：

```
# requirements.txt
...
```
```
# test-requirements.txt
-r requirements.txt
...
```
```
# lint-requirements.txt
-r requirements.txt
-r test-requirements.txt
...
```

执行 `pip install -r lint-requirements.txt` 或 `python3.9 -m pip install -r lint-requirements.txt -c constraints.txt` 时，pip 错误输出：

```
ERROR: .../requirements.txt recursively references itself in .../test-requirements.txt and again in .../lint-requirements.txt
```

以及：

```
ERROR: <omitted>/requirements.txt recursively references itself in <omitted>/test-requirements.txt and again in <omitted>/lint-requirements.txt
```

实际上 `requirements.txt` 仅被 `lint-requirements.txt` 和 `test-requirements.txt` 通过 `-r` 重复引用，没有直接或间接自引用；该用法在 pip 24.3 之前正常。

请在 `src/pip/_internal/req/req_file.py` 中修正递归检测：同一文件被多个父文件重复包含不应视为递归，只有真实循环引用才报错。可更新 `news/13046.bugfix.rst`。

验收标准：
- 上述三个文件下，`pip install -r lint-requirements.txt` 不再输出上述 `ERROR: ... recursively references itself ...` 消息，安装继续。
- 真实递归仍报错，且消息格式不变。
- `tests/unit/test_req_file.py::TestProcessLine::test_repeated_requirement_files` 通过。