# pathspec v1 changes

## 项目上下文
psf/black（Python 项目），涉及模块：CHANGES.md, pyproject.toml, src, tests。

## 问题描述
**Is your feature request related to a problem? Please describe.**

Hi, I'm the author of [pathspec]( and recently released v1. The biggest change is *GitWildMatchPattern* (a.k.a. "gitwildmatch") was split into two different implementations. (1) *GitIgnoreBasicPattern* (a.k.a. "gitignore") is new and properly implements the patterns in [gitignore's documentation]( (2) *GitIgnoreSpecPattern* is the previous *GitWildMatchPattern* implementation and is used by *GitIgnoreSpec* to implement Git's edge-cases. 

**PathSpec**

The form `PathSpec.from_lines('gitwildmatch', ...)` is now deprecated because it does not fully match the behavior of the gitignore docs or Git itself. There's 3 possible replacements depending on the exact behavior you want:

1. To keep the exact behavior as before, use `PathSpec.from_lines(GitIgnoreSpecPattern, ...)`. This is the non-deprecated equivalent to using "gitwildmatch". I discourage this use because it's a hybrid between Git's behavior and the gitignore docs.
 
    ```python
    from pathspec.patterns.gitignore.spec import GitIgnoreSpecPattern
    ```

2. To follow the gitignore docs, use `PathSpec.from_lines('gitignore', ...)`. The change for using this form is "`foo/*`" will no longer match files in subdirectories, and the exact pattern "`/`" is equivalent to "`**`" (match everything) rather than being a no-op.

3. To follow Git's implementation, use `GitIgnoreSpec.from_lines(...)`. The change for using this is Git allows including files from excluded directories which directly contradicts the gitignore docs.

**GitIgnorePatternError**

*pathspec.patterns.gitwildmatch.GitWildMatchPatternError* is now a deprecated alias of *pathspec.patterns.gitignore.GitIgnorePatternError*. I recommend switching to *GitIgnorePatternError*.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：200c550aff44。