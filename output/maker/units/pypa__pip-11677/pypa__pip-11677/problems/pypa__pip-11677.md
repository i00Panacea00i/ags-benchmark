# `pip list` should not perform a self-update check

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
### Description

Running `pip` in env which is cu off from public network I found that on each execution it tries to check availability of its new version.
It causes long freezing of pip command and atthe end it prints message `WARNING: There was an error checking the latest version of pip.`


### Expected behavior

IMO `pip` should **only** do what is specified in commad lie parameters and nothing more.


### pip version

22.3.1

### Python version

3.8.16

### OS

Linux x86/64

### How to Reproduce

Run `pip list` in env which is cut off from access to the public network.

### Output

Example:
```
$ time pip list
Package                       Version
----------------------------- -----------------
alabaster                     0.7.12
appdirs                       1.4.4

[..]

urllib3                       1.26.12
wheel                         0.38.4
zipp                          3.11.0
WARNING: There was an error checking the latest version of pip.

real    2m0.771s
user    0m0.605s
sys     0m0.114s
```

### Code of Conduct

- [X] I agree to follow the [PSF Code of Conduct](

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：46a342b44888。