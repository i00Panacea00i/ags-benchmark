# Crude error message if using VIRTUALENV_DISCOVERY=pyenv

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：src, tests。

## 问题描述
When virtualenv-pyenv is not installed, and the pyenv entry point is therefore not available.

### virtualenv, with cli parameter

Using cli parameter, the response is reasonable and helpful

```
$ virtualenv --discovery pyenv myenv
usage: virtualenv [--version] [--with-traceback] [-v | -q] [--read-only-app-data] [--app-data APP_DATA] [--reset-app-data] [--upgrade-embed-wheels] [--discovery {builtin}]
virtualenv: error: argument --discovery: invalid choice: 'pyenv' (choose from 'builtin')
SystemExit: 2
```

### virtualenv, with env.var.

If using the environment variable, its less helpful:

```
$ VIRTUALENV_DISCOVERY=pyenv virtualenv myenv
KeyError: 'pyenv'
```

### tox, with env.var.

```
# tox.ini
[tox]
envlist = py39

[testenv]
commands = pytest
setenv = 
    VIRTUALENV_DISCOVERY=pyenv
```

The result is both messy and unhelpful. And as a newbie, I thought it was probably a bug, but in fact I just needed to install virtualenv-pyenv.

```
$ tox
py39: internal error
Traceback (most recent call last):
  File "/home/velle/.virtualenvs/toxrunner/lib/python3.12/site-packages/tox/session/cmd/run/single.py", line 47, in _evaluate
    tox_env.setup()
  File "/home/velle/.virtualenvs/toxrunner/lib/python3.12/site-packages/tox/tox_env/api.py", line 282, in setup
    self._setup_env()
  File "/home/velle/.virtualenvs/toxrunner/lib/python3.12/site-packages/tox/tox_env/python/runner.py", line 98, in _setup_env
    super()._setup_env()
  File "/home/velle/.virtualenvs/toxrunner/lib/python3.12/site-packages/tox/tox_env/python/api.py", line 243, in _setup_env
    self.ensure_python_env()
  File "/home/velle/.virtualenvs/toxrunner/lib/python3.12/site-packages/tox/tox_env/python/api.py", line 247, in ensure_python_env
    conf = self.python_cache()
           ^^^^^^^^^^^^^^^^^^^
  File "/home/velle/.virtualenvs/toxrunner/lib/python3.12/site-packages/tox/tox_env/python/virtual_env/api.py", line 82, in python_cache
    base = super().python_cache()
           ^^^^^^^^^^^^^^^^^^^^^^
 

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：44b7bd6d103b。