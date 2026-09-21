# TypeError: 'NoneType' object is not iterable on `if _SIMPLE_VERSION_INDICATORS.issuperset(version):`

## 项目上下文
pypa/packaging（Python 项目），涉及模块：src, tests。

## 问题描述
Hi. I'm not sure/don't think this is actually a problem in this package, but I don't know where to turn. I was updating my dev environment yesterday (python managed by MacPorts) and I began seeing this message while trying to build/install several different packages.

I've seen it at least on `hatchling`, `setuptools-rust`, `shelligham` and `hatch-vcs`, using python 3.13.

Any idea what might be causing it, or where might I begin to troubleshoot?

I already tried uninstalling all my python3.13 packages and starting from scratch, but it didn't really help.

E.T.A. versions of some possibly relevant packages:

```
The following ports are currently installed:
  py313-build .4.4_0 (active) requested_variants='' platform='darwin any' archs='noarch' date='2026-07-06T07:43:26-0400'
  py313-installer .0.1_0 (active) requested_variants='' platform='darwin any' archs='noarch' date='2026-07-06T07:43:23-0400'
  py313-packaging .2_0 (active) requested_variants='' platform='darwin any' archs='noarch' date='2026-07-06T07:43:25-0400'
  py313-setuptools .10.2_0 (active) requested_variants='' platform='darwin any' archs='noarch' date='2026-07-06T07:43:33-0400'
  py313-wheel .47.0_0 (active) requested_variants='' platform='darwin any' archs='noarch' date='2026-07-06T07:43:38-0400'
  python313 .13.14_0+lto+optimizations (active) requested_variants='-universal' platform='darwin 22' archs='x86_64' date='2026-07-05T13:34:52-0400'
```

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：0a85b41e24c9。