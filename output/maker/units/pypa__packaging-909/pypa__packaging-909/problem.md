# Bug: `parse_wheel_filenames` accepts wheel filenames with unsorted compressed tag sets

## 项目上下文
pypa/packaging（Python 项目），涉及模块：src, tests。

## 问题描述
Hello `packaging` maintainers! 

I'm filing this as a bug report for some observed behavior.

TL;DR: `parse_wheel_filename` appears to allow _compressed tag sets_ (defined in [PEP 425]( to appear in any order, while the PEP and living spec both require the order to be "sorted" (my emphasis below):

> To allow for compact filenames of bdists that work with more than one compatibility tag triple, each tag in a filename can instead be a ‘.’-separated, **sorted**, set of tags. For example, pip, a pure-Python package that is written to run under Python 2 and 3 with the same source code, could distribute a bdist with the tag py2.py3-none-any.

(Permalinks: < and <

This can be seen by using `parse_wheel_filename` to parse a wheel whose compressed tags are out of order:

```python
from packaging.utils import parse_wheel_filename

name = "pyvirtualcam-0.13.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
parse_wheel_filename(name) 
```

## Actual behavior

The above call yields:

```
('pyvirtualcam', <Version('0.13.0')>, (), frozenset({<cp310-cp310-manylinux_2_17_x86_64 @ 4370315200>, <cp310-cp310-manylinux2014_x86_64 @ 4370315520>}))
```

## Expected behavior

I expected the above the raise a (subclass of) `ValueError`, since the compressed tag set appears in the wrong order in the wheel's filename.

The right order would be: `pyvirtualcam-0.13.0-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`.

## Additional context

This was noticed due to an interaction of a few different components in 

1. A user built a wheel (named `pyvirtualcam-0.13.0-cp310-cp310-linux_x86_64.whl`);
2. They called `auditwheel repair` on the wheel, which re-tagged it as `pyvirtualcam-0.13.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`). This tag ordering is incorrect per PEP 425, and is being tracked against `auditwheel` with 
3. `packaging` doesn't warn or fail with the new wheel distribution name, per this bug report;
4. `pypi-attestations` then "ultranormali

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：af0026cff97a。