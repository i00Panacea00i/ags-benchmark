# 修复 `flag_value` 与 `envvar` 同时使用时选项值错误的问题

在 Click 中，使用 `@click.command()` 和 `@click.option()` 定义选项时，若同时指定 `is_flag=True`、`flag_value=logging.DEBUG` 与 `envvar='DEBUG'`，通过命令行参数 `--debug` 调用时，`debug` 参数能正确获得 `flag_value` 指定的 `logging.DEBUG`。但通过环境变量 `DEBUG` 调用时，`debug` 参数却直接取到了环境变量中的原始值：例如 `DEBUG=8` 时输出 `8`，`DEBUG=1` 时输出 `1`，而不是 `logging.DEBUG`；未设置环境变量时也未回退为 `None`。

复现逻辑如下：

```python
import logging
import os
import sys

import click

@click.command()
@click.option('--debug', is_flag=True, flag_value=logging.DEBUG, envvar='DEBUG')
def sample(debug):
    click.echo(f"DEBUG: {debug}")
    assert debug in [logging.DEBUG, None], f"Invalid debug value: {debug} - expected >{logging.DEBUG}< or None"

if __name__ == '__main__':
    sample()
```

设置 `os.environ['DEBUG'] = '1'` 或运行 `DEBUG=8 python cli.py` 时，程序输出原始值并触发断言 `assert debug in [logging.DEBUG, None]`，报错消息为 `f"Invalid debug value: {debug} - expected >{logging.DEBUG}< or None"`。而 `sys.argv = ['', '--debug']` 时行为正常。

需要修复选项解析逻辑，使 `envvar` 与 `flag_value` 正确协同：环境变量存在且为真时，选项值应为 `flag_value`（即 `logging.DEBUG`）；环境变量未设置或为空时，应为 `None`；不得将环境变量字符串直接作为整数或原值返回。

行为级验收标准：
1. 使用 `--debug` 参数时，`debug` 为 `logging.DEBUG`。
2. 设置 `DEBUG=1` 或 `DEBUG=8` 时，`debug` 均为 `logging.DEBUG`，而非 `1`、`8` 等原始值。
3. 未设置 `DEBUG` 时，`debug` 为 `None`。
4. 断言 `assert debug in [logging.DEBUG, None]` 不再失败，且 `tests/test_arguments.py::test_envvar_flag_value` 通过。