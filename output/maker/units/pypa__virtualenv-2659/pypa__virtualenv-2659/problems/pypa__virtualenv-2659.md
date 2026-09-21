# `try-first-with` behaves differently for `--python` full paths and version specs

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：docs, src, tests。

## 问题描述
**Issue**

Describe what's the expected behaviour and what you're observing.

`--try-first-with` (and corresponding `try_first_with` config var) is described as "try first these interpreters before starting the discovery".

When using it, I observe a different behavior for it, depending on whether I use `--python` arg with a full interpreter path, or just a version specification.

Running `virtualenv` version `20.24.6`.

This creates a `python3.8` environment:

```
$ virtualenv --clear aaa --try-first-with=/usr/bin/python3.10 -p python3.8
created virtual environment CPython3.8.10.final.0-64 in 542ms
...
```

This creates a `python3.10` environment:

```
$ virtualenv --clear aaa --try-first-with=/usr/bin/python3.10 -p /usr/bin/python3.8
created virtual environment CPython3.10.13.final.0-64 in 525ms
...
```

The issue is that the behavior is different, and it's difficult to say what is the expected one. Documentation doesn't even mention the `try_first_with` config, nor does the help for the `--python` arg.

**Environment**

Provide at least:

- OS: Ubuntu 20.04
- `pip list` of the host python where `virtualenv` is installed:

```console
Package      Version
------------ -------
distlib      0.3.7
filelock     3.12.4
pip          23.0.1
platformdirs 3.11.0
setuptools   65.5.0
virtualenv   20.24.6
```

Tested in a clean virtualenv based on Python 3.10.

**Output of the virtual environment creation**

Make sure to run the creation with `-vvv --with-traceback`:

For `-p` with version spec:

```console
102 setup logging to NOTSET [DEBUG report:37]
106 find interpreter for spec PythonSpec(major=3, minor=8) [INFO builtin:58]
107 Attempting to acquire lock 140469522451232 on /home/.local/share/virtualenv/py_info/1/8a94588eda9d64d9e9a351ab8144e55b1fabf5113b54e67dd26a8c27df0381b3.lock [DEBUG _api:219]
107 Lock 140469522451232 acquired on /home/.local/share/virtualenv/py_info/1/8a94588eda9d64d9e9a351ab8144e55b1fabf5113b5

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：19796cfd76b9。