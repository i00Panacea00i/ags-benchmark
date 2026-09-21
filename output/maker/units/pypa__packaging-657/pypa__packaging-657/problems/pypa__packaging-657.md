# Improve error message when `.*` is used incorrectly

## 项目上下文
pypa/packaging（Python 项目），涉及模块：src, tests。

## 问题描述
The error message here complains about a right parenthesis missing, though that's not the issue:

```python
    raise InvalidRequirement(str(e)) from e
packaging.requirements.InvalidRequirement: Expected closing RIGHT_PARENTHESIS
    black (>=20.*) ; extra == 'format'
          ~~~~~^
```

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：63e657138d30。