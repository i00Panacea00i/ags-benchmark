# Disable upgrade prompt on `EXTERNALLY-MANAGED` environments

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
### Description

It's slightly odd that pip recommends running a pip install --upgrade pip that cannot succeed under EXTERNALLY-MANAGED environments

### Expected behavior

_No response_

### pip version

23.0.1

### Python version

3.11

### OS

Debian

### How to Reproduce

N/A

### Output

_No response_

### Code of Conduct

- [x] I agree to follow the [PSF Code of Conduct](

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：420435903ff2。