# TypeError when installing from git and git version contains a letter

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
### Description

I am trying to install a dependency from a git source and get an exception because the git version cannot be parsed

Going through the code (I have pip version 23.2.1 installed), it seems the issue is with my git version that contains an alphabetical patch version…

```bash
$ git version
git version 2.37.GIT
```

In `git.py:100` the match produces 3 groups with the last one being `None` because of the way the `GIT_VERSION_REGEX` is built. That in turns create a problem in `git.py:104` because `tuple(int(c) for c in match.groups())` doesn't work with the `None` value.

### Expected behavior

I would expect pip to accept the major and minor git version as they are and go on without a numeric patch version. But I can't tell why it is checking the version numbers.

### pip version

23.2.1

### Python version

3.9.9

### OS

Debian 11.5

### How to Reproduce

I can't share the code but what I do is simply `pip install "my_package @ git+

### Output

This is the full stacktrace :

```
ERROR: Exception:
Traceback (most recent call last):
  File "/home/lcottereau/my_project/env/lib/python3.9/site-packages/pip/_internal/cli/base_command.py", line 180, in exc_logging_wrapper
    status = run_func(*args)
  File "/home/lcottereau/my_project/env/lib/python3.9/site-packages/pip/_internal/cli/req_command.py", line 248, in wrapper
    return func(self, options, args)
  File "/home/lcottereau/my_project/env/lib/python3.9/site-packages/pip/_internal/commands/install.py", line 377, in run
    requirement_set = resolver.resolve(
  File "/home/lcottereau/my_project/env/lib/python3.9/site-packages/pip/_internal/resolution/resolvelib/resolver.py", line 73, in resolve
    collected = self.factory.collect_root_requirements(root_reqs)
  File "/home/lcottereau/my_project/env/lib/python3.9/site-packages/pip/_internal/resolution/resolvelib/factory.py", line 491, in collect_root_requirements
    req = self._make_requirement_from_install_req(
  File "/home

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：0827d76bd298。