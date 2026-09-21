# Make pip gracefully detect git servers that don't support `--filter=blob:none`

## 项目上下文
pypa/pip（Python 项目），涉及模块：docs, news, src, tests。

## 问题描述
### Description

This behaviour is observed since pip version 21.3 which has the changes for (#9086)

The change introduces the addition of the --filter=blob:none option for git clone when installing a pip package from a git repo. As a result of the change, the repo package that I'm trying to install errors out with the following signature

```
(fast2) ➜  ~ pip install zcsdgapi+
Collecting zcsdgapi@ git+
  Cloning  to /private/var/folders/z5/f81ktg8d5ng_pskb9wg2q4qr0000gn/T/pip-install-_jsv_zuz/zcsdgapi_e5a7fb3aae9d4eef9d8d91c42547d486
  Running command git clone --filter=blob:none -q  /private/var/folders/z5/f81ktg8d5ng_pskb9wg2q4qr0000gn/T/pip-install-_jsv_zuz/zcsdgapi_e5a7fb3aae9d4eef9d8d91c42547d486
  fatal: bad revision '43995bd42fa23bbc4c3a59d5fb9da99042fcf139'
  error:  did not send all necessary objects

  fatal: bad revision '43995bd42fa23bbc4c3a59d5fb9da99042fcf139'
  error:  did not send all necessary objects
```

The problem is reproduced on a mac terminal and ubuntu terminal , git versions are 
OSX
```
(fast2) ➜  ~ git --version
git version 2.32.0 (Apple Git-132)
(fast2) ➜  ~ and 
```
UBUNTU
```
$ git --version
git version 2.25.1
```


The complete workflow I performed is attached below. When trying with pip version 21.2.4 the install works correctly, when attempting with 21.3 it fails and the git clone command can be seen with the filter=blob:none flags set.

```
(fast2) ➜  ~ pip install --upgrade pip==21.2.4
Collecting pip==21.2.4
  Using cached pip-21.2.4-py3-none-any.whl (1.6 MB)
Installing collected packages: pip
  Attempting uninstall: pip
    Found existing installation: pip 21.2.3
    Uninstalling pip-21.2.3:
      Successfully uninstalled pip-21.2.3
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
fast 22.4.15 requires zcsdgapi@ git+ which is not installed.
Successfully instal

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：c8b4819f2ae8。