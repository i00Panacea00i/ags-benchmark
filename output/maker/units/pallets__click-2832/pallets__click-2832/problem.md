# 任务：修复 Click 8.1.8 中自定义帮助选项子类化失效的回归问题

## 问题描述
在 Click 库版本 8.18（对应 8.1.8）中，当通过 `help_option` 装饰器传入自定义的 `Option` 子类作为 `cls` 参数时，帮助选项无法正常工作。该问题在 Click 8.1.7 及之前版本中不存在。

## 可复现代码示例

### 正常情况（8.1.7 和 8.1.8 均正常工作，不使用自定义类）
`works.py`：
```python
import click

@click.command()
@click.help_option("-h", "--help")
def scancode():
    """OK in pkg:pypi/click.1.7 and pkg:pypi/click.1.8"""
    pass

if __name__ == "__main__":
    scancode()
```
运行 `python works.py --help` 应输出：
```
Usage: works.py [OPTIONS]

  OK in pkg:pypi/click.1.7 and pkg:pypi/click.1.8

Options:
  -h, --help  Show this message and exit.
```

### 失败情况（8.1.8 中出错，8.1.7 正常）
`failing.py`：
```python
import click

class PluggableCommandLineOption(click.Option):
    pass

@click.command()
@click.help_option("-h", "--help", cls=PluggableCommandLineOption)
def scancode():
    """Regression in pkg:pypi/click.1.8"""
    pass

if __name__ == "__main__":
    scancode()
```
在 8.1.7 中运行 `python failing.py -h` 或 `python failing.py --help` 应正常显示帮助信息。  
在 8.1.8 中运行上述命令会输出错误：
```
Error: Option '-h' requires an argument.
Error: Option '--help' requires an argument.
```

### 仅提供短选项（8.1.7 和 8.1.8 均部分正常）
`works2.py`：
```python
import click

class PluggableCommandLineOption(click.Option):
    pass

@click.command()
@click.help_option("-h", cls=PluggableCommandLineOption)
def scancode():
    """Regression in pkg:pypi/click.1.8"""
    pass

if __name__ == "__main__":
    scancode()
```
运行 `python works2.py -h` 应正常显示帮助，无需参数。

## 验收标准
1. 修复后，在 Click 8.18 中，`failing.py` 运行 `-h` 或 `--help` 均应输出正确的帮助信息，不再出现“requires an argument”错误。
2. `works.py` 和 `works2.py` 的行为不受影响，保持原有正确输出。
3. 所有涉及 `help_option` 使用自定义 `cls` 子类的场景（包括同时指定短、长选项，或仅指定短选项）均应正确解析并显示帮助，而不是要求额外参数。