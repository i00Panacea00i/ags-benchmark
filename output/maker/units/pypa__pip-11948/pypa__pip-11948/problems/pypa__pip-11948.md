# Install report download_info.info.hashes missing for direct URL archives without link hash

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
### Description

When installing an archive from a direct URL where the URL does not contain a hash fragment, the installation report misses the `hashes` key and only has the legacy `hash` key.

Originally reported by  in 

### Expected behavior

The `hashes` key should be populated.

### pip version

From 23.0

### Python version

any

### OS

any

### How to Reproduce

`pip install --dry-run --quiet --report -  {local archive}`.

### Output

_No response_

### Code of Conduct

- [X] I agree to follow the [PSF Code of Conduct](

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：55f1251fa28b。