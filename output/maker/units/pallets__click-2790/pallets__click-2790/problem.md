# Nested command option shadowing `-h` prints wrong suggestion

## 项目上下文
pallets/click（Python 项目），涉及模块：CHANGES.rst, src, tests。

## 问题描述
<!--
This issue tracker is a tool to address bugs in Click itself. Please use
GitHub Discussions or the Pallets Discord for questions about your own code.

Replace this comment with a clear outline of what the bug is.
-->

Click prints an incorrect suggestion when using a combination of nested command and required argument. This happens when the nested command shadows the `-h` option shortcut of the main command which Click apparently tolerates.

<!--
Describe how to replicate the bug.

Include a minimal reproducible example that demonstrates the bug.
Include the full traceback if there was an exception.
-->

## Replication

See 

```shell-session
$ click-test-cli foo
Usage: click-test-cli foo [OPTIONS] REQUIRED_ARG
Try 'click-test-cli foo -h' for help.

Error: Missing argument 'REQUIRED_ARG'.
```

But, actually running the suggested `click-test-cli foo -h` prints

```shell-session
$ click-test-cli foo -h
Error: Option '-h' requires an argument.
```

Interestingly, Click correctly detects the shadowing of the option when printing the foo command help and prints a consistent help page.

```shell-session
$ click-test-cli foo --help
Usage: click-test-cli foo [OPTIONS] REQUIRED_ARG

Options:
  -h, --host TEXT
  --help           Show this message and exit.
```

### Python code

```py
.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    pass

.command()
.argument("required_arg")
.option("--host", "-h", "host", default="localhost")
def foo(required_arg, host):
    click.echo(f"Foo command required_arg={required_arg} host={host}")

cli.add_command(foo)
```

<!--
Describe the expected behavior that should have happened but didn't.
-->

## Possible solutions

Fix the generated message, so it prints `Try 'click-test-cli foo --help' for help.` in this case.

Environment:

- Python version: 3.12.6
- Click version: 8.2.0.dev0 d73083e

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：8d3449517a97。