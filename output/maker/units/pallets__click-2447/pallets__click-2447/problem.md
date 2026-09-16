# Exception information isn't passed through to context.with_resource managed resources

## 项目上下文
pallets/click（Python 项目），涉及模块：CHANGES.rst, src, tests。

## 问题描述
When writing a simple tool with a bunch of commands updating a database, I was using a context manager in each command that would begin a transaction, and then commit it on success, or rollback on error.

Initially, I thought I'd be able to avoid some boilerplate on every subcommand by adding the session as a managed resource via ctx.with_resource(context_manager).  However, while this works in the success case, it will also commit the transaction if an unexpected exception occurs, since the exception information doesn't seem to be being passed through to the context manager.

Eg. given the below context manager:

    class TestContextManager:
        def __enter__(self):
            print("ENTER")

        def __exit__(self, exc_type, exc_val, traceback):
            print("EXIT", exc_type, exc_val, traceback)

Using it in a regular context manager via:

    with TestContextManager():
        raise Exception()

will correctly print the exc_type, exc_val and traceback parameters when an exception occurs.  But using it via:

    .group()
    .pass_context
    def cli(ctx):
        ctx.obj = ctx.with_resource(TestContextManager())

These will always be `None`, and so any context manager that needs to act differently on the occurrence of an exception vs success will always treat this as success.  (And likewise, try/except blocks will never trigger in function-style ones using the `` decorator.)

Would it be possible for the exception information to be passed through to managed resources so that context managers that treat success/failure cases differently operate correctly?

Environment:

- Python version: 3.10.9
- Click version: 8.1.3

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：16fe802a3f96。