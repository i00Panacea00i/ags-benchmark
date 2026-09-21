# virtualenv --help is not formatting using terminal width

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：docs, src, tests。

## 问题描述
**Issue**

virtualenv --help should use terminal width to format output, but it does not. The output just runs on without regard for the terminal width which makes it hard to read.
Note: The argparse package does this by default, which I am very familiar with having used it for all my python programs.

Here is what a section of the output from virtualenv showing how it disregards terminal width:

<img width="939" height="420" alt="Image" src=" />

In contrast here is a section of output from `pip --help` showing how output should be formatted making it easy to read.

<img width="950" height="222" alt="Image" src=" />

**Environment**

Provide at least:

- OS: Windows 10
- Shell: git bash under Windows Terminal
- Python version and path: 
python was installed using pyenv
virtualenv was installed with pip

- `pip list` of the host python where `virtualenv` is installed:
  ```console
$ which python
/c/Users/julie/home/.local/pyenv/pyenv-win/shims/python
$ pyenv which python
C:\Users\julie\home\.local\pyenv\pyenv-win\versions\3.14.2\python.exe
$ python -V
Python 3.14.2
$ pip -V
pip 26.0.1 from C:\Users\julie\home\.local\pyenv\pyenv-win\versions\3.14.2\Lib\site-packages\pip (python 3.14)
$ virtualenv --version
virtualenv 21.2.0 from C:\Users\julie\home\.local\pyenv\pyenv-win\versions\3.14.2\Lib\site-packages\virtualenv\__init__.py
$ pip list
Package           Version
argcomplete       3.6.3
click             8.3.2
colorama          0.4.6
distlib           0.4.0
filelock          3.25.2
packaging         26.0
pip               25.3
pipx              1.11.1
platformdirs      4.9.4
python-discovery  1.2.1
stevedore         5.7.0
userpath          1.9.2
virtualenv        21.2.0
virtualenv-clone  0.5.7
virtualenvwrapper 6.1.1
```

**Output of the virtual environment creation**

Make sure to run the creation with `-vvv --with-traceback`:

```console

```

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：dfaa73826dad。