# Click 8.2.0 ignores is_flag options that have a type

Click 8.2.0 ignores the use of options defined with `is_flag` and `type=str`.

Of course, combining `is_flag` and `type=str` does not make sense, but it happened in one of our projects. Click before 8.2.0 ignored `type=str` and processed this as expected for `is_flag`.

Click 8.2.0 does not set a value for such an option.

I could trace this change to PR #2829 - If I install click 8.2.0 and manually undo the change in `core.py` that is done by that PR, it works as before.

To reproduce:

1. Have a file `main.py` with:

```
import click

.group(invoke_without_command=True)
.option('-x', '--transpose', type=str, is_flag=True,
              help='Transpose the output table.')
def cli(transpose):
    print(f"Debug: transpose={transpose}")
    return 0
```

2. Reproduce with click 8.2.0:
```
$ pip install click==8.2.0
$ python -c "import main,sys; sys.argv=['cli', '--transpose']; main.cli()"
Debug: transpose=None
```

3. Verify that click 8.2.0 with PR #2829 undone works:
```
# perform the undo in core.py (see below)
$ python -c "import main,sys; sys.argv=['cli', '--transpose']; main.cli()"
Debug: transpose=True
```

4. Verify that click 8.1.8 works:
```
$ pip install click==8.1.8
$ python -c "import main,sys; sys.argv=['cli', '--transpose']; main.cli()"
Debug: transpose=True
```

The "undo" of PR #2829 has the following changes in `core.py`, starting at line 2613:
```
        # Undo PR 2829: Added the following two lines
        if flag_value is None:
            flag_value = not self.default
        self.type: types.ParamType
        if is_flag and type is None:
            # Undo PR 2829: Removed the following two lines
            # if flag_value is None:
            #     flag_value = not self.default
            # Re-guess the type from the flag value instead of the
            # default.
            self.type = types.convert_type(None, flag_value)
```

Environment:

- Python version: 3.12.7 on macOS (it happens on all Python versions supported by click 8.2.0, but 