# The --python command-line flag should take precedence over config file python and VIRTUALENV_PYTHON variable 

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：src, tests。

## 问题描述
### Current state

Currently each python provided by `--python` cli flag is appended to the list. It's meant to provide [fallback functionality for interpreter discovery]( The side effect of it is that any python defined in configuration file or in the `VIRTUALENV_PYTHON` environment variable is used as default because the one provided by cli flag is at the end of the list.

I believe that it's a sane expectation for command line flags to take precedence over environment variables. 

### Example

Consider system with system python 3.9 where Alice for some reason prefers to create venvs with python 3.10, so she sets `VIRTUALENV_PYTHON` in her shell environment to `/usr/bin/python3.10`.

That way running:

```bash
virtualenv some-name
```

always creates venv with `python3.10`

That's fine until she needs to create virtual environment with `python3.8`, by running:

```bash
virtualenv --python python3.8 some-other-name
```

It unexpectedly produces virtual environment with `python3.10`

She can use:

```bash
virtualenv --try-first-with /usr/bin/python3.8 some-completely-different-name
```

but not:

```bash
virtualenv --try-first-with python3.8 some-other-completely-different-name
```

as `--try-first-with` works with paths only, and not with `pythonX.Y` specs.

All of that is hard to get from the [discovery docs]( and [introduction to cli flags section]( mentions that "Environment variables takes priority over the configuration file values" but is silent about precedence of values provided in the cli itself.

### Possible solutions

I am happy to fix it and propose pull request but I would like first to discuss the right way to approach it. The question is how to express the intent of the user in the best possible way without ambiguity and doubts.

One possibility is to call it a feature not a bug and just add more extensive description of behavior with examples to the docs. That way anyone who wants to change it has to wr

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：7f450c3e1d9f。