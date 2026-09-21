# pygettext.py: Black 26.1.0 on Python (CPython) 3.14 produced different code on the second pass of the formatter

## 项目上下文
psf/black（Python 项目），涉及模块：CHANGES.md, src, tests。

## 问题描述
**Describe the bug**

Black crashes with the mentioned error on a very old script that we have included for ages

**To Reproduce**

See: 

Log as mentioned in the error:
[blk_ym54yfeb.log](

This also happens when I use black.vercel.app. 
It crashes.

**Expected behavior**

No failure

**Environment**

Black 26.1.0
Windows and black.vercel.app. 

**Additional context**

<!-- Add any other context about the problem here. -->

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：a998a1816d04。