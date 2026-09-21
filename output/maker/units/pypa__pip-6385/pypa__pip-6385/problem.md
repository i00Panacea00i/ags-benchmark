# pip install raises exception on two markers in requirements file

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
**Environment**

* pip version:  19.0.3
* Python version: 3.4 (but happens also at least on 2.7 and 3.7)
* OS: Ubuntu 14.04.5 LTS (Travis CI)

**Description**

When using two python version markers in a requirements file, pip install raises an exception.

The following is from Travis job 

```
pip install --upgrade -r dev-requirements.txt
DEPRECATION: Python 3.4 support has been deprecated. pip 19.1 will be the last one supporting it. Please upgrade your Python as Python 3.4 won't be maintained after March 2019 (cf PEP 429).
Ignoring pytest: markers 'python_version == "2.6"' don't match your environment
Ignoring httpretty: markers 'python_version == "2.6"' don't match your environment
Ignoring lxml: markers 'python_version == "2.6"' don't match your environment
Ignoring PyYAML: markers 'python_version == "2.6"' don't match your environment
Ignoring python-coveralls: markers 'python_version == "2.7"' don't match your environment
Exception:
Traceback (most recent call last):
  File "/home/travis/virtualenv/python3.4.6/lib/python3.4/site-packages/pip/_vendor/packaging/markers.py", line 270, in __init__
    self._markers = _coerce_parse_result(MARKER.parseString(marker))
  File "/home/travis/virtualenv/python3.4.6/lib/python3.4/site-packages/pip/_vendor/pyparsing.py", line 1814, in parseString
    raise exc
  File "/home/travis/virtualenv/python3.4.6/lib/python3.4/site-packages/pip/_vendor/pyparsing.py", line 1804, in parseString
    loc, tokens = self._parse( instring, 0 )
  File "/home/travis/virtualenv/python3.4.6/lib/python3.4/site-packages/pip/_vendor/pyparsing.py", line 1548, in _parseNoCache
    loc,tokens = self.parseImpl( instring, preloc, doActions )
  File "/home/travis/virtualenv/python3.4.6/lib/python3.4/site-packages/pip/_vendor/pyparsing.py", line 3722, in parseImpl
    loc, exprtokens = e._parse( instring, loc, doActions )
  File "/home/travis/virtualenv/python3.4.6/lib/python3.4/site-packages/pip/_vendor/pyparsing.py", li

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：9d0e2601f8c8。