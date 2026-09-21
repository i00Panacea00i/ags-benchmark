# Add option to bypass http proxy

## 项目上下文
pypa/pip（Python 项目），涉及模块：docs, news, src, tests。

## 问题描述
* Pip version: 10.0.1
* Python version: 2.7.8 & 3.6.3
* Operating system: Windows 7

### Description:

I'm trying to install packages from a local (SVN) repository. Since I'm behind a proxy I have configured the proxy in the pip.ini. For local resources pip should bypass the proxy. 

Please add an option to specify a list of IP address ranges, domains and domain wildcards to connect directly.

### What I've run:

```
prompt> pip install 

Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProxyError('Cannot connect to proxy.', timeout('timed out',))': /svn/MyRepo/trunk/some-package-1.0.0.zip
```

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：6989a79f97a4。