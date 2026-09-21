# 修复 `multiple=True` 标志选项触发 `TypeError`

在 Click 命令行库中，为命令定义同时带有 `is_flag=True` 和 `multiple=True` 的选项时，若运行命令且未提供该标志，会在 `Parameter.consume_value()` 中因默认值不合适而触发 `TypeError`。

复现代码（保存为 `foo.py`）：
```py
import click

@click.command()
@click.option("-v", is_flag=True, multiple=True)
def main(v):
    click.echo(v)

if __name__ == "__main__":
    main()
```
在 `python3.9` 环境下运行 `python foo.py`（未加 `-v`）会抛出如下异常：
```
Traceback (most recent call last):
  File "/Users/jreese/scratch/foo.py", line 25, in <module>
    main()
  File "/Users/jreese/scratch/venv39/lib/python3.9/site-packages/click/core.py", line 1130, in __call__
    return self.main(*args, **kwargs)
  File "/Users/jreese/scratch/venv39/lib/python3.9/site-packages/click/core.py", line 1054, in main
    with self.make_context(prog_name, args, **extra) as ctx:
  File "/Users/jreese/scratch/venv39/lib/python3.9/site-packages/click/core.py", line 920, in make_context
    self.parse_args(ctx, args)
  File "/Users/jreese/scratch/venv39/lib/python3.9/site-packages/click/core.py", line 1378, in parse_args
    value, args = param.handle_parse_result(ctx, opts, args)
  File "/Users/jreese/scratch/venv39/lib/python3.9/site-packages/click/core.py", line 2356, in handle_parse_result
    value, source = self.consume_value(ctx, opts)
  File "/Users/jreese/scratch/venv39/lib/python3.9/site-packages/click/core.py", line 2903, in consume_value
    and any(v is _flag_needs_value for v in value)
TypeError: 'bool' object is not iterable
```
手动指定 `default=()` 可规避该错误，但在 7.x 中无需设置默认值即可正常工作。该问题在 Python 3.8.6 与 3.9.3 上可复现；Click 7.1.2 正常，而 8.0.4 与 8.1.2 会报错。

验收标准：修复后，上述 `foo.py` 在未传递 `-v` 时应正常结束，不抛出 `TypeError: 'bool' object is not iterable`，且 `v` 的默认值行为与 7.1.2 一致（无需用户手动设置 `default=()`）；传递一次或多次 `-v` 时，`v` 应为对应的布尔元组并正常通过 `click.echo(v)` 输出。在 Python 3.8.6、3.9.3 以及 Click 8.0.4、8.1.2 环境下均不应再触发该异常。