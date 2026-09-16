# Pip raises unhandled exception on invalid entrypoint in wheel

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
<!--
If you're reporting an issue for `--unstable-feature=resolver`, use the "Dependency resolver failures / errors" template instead.
-->

**Environment**

* pip version: 20.1.1, master
* Python version: 3.8 (probably any)
* OS: Ubuntu (probably any)

**Description**

When pip encounters invalid entrypoints in wheels, it raises a `ValueError` that is visible to the user.

**Expected behavior**

pip should throw a nicer looking error for this expected situation

**How to Reproduce**

```
cd "$(mktemp -d)"
git clone  .
tox -e py38 --notest
./.tox/py38/bin/python -c 'from tests.lib.wheel import make_wheel; print(make_wheel("a", "1", entry_points={"console_scripts": ["a = a:"]}).save_to_dir("."))'
python -m venv env
./env/bin/python -m pip install --upgrade pip
./env/bin/python -m pip install ./a-1-py2.py3-none-any.whl
```

**Output**

<details>
<summary>Output</summary>

```
$ cd "$(mktemp -d)"
$ git clone  .
Cloning into '.'...
remote: Enumerating objects: 20, done.
remote: Counting objects: 100% (20/20), done.
remote: Compressing objects: 100% (18/18), done.
remote: Total 63409 (delta 7), reused 5 (delta 0), pack-reused 63389
Receiving objects: 100% (63409/63409), 55.20 MiB | 68.35 MiB/s, done.
Resolving deltas: 100% (42341/42341), done.
$ tox -e py38 --notest
GLOB sdist-make: /tmp/user/1000/tmp.FMLLJSRxGK/setup.py
py38 create: /tmp/user/1000/tmp.FMLLJSRxGK/.tox/py38
py38 installdeps: -r/tmp/user/1000/tmp.FMLLJSRxGK/tools/requirements/tests.txt
py38 inst: /tmp/user/1000/tmp.FMLLJSRxGK/.tox/.tmp/package/1/pip-20.2.dev1.zip
py38 installed: apipkg==1.5,atomicwrites==1.4.0,attrs==19.3.0,cffi==1.14.0,coverage==5.2,cryptography==2.8,csv23==0.3.2,execnet==1.7.1,freezegun==0.3.15,mock==4.0.2,more-itertools==8.4.0,packaging==20.4,pip @ file:///tmp/user/1000/tmp.FMLLJSRxGK/.tox/.tmp/package/1/pip-20.2.dev1.zip,pluggy==0.13.1,pretend==1.0.9,py==1.9.0,pycparser==2.20,pyparsing==2.4.7,pytest==4.6.11,pytest-cov==2.10.0,pytest-fork

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：6236392d41f0。