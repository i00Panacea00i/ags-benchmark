# `Sentinel` is passed to `type_cast_value`

Starting in version 8.3.0, a `Sentinel` object is passed in to the `type_cast_value` function of the `Parameter` class and its derivatives if no value is supplied.

Reproduction:

```python
# cli_bug.py
import click

class CSVOption(click.Option):
    def type_cast_value(self, ctx, value):
        if value:
            return value.split(",")
        return value

.command(name="run")
.option("--csv", cls=CSVOption)
def main(csv):
    click.echo(f"{csv!r}")

if __name__ == "__main__":
    main()
```

```shell
$ uv run --with 'click==8.3.0' cli_bug.py

Installed 1 package in 1ms
Traceback (most recent call last):
  File "/home/coder/workspace/scratch/click-8_3_0-bug/cli_bug.py", line 17, in <module>
    main()
  File "/home/coder/.cache/uv/archive-v0/9Q5N3REh-YZUOJbO3iHRv/lib/python3.10/site-packages/click/core.py", line 1462, in __call__
    return self.main(*args, **kwargs)
  File "/home/coder/.cache/uv/archive-v0/9Q5N3REh-YZUOJbO3iHRv/lib/python3.10/site-packages/click/core.py", line 1382, in main
    with self.make_context(prog_name, args, **extra) as ctx:
  File "/home/coder/.cache/uv/archive-v0/9Q5N3REh-YZUOJbO3iHRv/lib/python3.10/site-packages/click/core.py", line 1206, in make_context
    self.parse_args(ctx, args)
  File "/home/coder/.cache/uv/archive-v0/9Q5N3REh-YZUOJbO3iHRv/lib/python3.10/site-packages/click/core.py", line 1217, in parse_args
    _, args = param.handle_parse_result(ctx, opts, args)
  File "/home/coder/.cache/uv/archive-v0/9Q5N3REh-YZUOJbO3iHRv/lib/python3.10/site-packages/click/core.py", line 2516, in handle_parse_result
    value = self.process_value(ctx, value)
  File "/home/coder/.cache/uv/archive-v0/9Q5N3REh-YZUOJbO3iHRv/lib/python3.10/site-packages/click/core.py", line 2401, in process_value
    value = self.type_cast_value(ctx, value)
  File "/home/coder/workspace/scratch/click-8_3_0-bug/cli_bug.py", line 7, in type_cast_value
    return value.split(",")
AttributeError: 'Sentinel' object has no attribute 'split'
```

```shell
uv run 