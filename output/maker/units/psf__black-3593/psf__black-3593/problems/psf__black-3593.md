# Let black run on files even if `ast.parse` with `type_comments=True` fails

## 项目上下文
psf/black（Python 项目），涉及模块：CHANGES.md, src, tests。

## 问题描述
**Is your feature request related to a problem? Please describe.**

Right now, if a file parsing because of invalid type comments (even if the code runs just fine), black won't format the file.

For example:

```python
import typing

def foo(
    # type: typing.List
    bar,
):
    print(bar)

foo(10)
```

While the code still runs:

```console
$ python3 asd.py            
10
```

Black no longer formats it:

```console
$ black asd.py        
error: cannot format asd.py: cannot use --safe with this file; failed to parse source file AST: invalid syntax (<unknown>, line 4)
This could be caused by running Black with an older Python version that does not support new syntax used in your source file.

Oh no! 💥 💔 💥
1 file failed to reformat.
```

This is because `ast.parse` on that code fails if you pass `type_comments=True`:

```pycon
>>> import ast
>>> ast.parse(open('asd.py').read(), type_comments=True)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/opt/homebrew/Cellar/python.10/3.10.9/Frameworks/Python.framework/Versions/3.10/lib/python3.10/ast.py", line 50, in parse
    return compile(source, filename, mode, flags,
  File "<unknown>", line 4
    # type: typing.List
            ^^^^^^^^^^^
SyntaxError: invalid syntax
```

(Black does work if you do `black asd.py --fast`, as it no longer does the AST based check.)

**Describe the solution you'd like**

If `ast.parse(..., type_comments=True)` fails for the before/after check, maybe doing it with `type_comments=False` is fine, just for that file?

**Describe alternatives you've considered**

None so far.

**Additional context**

I don't think this can be considered an upstream bug, as this is indeed invalid syntax for a type checker's perspective. But black shouldn't care if the types are correct, in any way shape or form.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：6ffc5f7b01ea。