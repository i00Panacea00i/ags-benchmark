# Interpreter lookup fails when first `-p` value is absolute and missing

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：docs, src, tests。

## 问题描述
We use virtualenv and tox to run tests against a commercial application that embeds its own Python interpreter. The location of that interpreter varies by OS, so we pass all the possible locations as `-p` values to virtualenv by providing multiple values of `basepython` on `tox.ini`.

**Issue**

When providing the `-p` / `--python` multiple time, virtualenv creation fails if a missing, absolute path occurs before an existing path.

**Output of the virtual environment creation**

```console
# This works fine:
$ virtualenv -p this/doesnt/exist -p python3.9 dest
created virtual environment CPython3.9.5.final.0-64 in 363ms
[snip]
# But this fails
$ virtualenv -p /this/doesnt/exist -p python3.9 dest
FileNotFoundError: [Errno 2] No such file or directory: '/this/doesnt/exist'
```

I'd expect the absolute path to be handled just like the relative path, e.g. the failure should be ignored and we should move on to the next `-p` value.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：07e61107546b。