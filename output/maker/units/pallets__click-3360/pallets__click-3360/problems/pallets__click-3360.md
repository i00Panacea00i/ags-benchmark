# Empty output from `HelpFormatter.write_usage` for a program without arguments

## 项目上下文
pallets/click（Python 项目），涉及模块：CHANGES.rst, src, tests。

## 问题描述
If no `args` are passed to `HelpFormatter.write_usage`, the Usage line is not printed.

### Reproduction

```python
import click

f = click.HelpFormatter()
f.write_usage("program")
print(f.getvalue())
```
<!--
Describe how to replicate the bug.

Include a minimal reproducible example that demonstrates the bug.
Include the full traceback if there was an exception.
-->

### Expected output
```
Usage: program
```

### Actual output
(an empty line)

### Environment

- Python version: 3.12.3
- Click version: 8.3.1

### Additional information

We use `click` for a CLI program with interactive mode. We are about to use `click.HelpFormatter` to print help for internal commands, some of which do not accept any arguments (`exit`, for example).

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：7c99ebe23b93。