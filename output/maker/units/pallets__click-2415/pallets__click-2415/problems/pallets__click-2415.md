# Error in click.utils.echo() when console is unavailable

## 项目上下文
pallets/click（Python 项目），涉及模块：CHANGES.rst, src, tests。

## 问题描述
The `click.utils.echo()` function does not seem to account for the case when the console is not available on Windows, i.e., when running under `pythonw.exe` interpreter instead of the `python.exe` one.

Minimal example: 

```python
# program.py
import sys
import os

try:
    import click
    click.utils.echo("Hello world")
except Exception:
    import traceback
    error_file = os.path.join(os.path.dirname(__file__), "error_log.txt")
    with open(error_file, "w") as fp:
        traceback.print_exc(file=fp)
```

Running this program with `pythonw.exe program.py` produces the `error_log.txt`:
``` 
Traceback (most recent call last):
  File "C:\Users\Rok\Development\pyi-click\program.py", line 6, in <module>
    click.utils.echo("Hello world")
  File "C:\Users\Rok\Development\pyi-click\venv\lib\site-packages\click\utils.py", line 299, in echo
    file.write(out)  # type: ignore
AttributeError: 'NoneType' object has no attribute 'write'
```

In contrast, standard `print()` function gracefully handles situations when console is unavailable and `sys.stdout` and `sys.stderr` are `None`.

This attempt at retrieving stdout/stderr:

should be followed by another `None` check, and if the stream is unavailable, the function should become a no-op (exit immediately).

Environment:

- OS: Windows
- Python version: any
- Click version: 8.1.3 (and earlier)

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：9a536eebd958。