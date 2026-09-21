# Oversized numeric components raise ValueError instead of InvalidVersion / InvalidSpecifier in packaging 26.0

## 项目上下文
pypa/packaging（Python 项目），涉及模块：src, tests。

## 问题描述
I found that malformed inputs with oversized numeric components raise a raw
ValueError instead of the documented public exception types.

Confirmed on:
- packaging 26.0
- Python 3.12.7

Minimal reproducer:

```python
import packaging, sys
from packaging.version import Version, InvalidVersion
from packaging.specifiers import SpecifierSet, InvalidSpecifier

print("packaging:", packaging.__version__)
print("python:", sys.version)
print("int max str digits:", sys.get_int_max_str_digits())

def classify_version_exception(value: str) -> str:
    try:
        Version(value)
        return "OK"
    except InvalidVersion:
        return "InvalidVersion"
    except Exception as e:
        return type(e).__name__

def classify_specifier_exception(value: str) -> str:
    try:
        SpecifierSet(value)
        return "OK"
    except InvalidSpecifier:
        return "InvalidSpecifier"
    except Exception as e:
        return type(e).__name__

print("Version normal malformed:", classify_version_exception("not-a-version"))
print("Version oversized numeric:", classify_version_exception("1" * 5000))
print("Specifier normal malformed:", classify_specifier_exception("not a specifier"))
print("Specifier oversized numeric:", classify_specifier_exception(">=" + "1" * 5000))
```

Observed output:

```
packaging: 26.0
python: 3.12.7 | packaged by Anaconda, Inc. | (main, Oct  4 2024, 08:22:19) [Clang 14.0.6 ]
int max str digits: 4300
Version normal malformed: InvalidVersion
Version oversized numeric: ValueError
Specifier normal malformed: InvalidSpecifier
Specifier oversized numeric: ValueError
```

Expected behavior:

- invalid version inputs should raise InvalidVersion
- invalid specifier inputs should raise InvalidSpecifier

Actual behavior:

- oversized numeric inputs can leak a raw ValueError instead

This seems to break the documented exception boundary for invalid inputs and may
surprise callers that correctly catch the public exception types.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：905c90c1eb8c。