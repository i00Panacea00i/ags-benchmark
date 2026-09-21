# Flags with `multiple=True` trigger `TypeError`

Adding an option with `is_flag=True` and `multiple=True` will trigger a `TypeError` in `Parameter.consume_value()` due to bad default value.

```py
import click

.command()
.option("-v", is_flag=True, multiple=True)
def main(v):
    click.echo(v)

if __name__ == "__main__":
    main()
```

When run without the flag, a TypeError is raised:

```
(venv39) jreese ~/scratch » python foo.py
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

Manually setting a better default value, like `default=()`, avoids the type error, but this used to work on 7.x without setting the default value.

Environment:

- Python version: tested on 3.8.6 and 3.9.3
- Click version: worked on 7.1.2; errors on 8.0.4 and 8.1.2