# 修复 Click 在 shell completion 期间未关闭 file option 的问题

在 Click 项目中，若命令通过如下方式定义文件选项：

```python
.group()
.option('--config_file',
              default=CONFIG,
              type=click.File(mode='r'),
              help='help')
.pass_context
def cli(ctx, config_file: typing.TextIO):
```

则在触发 shell completion 时，由 `click.File(mode='r')` 打开的文件不会被关闭，产生资源警告。原始报错为：

```
/Users/grzesiek/Library/Caches/pypoetry/virtualenvs/findata-fetcher-3hK6JJJX-py3.12/lib/python3.12/site-packages/click/shell_completion.py:293: ResourceWarning: unclosed file <_io.TextIOWrapper name='/Users/grzesiek/.config/findata/fetcher.json' mode='r' encoding='UTF-8'>
  completions = self.get_completions(args, incomplete)
```

相关调用链为：`sys.exit(main())` 触发 `main()`，其中执行 `cli(obj={})`，进入 `core.py` 的 `__call__` 并执行 `return self.main(*args, **kwargs)`；随后 `main` 调用 `self._main_shell_completion(extra, prog_name, complete_var)`，`_main_shell_completion` 调用 `rv = shell_complete(self, ctx_args, prog_name, complete_var,`，最终在 `shell_completion.py` 的 `shell_complete` 中执行 `echo(comp`。在此过程中文件选项被打开但未释放。

请修改 `src/click/core.py`、`src/click/shell_completion.py`（必要时更新 `CHANGES.rst`），使 shell completion 流程中由 `click.File` 打开的文件被正确关闭，同时保持补全逻辑不变。

行为级验收标准：
1. 对带 `type=click.File(mode='r')` 选项的命令执行 shell completion 时，不再出现上述 `ResourceWarning: unclosed file <_io.TextIOWrapper name='/Users/grzesiek/.config/findata/fetcher.json' mode='r' encoding='UTF-8'>` 警告，文件被关闭且资源释放。
2. `self.get_completions(args, incomplete)` 与 `shell_complete` 仍能返回正确的补全结果，输出行为无回归。
3. 测试 `tests/test_shell_completion.py::test_files_closed` 通过。