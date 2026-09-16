# Revisiting stderr flush in CLIRunner

## 项目上下文
pallets/click（Python 项目），涉及模块：CHANGES.rst, src, tests。

## 问题描述
This bug is described in detail at  and   I've read through those issues and am not convinced the current behavior is accurate or beneficial.

From: 

> This isn't a bug. When using print in general, you have to flush to be sure all output is sent to stderr. That's one of the reasons Click provides echo instead.

From: 

> Another way to put it is: you need to explain why your suggested behavior is correct. It's certainly different than current, but that doesn't mean it's more correct.

> What I know is that stdout is flushed, and stderr isn't. I don't know why that's the case, but I do know that this is the behavior I've encountered all over the place, and if I want stderr to show up at a specific time I need to flush manually. This is what click.echo does automatically. If what I know and click's test runner's current behavior is incorrect, then you need to show me sources that explain why. Otherwise, it would just mean we're hiding the actual behavior of the calls you're making.

I believe the current behavior of not flushing stderr is wrong because it results in semantics during testing that aren't present during a normal run of the command.  Take:

```python
import sys

import click
from click.testing import CliRunner


.command()
def cli():
    print("to stdout")
    print("to stderr", file=sys.stderr)


def test_cli():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, (), catch_exceptions=False)

    assert result.stdout.strip() == "to stdout"
    assert result.stderr.strip() == "to stderr"


if __name__ == "__main__":
    cli()
```


If you run this through a normal Python execution, you will __always__ get "to stdout" and "to stderr" on the console.  If there were times when "to stderr" were not printed to the console, it would be a bug in Python.  If I don't care when the output comes through, only that it shows up by the time the process has exited, then I don't need to take any extra steps.


## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：b7cf06970e40。