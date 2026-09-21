# `@click.Option` with `'hide_input' = True` (used for password) and custom `type` parameter doesn't show custom error message

## 项目上下文
pallets/click（Python 项目），涉及模块：CHANGES.rst, src, tests。

## 问题描述
I use .Option with 'hide_input' = True and custom 'type' parameter for password prompt with raise click.BadParameter (it inheriths class UsageError). And if the password failed the code doesn't show custom error message, but standard message "Error: The value you entered was invalid"

Standard message comes from termui.py file: ~172 line - 
```python
        except UsageError as e:
            if hide_input:
                echo(_("Error: The value you entered was invalid."), err=err)
            else:
                echo(_("Error: {e.message}").format(e=e), err=err)  # noqa: B306
            continue
```
Because it checks hide_input parameter and if it True (and it is really True as i hide_input because of the password) it give the error "Error: The value you entered was invalid". When hide_input is False - it gives me my custom message.

If i use click.ClickException exception class it give me my error, but stops the promt, so i have to start from the beginning.
If i make hide_input = False - the password is visible on the screen and i recieve my custom message. But it is wrong for password entry.

Here is the example how to replicate my error. 
Run the code and enter "1234".
The message i expect "Error: Your password is week. Use 'Minimum eight characters, at least one letter and one number"

```python
import click
import re

class PassRequirement(click.ParamType):
    """Click check class for password"""

    name = "Password requirements"

    def convert(self, value, param, ctx):
        pw_req = "Minimum eight characters, at least one letter and one number"
        pw_strength = r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$"

        if re.match(pw_strength, value):
            return value

        self.fail(f"Your password is week. Use {pw_req!r}", param, ctx)

    def fail(self, message="", param=None, ctx=None):
        raise click.BadParameter(message, ctx, param)
        # raise click.ClickException(message) - # works well, shows my message, but stops the p

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：fc6c7c47edd6。