# ANSI codes not stripped from click.confirm after upgrading to click 8.4

<!--
This issue tracker is a tool to address bugs in Click itself. Please use
GitHub Discussions or the Pallets Discord for questions about your own code.

Replace this comment with a clear outline of what the bug is.
-->
I had failing unit tests after upgrading to click 8.4.1. I was able to address some 
by using `runner.invoke(cmd, color=False)`, but that didn't help for commands
that use `click.confirm()`

<!--
Describe how to replicate the bug.

Include a minimal reproducible example that demonstrates the bug.
Include the full traceback if there was an exception.
-->

This test script `test_repro.py` replicates the issue.
```
import click
from click.testing import CliRunner

.command()
def cmd():
    click.echo(click.style('Hello World!', fg='green'))

.command()
def cmd_confirm():
    click.confirm(click.style('Hello World!', fg='green'), abort=True)

def test_echo_strips_ansi_with_color_false():
    runner = CliRunner()
    result = runner.invoke(cmd, color=False)
    assert result.output == "Hello World!\n"

def test_confirm_strips_ansi_with_color_false():
    runner = CliRunner()
    result = runner.invoke(cmd_confirm, input="Y", color=False)
    assert result.output == "Hello World! [y/N]: Y\n"  # FAILS: ANSI codes present
```

With click 8.3.3 both tests pass. With click 8.4.0 and 8.4.1, the `test_confirm_strips_ansi_with_color_false` test fails:

```
uvx --with click==8.4 pytest test_repro.py
...
================================================ FAILURES ================================================
_______________________________ test_confirm_strips_ansi_with_color_false ________________________________

    def test_confirm_strips_ansi_with_color_false():
        runner = CliRunner()
        result = runner.invoke(cmd_confirm, input="Y", color=False)
>       assert result.output == "Hello World! [y/N]: Y\n"  # FAILS: ANSI codes present
```

<!--
Describe the expected behavior that should have happened but didn't.
-->
The ansi codes should be stripped 