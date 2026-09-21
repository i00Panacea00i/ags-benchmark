# zsh completion still misbehaving in the presence of `:`

<!--
This issue tracker is a tool to address bugs in Click itself. Please use
Pallets Discord or Stack Overflow for questions about your own code.

Replace this comment with a clear outline of what the bug is.
-->

<!--
Describe how to replicate the bug.

Include a minimal reproducible example that demonstrates the bug.
Include the full traceback if there was an exception.
-->

Given `foo` containing:

```python
#!/usr/bin/env python3
from click.shell_completion import CompletionItem
import click

class Foo(click.ParamType):
    def convert(self, value, param, ctx):
        return value

    def shell_complete(self, ctx, param, incomplete):
        return [
            CompletionItem(value=value, help="adsf") for value in 
            ["baz:quux", "spam:eggs"]
        ]

.command()
.argument("foo", type=Foo())
def main(foo):
    print(foo)
```

and running shell completion generation, followed by attempting to complete the command (indicated via `<Tab>`, produces:

```
⊙  PATH=$PWD:/Users/Julian/.local/share/virtualenvs/bowtie/bin/:$PATH
⊙  eval "$(_FOO_COMPLETE=zsh_source ./foo)"                                                                                                                                                                                                                                                                         
⊙  foo <Tab>
baz   -- quux:adsf
spam  -- eggs:adsf
```

rather than the expected:

```
baz:quux   -- adsf
spam:eggs -- adsf
```

<!--
Describe the expected behavior that should have happened but didn't.
-->

This seems to be a regression on #1812.

The fix mentioned there (of "fake escaping" the colons via `.replace(":", "\\:")` seems to work.

Environment:

- Python version:

```
⊙  python --version                                                                                                                                                                       