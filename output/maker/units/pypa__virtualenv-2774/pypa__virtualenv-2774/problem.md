# python3.exe missing on windows when creating a virtualvenv

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：docs, src, tests。

## 问题描述
**Issue**

I mainly develop for linux on a windows so all my scripts start with `#!/usr/bin/env python3`

I created a precommit hack for git and it fails on the shebang `python3 not found` This is the first ever I've seen
the shebang being used on windows. So I discovered it was not there :-)

We have lots of legacy system with legacy python pointing to old version2 python, and -m venv creates a python3 softlink on linux

So it would be nice if they where the same.

I see I do not have a python3.exe under windows main python either, but how can we assure same file will run same binary

**Environment**

Provide at least:

- OS: windows11
- `pip list` of the host python where `virtualenv` is installed:

```console
pip list
Package Version
------- -------
pip     24.2
 ```

**Output of the virtual environment creation**

Make sure to run the creation with `-vvv --with-traceback`:

```console
python -m venv C:\dist\venvs\ranchercli
(trk-fullstack-test) PS C:\dist\trk-fullstack-test> C:\dist\venvs\ranchercli\Scripts\Activate.ps1
(ranchercli) PS C:\dist\trk-fullstack-test> where.exe python3
INFO: Could not find files for the given pattern(s).
(ranchercli) PS C:\dist\trk-fullstack-test> where.exe python 
C:\dist\venvs\ranchercli\Scripts\python.exe
C:\dist\python312\python.exe
(ranchercli) PS C:\dist\trk-fullstack-test> python --version
Python 3.12.6
(ranchercli) PS C:\dist\trk-fullstack-test> ls -l C:\dist\venvs\ranchercli\Scripts\


    Directory: C:\dist\venvs\ranchercli\Scripts


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        30.09.2024     16:31           2052 activate
-a----        30.09.2024     16:31           1005 activate.bat
-a----        30.09.2024     16:31          26199 Activate.ps1
-a----        30.09.2024     16:31            393 deactivate.bat
-a----        30.09.2024     16:31         108402 pip.exe
-a----        30.09.2024   

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：ec924643a494。