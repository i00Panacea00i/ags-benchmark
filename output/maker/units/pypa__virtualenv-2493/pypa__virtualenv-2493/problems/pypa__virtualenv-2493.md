# Better error message with failing discovery

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：docs, src, tests。

## 问题描述
**What's the problem this feature will solve?**

`pre-commit` failed due to `StopIteration`. Investigation shows that this is caused by an error thrown by `virtualenv`. See below for full trace when attempting to construct a virtual environment. Through discussion on the virtualenv discord, this closed issue was suggested as related: #2176

Investigation strongly suggested that the issue was indeed related. Pip uninstalling all packages and reinstalling only `virtualenv` allowed for creation of the virtual environment. `pip list` before uninstalling shows that there were some horribly out of date packages for the python version used. Removing or updating the packages fixed the issue.

**Describe the solution you'd like**

While I was able to identify and fix the issue with a bit of help from the virtualenv community, the error was cryptic and did not provide information about what problem was or what steps could be taken to solve it. 

I am not familiar with the discovery process, but a message stating which package or path was causing the issue would be helpful. Perhaps:
```
> python -m virtualenv my_venv
Error: package discovery failed for <packageName>. Please check for package updates.
```

**Alternative Solutions**

`pip list -o` does show the installed and latest version of all packages which was able to help me find which were significantly out of date, but this is a partial solution unless a user knows that other packages are the issue. Adding a note to the Users Guide may be helpful.



This is the current output (with full traceback):
```console
> python -m virtualenv --with-traceback my_venv
Traceback (most recent call last):
  File "C:\ANSYSDev\develop\Core_Dependencies\CPython\3_10\winx64\Release\python\lib\runpy.py", line 196, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "C:\ANSYSDev\develop\Core_Dependencies\CPython\3_10\winx64\Release\python\lib\runpy.py", line 86, in _run_code
    exec(cod

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：153227f8b848。