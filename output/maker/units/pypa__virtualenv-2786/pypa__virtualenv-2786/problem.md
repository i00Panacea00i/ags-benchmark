# creating a virtual environment on a filesystem without symlink-support fails even with --copies

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：docs, src, tests。

## 问题描述
**Issue**

i am new to python venv, so please forgive me if i open the issue on a wrong place or missunderstood something.

as i am on a virtualmachine which is hosted on a windows system where i share the repository i am working in with the hsot system i 

**Environment**

Provide at least:

- OS: alpine 3.19
- `pip list` of the host python where `virtualenv` is installed:

```console
 pip list
Package                   Version
------------------------- --------
altgraph                  0.17.3
ansible                   8.6.1
ansible-compat            3.0.2
ansible-core              2.16.1
argcomplete               3.1.1
arrow                     1.2.3
attrs                     23.1.0
bcrypt                    4.1.1
binaryornot               0.4.4
certifi                   2023.5.7
cffi                      1.16.0
chardet                   5.1.0
charset-normalizer        3.1.0
click                     8.1.3
click-help-colors         0.9.1
cookiecutter              2.1.1
cryptography              41.0.7
distlib                   0.3.7
distro                    1.8.0
docker                    6.1.2
enrich                    1.2.7
filelock                  3.12.4
hcloud                    2.2.1
idna                      3.4
iniconfig                 1.1.1
Jinja2                    3.1.4
jinja2-time               0.2.0
jmespath                  1.0.1
jsonschema                4.17.3
markdown-it-py            2.2.0
MarkupSafe                2.1.3
mdurl                     0.1.2
molecule                  5.0.1
molecule-docker           2.1.0
molecule-podman           2.0.3
mypy                      1.6.1
mypy-extensions           1.0.0
netaddr                   0.9.0
packaging                 23.2
paramiko                  3.4.0
pip                       23.3.1
platformdirs              4.0.0
pluggy                    1.0.0
py                        1.11.0
pycparser                 2.21
Pygments              

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：683e5db32537。