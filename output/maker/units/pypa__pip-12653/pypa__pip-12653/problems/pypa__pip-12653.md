# Recursive loops in requirements files not detected

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
### Description

If a requirements file references itself (directly or indirectly), an RecursionError is raised. 

### Expected behavior

The RecursionError isn't strictly *wrong*, but the cause of the error may not be obvious as it results in a hard interpreter crash. It would be desirable to detect the recursion, and report the source of the problem rather than crashing the Python interpreter.

### pip version

24.0

### Python version

3.10 (but should affect any version)

### OS

macOS (but should affect any OS)

### How to Reproduce

1. Construct a `requirements.txt` that contains:
```
-r requirements.txt
```
2. Run `pip install -r requirements.txt`

This is the simplest case; other loops (such as requirements files that include each other, and cycles of 3 or more requirements files) also cause the problem.

### Output

```shell
ERROR: Exception:
Traceback (most recent call last):
  File "/Users/rkm/beeware/toga/venv3.10/lib/python3.10/site-packages/pip/_internal/cli/base_command.py", line 180, in exc_logging_wrapper
    status = run_func(*args)
  File "/Users/rkm/beeware/toga/venv3.10/lib/python3.10/site-packages/pip/_internal/cli/req_command.py", line 245, in wrapper
    return func(self, options, args)
  File "/Users/rkm/beeware/toga/venv3.10/lib/python3.10/site-packages/pip/_internal/commands/install.py", line 342, in run
    reqs = self.get_requirements(args, options, finder, session)
  File "/Users/rkm/beeware/toga/venv3.10/lib/python3.10/site-packages/pip/_internal/cli/req_command.py", line 433, in get_requirements
    for parsed_req in parse_requirements(
  File "/Users/rkm/beeware/toga/venv3.10/lib/python3.10/site-packages/pip/_internal/req/req_file.py", line 156, in parse_requirements
    for parsed_line in parser.parse(filename, constraint):
  File "/Users/rkm/beeware/toga/venv3.10/lib/python3.10/site-packages/pip/_internal/req/req_file.py", line 337, in parse
    yield from self._parse_and_recurse(filename, constraint)
  File "/

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：c33c1881a4cf。