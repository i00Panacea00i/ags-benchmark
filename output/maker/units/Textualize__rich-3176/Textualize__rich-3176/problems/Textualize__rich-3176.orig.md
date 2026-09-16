# [BUG] Chunks of text go missing when writing Asian text (wrapping issue)

### Description

(Originally reported in Textual: 

When you print Asian text (specifically Chinese and Japanese, which do not use spaces), portions of the text go missing, making it unreadable.

This seems to be related to wrapping, as the characters which go missing are at the end of a line.
Instead of being wrapped on to a new line, they disappear.

There are [rules for wrapping]( in these languages which would take more effort to adhere to, but at the very least, text should not go missing when printed.

### Examples

For example, running the snippet below, the `7` in `1670` disappears:

```python
from rich.console import Console
console = Console(width=20)
console.print("アプリケーションは1670万色を使用でき")
```

Output:

```
アプリケーションは16
0万色を使用でき
```

And in many cases, like those reported in this issue, multiple characters disappear:

```python
from rich.console import Console
console = Console(width=20)
console.print("TextualはPythonの高速アプリケーション開発フレームワークです")
```

Output:

```
TextualはPy
thonの高速アプリ
ケーション開発フレー
```

Notice that many of the characters at the end of the text are completely missing (`ムワークです`).