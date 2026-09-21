# migrating from distlib.wheel: `packaging.utils.parse_wheel_filename` allows illegal platform tags

## 项目上下文
pypa/packaging（Python 项目），涉及模块：CHANGELOG.rst, src, tests。

## 问题描述
I'm looking to migrate a caller from utilizing `distlib.wheel` to instead use `packaging.utils.parse_wheel_filename` and my tests encountered an edge case which isn't handled by the `packaging` version

here's the distlib code: 

packaging's `parse_tag` doesn't validate the interpreter in any way -- whereas distlib required a particular structure

the test case in question: 

`playlyfe-0.1.1-2.7.6-none-any.whl` should not parse as a valid wheel, however `packaging` allows it (and parses as three separate tag-triplets: `2-none-any`, `7-none-any`, `6-none-any`)

I propose adding a little bit of validation to `parse_tag` to check that the tags are supported interpreter versions

I believe this involves something like:

```python
_INTERPRETER_RE = re.compile(fr'^(?:{"|".join(sorted(INTERPRETER_SHORT_NAMES.values()))}\d+')
```

and then utilizing that regex to validate the names (and throwing an appropriate exception) -- I think a new `InvalidTag` (extending `ValueError`) or somesuch exception would need to be created as well (similar to the ones in `packaging.utils` for the wheel / stdist filename)

wanted to propose this first before diving in and implementing it to save time -- thoughts?

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：b62954b62d04。