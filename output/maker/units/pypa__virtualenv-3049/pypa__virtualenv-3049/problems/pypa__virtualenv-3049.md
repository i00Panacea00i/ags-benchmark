# Python discovery resolves pyenv shims to system Python instead of pyenv-managed version

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：docs, src, tests。

## 问题描述
## Description

When using pyenv to manage Python versions, virtualenv's builtin discovery resolves pyenv shims to the system Python instead of the pyenv-managed version. For example, with pyenv providing Python 3.8.12 on `$PATH`, virtualenv resolves the shim to `/usr/bin/python3.8` (system Python 3.8.6).

Originally reported as [tox-dev/tox#3064]( but the issue is in virtualenv's discovery logic, not tox.

## Steps to Reproduce

1. Install a Python version via pyenv (e.g. `pyenv install 3.8.12`)
2. Set it as local version (`pyenv local 3.8.12`)
3. Confirm `python3.8 --version` returns 3.8.12
4. Have a different system Python 3.8 installed (e.g. `/usr/bin/python3.8` = 3.8.6)
5. Create a virtualenv targeting `python3.8`

The virtualenv will use the system Python 3.8.6 instead of the pyenv-managed 3.8.12.

## Verbose Discovery Log

From the original report, running `tox -rvvve py38` shows virtualenv's discovery:

```
py38: discover exe for PythonInfo(spec=CPython3.10.6) in /usr
py38: discover PATH[0]=/home/user/.pyenv/plugins/pyenv-virtualenv/shims
py38: discover PATH[1]=/home/user/.pyenv/shims
py38: got python info of %s from (PosixPath('/home/user/.pyenv/shims/python3.8'), ...)
py38: got python info of %s from (PosixPath('/usr/bin/python3.8'), ...)
py38: proposed PathPythonInfo(spec=CPython3.8.6.final.0-64, system=/usr/bin/python3.8, exe=/home/user/.pyenv/shims/python3.8, ...)
py38: accepted PathPythonInfo(spec=CPython3.8.6.final.0-64, system=/usr/bin/python3.8, ...)
```

The shim at `/home/user/.pyenv/shims/python3.8` is found first, but when resolving to get `PythonInfo`, it resolves `system=/usr/bin/python3.8` (3.8.6) instead of the pyenv-managed `/home/user/.pyenv/versions/3.8.12/bin/python3.8`.

## Expected Behavior

virtualenv should resolve pyenv shims to the actual Python they delegate to, respecting pyenv's version selection (`.python-version`, `PYENV_VERSION`, etc.), rather than resolving to the system Python.

## Environment

- OS: Ubuntu (Linux)
- pyenv 

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：e32d82d40b1a。