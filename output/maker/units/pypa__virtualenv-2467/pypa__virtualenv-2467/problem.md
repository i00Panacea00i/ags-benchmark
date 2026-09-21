# Cache is not invalidated if PythonInfo is changed

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：docs, src, tests。

## 问题描述
**Issue**

For example in the commit  it was fixed that the venv prefix on Debian systems with 3.10 includes a wrong "local" prefix. But since `virtualenv` caches the PythonInfo class on disk if it called with a specific executable (e.g. poetry specifies a specific exe), it can happen that broken information is provided for the virtual env creation.

The package should include a mechanism to invalidate the cache data if the internals of the PythonInfo changes.

**Environment**

Provide at least:

- OS: Debian unstable
- Python: 3.10.9
- `pip list` of the host python where `virtualenv` is installed:

```console
$ pip list
Package                            Version
---------------------------------- -------------------------
appdirs                            1.4.4
argon2-cffi                        21.1.0
asn1crypto                         1.5.1
astroid                            2.12.13
asttokens                          2.2.0
async-generator                    1.10
attrs                              22.1.0
Babel                              2.10.3
backcall                           0.2.0
beautifulsoup4                     4.11.1
beniget                            0.4.1
black                              22.10.0
bleach                             5.0.1
borgbackup                         1.2.2
Brotli                             1.0.9
build                              0.7.0
bytecode                           0.14.0
certifi                            2022.9.24
chardet                            5.1.0
charset-normalizer                 3.0.1
click                              8.1.3
colorama                           0.4.6
coverage                           6.5.0
cryptography                       38.0.4
cupshelpers                        1.0
cycler                             0.11.0
dbus-python                        1.3.2
debugpy                            1.6.3+git20221103.a2a3328
decorator                          5.1.1

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：ec1c83e2b303。