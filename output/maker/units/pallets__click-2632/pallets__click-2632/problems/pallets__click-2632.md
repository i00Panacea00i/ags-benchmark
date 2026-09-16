# Flag option with secondary opts: show_default=True does not show value from default_map in "help" output

## 项目上下文
pallets/click（Python 项目），涉及模块：CHANGES.rst, src, tests。

## 问题描述
I'm setting the `default_map` from a config file, and it seems the values from the `default_map` are not correctly shown in the `--help` output if I set `show_default=True` on my option.

My Option looks like this:

```python
.option(
    "--long/--short",
    "-l/-s",
    is_flag=True,
    show_default=True,
    help="show additional information like size and creation date",
)
```

I initialize the `default_map` with a custom command class that I attach via the `.command` decorator like this `.command(cls=ConfigAwareCommand)`

```python
from click import Command as _Command


class ConfigAwareCommand(_Command):
    def __init__(self, *args, **kwargs):
        kwargs["context_settings"] = {
            "default_map": CONFIG.get_cli_command_defaults(kwargs["name"])
        }
        super().__init__(*args, **kwargs)

```

The `default_map` value is in my example `{'long': True}`. In the `--help` output, the default value is shown like this

```
  -l, --long / -s, --short        show additional information like size and
                                  creation date  [default: short]
```

When executing the command, the default value from the `default_map` is used correctly (`long` defaults to `True`).

During debugging, I might have found the culprit inside [src/click/core.py](

```python
            elif self.is_bool_flag and self.secondary_opts:
                # For boolean flags that have distinct True/False opts,
                # use the opt without prefix instead of the value.
                default_string = _split_opt(
                    (self.opts if self.default else self.secondary_opts)[0]
                )[1]
```

As you can see, `self.default` is used instead of the `default_value` variable that is initialized [further above]( this code snippet.

If I change the part of the code above and use `default_value` instead of `self.default` the help output shows the correct default values from the `default_m

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：5b1624bf0994。