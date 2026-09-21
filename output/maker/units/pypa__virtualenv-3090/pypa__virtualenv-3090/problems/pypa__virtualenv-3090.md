# [Bash] activate script incorrectly uses $0 instead of BASH_SOURCE for relocation fallback

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：.github, docs, pyproject.toml, src, tests。

## 问题描述
**Issue**

When a virtual environment (created using [virtualenv.pyz]( is activated from a directory other than its own root (using either an absolute or relative path), the `PATH` variable is not updated correctly. Instead of pointing to the virtual environment's `bin` directory, it incorrectly adds a path relative to the user's **current location or the shell's location**. I have verified this locally on my system

This occurs because the `activate` script's fallback logic for determining `VIRTUAL_ENV` relies on `realpath "${0}"`. Since the script is intended to be **sourced** in `bash`, `${0}` evaluates to the name of the shell (e.g., `/bin/bash`), causing the script to calculate an incorrect root directory (often resulting in `<current directory>/bin` being added to the `PATH`).

**Environment**

- OS: Debian GNU/Linux rodete                     
- Kernel: Linux 6.17.13-1rodete1-amd64
- Architecture: x86-64
- Shell: bash
- Python version and path: Python 3.13.12 , /usr/bin/python3
- `pip list` of the host python where `virtualenv` is installed: 
` virtualenv                  20.36.1`
Others are not relevant here.
- The details of virtualenv.pyz: `[virtualenv.pyz](                                     27-Feb-2026 09:48             8378751`

**The exact problematic code**

**Potentially fixed code**
In the above code, the `CURRENT_PATH=$(realpath "${0}")` should be replaced with `CURRENT_PATH=$(realpath "${BASH_SOURCE[0]}")`

If the community agrees that this is the right fix then I can create a pull request.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：0cd0e0952686。