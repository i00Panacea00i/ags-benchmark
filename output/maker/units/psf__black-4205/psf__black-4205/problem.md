# `black` ignores file in current folder if current folder is `git` workspace and (parent of) current folder is a symbolic link

## 项目上下文
psf/black（Python 项目），涉及模块：CHANGES.md, src, tests。

## 问题描述
**Describe the bug**

`black` incorrectly ignores a file in the current folder

**To Reproduce**

```
(.venv) C:\>dir

12/21/2023  10:19 AM    <JUNCTION>     Code [C:\ws]
...
02/02/2024  08:33 AM    <DIR>          ws

(.venv) C:\>cd Code

(.venv) C:\Code>mkdir Bug

(.venv) C:\Code>cd Bug

(.venv) C:\Code\Bug>git init
Initialized empty Git repository in C:/ws/Bug/.git/

(.venv) C:\Code\Bug>echo 1 > bug.py

(.venv) C:\Code\Bug>black --verbose bug.py
Identified `C:\ws\Bug` as project root containing a .git directory.
bug.py ignored: is a symbolic link that points outside C:\ws\Bug
No Python files are present to be formatted. Nothing to do 😴
```

**Expected behavior**
`black` should not ignore `bug.py`

**Environment**

black, 24.1.2.dev11+g632f44bd68 (compiled: no)
Python (CPython) 3.12.1
Windows 10 22H2

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：a20100395cf6。