# Add support for PEP 730 iOS packaging tags

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests, tools。

## 问题描述
### What's the problem this feature will solve?

PEP 730 added iOS as a supported platform. It would be desirable to be able to install third-party binary packages into iOS installs.

### Describe the solution you'd like

`pip` probably won't ever be run *on* an iOS device to install binary packages, as this would violate Apple's app distribution rules (and would be difficult to accomodate with iOS binary signing requirements). However, it should be possible to install an iOS binary package using `pip install --platform ios_13_0_arm64_iphoneos mypackage` (or similar)

### Alternative Solutions

[Briefcase]( currently has a workaround that involves using a `sitecustomize.py` script to mock being on iOS for the purpose of running pip. This works, but can only support a single binary tag. iOS support includes the minimum supported iOS version as part of the tag, and older compatible versions should be considered as part of a match.

### Additional context

See [PEP 730]( for details of iOS package tagging.

### Code of Conduct

- [X] I agree to follow the [PSF Code of Conduct](

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：93fa89c8eb4c。