# [Feature Request] Consider adding a `key` argument to `SpecifierSet.filter()`

## 项目上下文
pypa/packaging（Python 项目），涉及模块：pyproject.toml, src, tests。

## 问题描述
I report here because packaging 26.0 introduces a behavior change(#895, #897). Regardless of whether I agree with the motivation for this change, it has made things somewhat more difficult.

Let me elaborate, when we filter versions, we seldom use the `SpecifierSet.filter()` method because it only accepts a set of versions. Usually, we have several objects, and each object has a version attribute, which is very common in package management tools. So to filter these objects, we have to use `.contain()` method like following:

```python
# on packaging==25, when prereleases is not explicitly given, it will respect specifier.prereleases property.
# while on packaging==26, it always accept prereleases
acceptable_candidates = [can for can in candidates if specifier.contains(can.version)]
# For the second run, check if there are no candidates available.
if no acceptable_candidates and not specifier.prereleases:
    acceptable_candidates = [can for can in candidates if specifier.contains(can.version, True)]
```

Due to the change of packaging 26, this snippet no longer works as PEP 440. We have to always pass `prereleases=` explicitly.

I considered that since `.filter()` exists and can automatically execute the above logic, we should use it directly. But the fact that it only accepts a set of versions prevented me from doing so. I believe my usage is not in the minority, so I think we can add a `key` parameter to `.filter()` to return the version of each element. So the above code can be simplified as following:

```python
acceptable_candidates = specifier.filter(candidates, key=operator.attrgetter("version"))
```
It no longer needs a second filter.

cc  for what you think

I can drive the PR if this is okay.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：0e9f03137bba。