# [BUG] ANSI sequences parsed incorrectly: \x1b(B\x1b[m

- [x] I've checked [docs]( and [closed issues]( for possible solutions.
- [x] I can't find my issue in the [FAQ](

**Describe the bug**

Some ANSI sequences (which I didn't know about) are not correctly parsed.
Here is a text example with such ANSI sequences:

```
src/failprint/capture.py:57: \x1b[1m\x1b[31merror:\x1b(B\x1b[m Property \x1b(B\x1b[m\x1b[1m"buffer"\x1b(B\x1b[m defined in \x1b(B\x1b[m\x1b[1m"TextIOWrapper"\x1b(B\x1b[m is read-only  \x1b(B\x1b[m\x1b[33m[misc]\x1b(B\x1b[m
src/failprint/capture.py:57: \x1b[1m\x1b[31merror:\x1b(B\x1b[m Incompatible types in assignment (expression has type \x1b(B\x1b[m\x1b[1m"_BytesBuffer"\x1b(B\x1b[m, variable has type \x1b(B\x1b[m\x1b[1m"BinaryIO"\x1b(B\x1b[m)  \x1b(B\x1b[m\x1b[33m[assignment]\x1b(B\x1b[m
src/failprint/capture.py:77: \x1b[1m\x1b[31merror:\x1b(B\x1b[m Argument 1 to \x1b(B\x1b[m\x1b[1m"StringIO"\x1b(B\x1b[m has incompatible type \x1b(B\x1b[m\x1b[1m"StringIO"\x1b(B\x1b[m; expected \x1b(B\x1b[m\x1b[1m"Optional[str]"\x1b(B\x1b[m  \x1b(B\x1b[m\x1b[33m[arg-type]\x1b(B\x1b[m
src/failprint/runners.py:221: \x1b[1m\x1b[31merror:\x1b(B\x1b[m Incompatible return value type (got \x1b(B\x1b[m\x1b[1m"Union[str, int, None]"\x1b(B\x1b[m, expected \x1b(B\x1b[m\x1b[1m"int"\x1b(B\x1b[m)  \x1b(B\x1b[m\x1b[33m[return-value]\x1b(B\x1b[m
\x1b[1m\x1b[31mFound 4 errors in 2 files (checked 18 source files)\x1b(B\x1b[m
```

This is the (ANSI colored) output of mypy.
Other libraries like `ansimarkup` are able to print it.

```python
from ansimarkup import ansiprint
ansiprint('\x1b[31mFound 4 errors in 2 files (checked 18 source files)\x1b(B\x1b[m\n')
```

```python
from rich.text import Text
from rich import print as richprint
richprint(Text.from_ansi('\x1b[31mFound 4 errors in 2 files (checked 18 source files)\x1b(B\x1b[m\n'))
```



Note the trailing `B` in the above screenshot.

**Platform**
<details>
<summary>Click to expand</summary>

What platform (Win/Linux/Mac) are you running on? What term