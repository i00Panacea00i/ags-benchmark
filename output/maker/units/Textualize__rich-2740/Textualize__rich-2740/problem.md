# [BUG] Double rendering of notebook output with `rich>=12.6.0`

## 项目上下文
Textualize/rich（Python 项目），涉及模块：CHANGELOG.md, CONTRIBUTORS.md, rich, tests。

## 问题描述
- [x] I've checked [docs]( and [closed issues]( for possible solutions.
- [x] I can't find my issue in the [FAQ](

**Describe the bug**
It appears the double rendering issue referenced in #1737 has returned starting in version 12.6.0.

With a poetry environment given by:

```toml
[tool.poetry]
name = "rich-bug-repro"
version = "0.0.1"
description = "..."
authors = ["John Doe"]

[tool.poetry.dependencies]
python = "^3.9"
jupyter = "^1.0.0"
rich = {version = "x.x.x", extras=["jupyter"]}  # fill out with desired version
```

a simple reproducing example is (from a jupyter notebook)

```python
from rich.progress import track
import time

for i in track(range(100)):
    time.sleep(0.01)
```

when `version` is set to any of `12.6.0,13.0.0,13.0.1` in the `pyproject.toml` above, the output of this example looks like



When using `<12.6.0`, you get the expected


Note that this is strictly a jupyter problem: for any of these versions, running e.g.
```console
python -c 'from rich.progress import track;import time;[time.sleep(0.01) for _ in track(range(100))]'
```
results in just a single progress bar being printed, as expected.

**Platform**
<details>
<summary>Click to expand</summary>

What platform (Win/Linux/Mac) are you running on? What terminal software are you using?
Linux, both natively and in WSL2 on Windows.

I may ask you to copy and paste the output of the following commands. It may save some time if you do it now.

If you're using Rich in a terminal:

```
python -m rich.diagnose
pip freeze | grep rich
```

If you're using Rich in a Jupyter Notebook, run the following snippet in a cell
and paste the output in your bug report.

```python
from rich.diagnose import report
report()
```
```console
╭────────────────────── <class 'rich.console.Console'> ──────────────────────╮
│ A high level console interface.                                            │
│                                               

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：155bd04b1258。