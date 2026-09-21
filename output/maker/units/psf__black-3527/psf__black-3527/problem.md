# Apply excludes before normalising symlinks

## 项目上下文
psf/black（Python 项目），涉及模块：CHANGES.md, src, tests。

## 问题描述
**Is your feature request related to a problem? Please describe.**

Our project contains symlinks like this:

```
project
+- a
   +- b -> ../x/y
   +- other files
+- x
   +- y
      +- lots of files
```

We would like to avoid black spending time formatting/complaining about the same files twice, so we make the excludes regex match `/a/b/`.
This doesn't help because the excludes are evaluated after normalising the path to `/x/y/`.
We cannot put that in the excludes because we do want to format the files.

**Describe the solution you'd like**

Excludes could be evaluated before normalising the path, or at least before evaluating symlinks.

**Describe alternatives you've considered**

Perhaps it would be best to evaluate excludes both before and after normalising the path.
There is also a use case for the way it is now, if we did want to exclude the files completely without listing all paths to them in the excludes.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：c6a031e623c7。