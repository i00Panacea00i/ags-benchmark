# `progressbar(hide=True)` option for hiding the progress bar

## 项目上下文
pallets/click（Python 项目），涉及模块：.gitignore, CHANGES.rst, src, tests。

## 问题描述
Often when I use the Click `progressbar` I find myself wanting to conditionally hide it. Sometimes it's because there's another option in play which means I have output to display in place of it - others it's because I added a `--silent` option (as seen in `curl`) for disabling it entirely.

It's actually a bit tricky doing this at the moment, due to its use as a context manager.

What I'd really like to be able to do is this:

```python
hide = True  # or False depending on various things

with click.progressbar(items, show_eta=True, hide=hide):
    for item in items:
        process_item(item)
```

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：c326df95e9e3。