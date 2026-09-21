# Unclear documentation and error messages around combining post releases and prefix matches

## 项目上下文
pypa/packaging（Python 项目），涉及模块：src, tests。

## 问题描述
OS: Windows 11
CPython: 3.12.5
Packaging: 24.1

Apologies for re-raising an old issue:
- 
- 

However, I recently came across the issue while upgrading our python usage to 3.12.5, which includes pip 24.2 which vendors packaging 24.1. Previous discussions of the issue said they would be open to users sharing valid use cases for disallowed specifiers, so here I am ;)

The specific requirement I am trying to parse is of the form:
`a==1.2.3.post4.*`

Which we would like to match a version such as:
`a==1.2.3.post4.dev5`

Our use case for this is as follows:
- We have an internal pypi repo
- We patch and rebuild many externally-developed packages to meet our needs, before publishing them to our internal repo
- We use post versions for the "in between" versions between officially published external releases
- We use dev versions on those post versions while working on new changes
- We in turn use prefix matching when depending on those dev builds of patched external packages, to say, "use the latest development version of this particular post version"
- This allows us to develop against these changes before landing them and doing our official post release.

I appreciate this is a somewhat esoteric use case, but it's one we've been doing for a few years and not had issues with. Given the unusual nature of this requirement, I'm not going to push hard to change behaviour here.

*However*, the documentation and error messages do not match the behaviour. To find out that this was not allowed, I had to look at the packaging source code, track down the commit that made the change, then the pull request, and finally the issues and mailing list discussion it stemmed from. So, even if the behaviour is not changed, a documentation change would be very useful.

The documentation [here]( only talks about prefix matches being invalid after dev versions. It does not mention post versions. It also states, "a trailing .* is permitted on public version identifier

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：d2fa92384821。