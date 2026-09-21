# Cannot install pylock.toml from CPython dev version

## 项目上下文
pypa/packaging（Python 项目），涉及模块：src, tests。

## 问题描述
### Description

CPython's dev versions don't strictly follow PEP 440 because of the plus: 3.15.0a8+

This prevents pip installing from a pylock.toml with this version.

### Expected behavior

I expect to be able to install from a CPython dev version, because I'd like to use a lockfile for CPython's docs: 

### pip version

25.1

### Python version

3.15.0a8+

### OS

macOS and Linux

### How to Reproduce

1. Build CPython from source: 
2. Save this as `pylock.toml`:
```toml
lock-version = "1.0"
created-by = "minimal-repro"
requires-python = ">=3.12"
packages = []
```
3. Install: `python.exe  -m pip install -r pylock.toml`

### Output

```
Defaulting to user installation because normal site-packages is not writeable
WARNING: Using pylock.toml as a requirements source is an experimental feature. It may be removed/changed in a future release without prior warning.
ERROR: Cannot select requirements from pylock file 'pylock.toml': python_full_version '3.15.0a8+' in provided environment does not satisfy the Python version requirement '>=3.12'
```

See also 

This comes from `src/packaging/pylock.py`

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：e7b42de39c79。