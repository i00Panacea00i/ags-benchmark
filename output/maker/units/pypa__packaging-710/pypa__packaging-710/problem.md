# Incorrect platform tag returned for GraalPy

## 项目上下文
pypa/packaging（Python 项目），涉及模块：src, tests。

## 问题描述
When running a 64-bit version of GraalPy (either x86_64 or aarch64), packaging returns the wrong platform tag (either i686 or armv8l).

Attempt to fix in  which is now closed.
Hopefully,  might help in the future but, for now and for already released python interpreters versions, a fix is needed in packaging.

cc

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：7e68d828f265。