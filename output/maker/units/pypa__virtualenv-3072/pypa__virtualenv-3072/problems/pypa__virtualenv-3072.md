# pythonw3.exe is missing

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：src, tests。

## 问题描述
**Issue**

Occasionally, users may install a Python package that includes GUI scripts. If they use 

```
python3 -m pip install "git+
```

for example, to install a package, the GUI script will look for `pythonw3.exe` since they used `python3`. If they do this with virtualenv, then there will be an error because, for some reason, `pythonw3.exe` is not created by virtualenv.

The current workaround we have found is to use 

```
python -m pip install "git+
```

so that the GUI script is created, which will look for `pythonw.exe`, which is created by virtualenv. See  for more details.

Provide at least:

- OS: Windows 11
- Shell: powershell
- Python version and path:  Python 3.14.3  'C:\\Users\\username\\AppData\\Local\\Python\\pythoncore-3.14-64'
- `pip list` of the host python where `virtualenv` is installed:

```
Package      Version
------------ -------
distlib      0.4.0
filelock     3.24.3
pip          26.0.1
platformdirs 4.9.2
virtualenv   20.38.0
```

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：1d4a33811f99。