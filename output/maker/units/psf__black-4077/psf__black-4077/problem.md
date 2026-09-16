# pathlib exception when symlinks are involved

## 项目上下文
psf/black（Python 项目），涉及模块：CHANGES.md, src, tests。

## 问题描述
**Describe the bug**

Hello! First of all, thank you for this invaluable tool.

I first ran into this issue on Windows when using black to format code located on a mapped network drive. 

This line in [get_sources()]( doesn't ignore symlinks pointing outside of `root`, which has symlinks resolved by [find_project_root()](


**To Reproduce on Linux**

```shell
mkdir test_black
ln -s test_black test_black_sym
cd test_black
git init
echo "print('hello')" > app.py
black ~/test_black_sym/app.py
```

`git init` is needed so that [find_project_root()]( doesn't return the root of the file system. 

The resulting error is:

```shell
Traceback (most recent call last):
  <some omitted>
  File "/home/tg2648/black/src/black/__init__.py", line 600, in main
    sources = get_sources(
              ^^^^^^^^^^^^
  File "/home/tg2648/black/src/black/__init__.py", line 687, in get_sources
    root_relative_path = path.absolute().relative_to(root).as_posix()
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/tg2648/.pyenv/versions/3.11.0/lib/python3.11/pathlib.py", line 730, in relative_to
    raise ValueError("{!r} is not in the subpath of {!r}"
ValueError: '/home/tg2648/test_black_sym/app.py' is not in the subpath of '/home/tg2648/test_black' OR one path is relative and the other is absolute.
```

**Environment**

<!-- Please complete the following information: -->

- Black's version: 23.11.0
- OS and Python version: Windows and Linux / Python 3.11.0

**Ideas**

[normalize_path_maybe_ignore()]( which is used later in `get_sources()`, also calculates the root relative path but catches the `ValueError` exception:



Maybe one solution is to extract these lines into a function like `get_root_relative_path` and then use it in `get_sources()` and `normalize_path_maybe_ignore()`. I can submit a PR if this sounds reasonable.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：995e4ada14d6。