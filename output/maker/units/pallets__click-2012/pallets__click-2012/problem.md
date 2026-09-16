# `flag_value` is passed through `ParamType.convert`

## 项目上下文
pallets/click（Python 项目），涉及模块：CHANGES.rst, src, tests。

## 问题描述
In upgrading from click 7.1.2 to 8.0.1, our click-based CLI started failing with type errors. We have click options whose default values are classes, and as of 8.0.1 they're being converted to strings.

This script is able to reproduce the behavior change:

```python
import click

class Class1:
    pass

class Class2:
    pass

.command()
.option("--cls1", "config_cls", flag_value=Class1, default=True)
.option("--cls2", "config_cls", flag_value=Class2)
def test(config_cls):
    print(config_cls)
    print(type(config_cls))

if __name__ == "__main__":
    test()

```

Behavior with click 7.1.2:
```shell-session
# pip freeze | grep click
click==7.1.2
# python test.py
<class '__main__.Class1'>
<class 'type'>
```

Behavior with 8.0.1:
```shell-session
# pip freeze | grep click
click==8.0.1
# python test.py
<class '__main__.Class1'>
<class 'str'>
```

The type of `config_cls` should be the class we specified, not 'str'.

Environment:

- Python version: 3.9
- Click version: 8.0.1

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：c8da1fcc2cb4。