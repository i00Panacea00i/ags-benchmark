# 修复亚洲文本换行时字符缺失的问题

**问题描述**  
在使用 `rich` 库的 `Console.print` 方法输出亚洲文本（如中文、日文）时，当文本长度超过控制台宽度，部分字符会在行尾消失而非被正确换行到下一行。该问题与 `rich` 的换行逻辑有关，特别是涉及 `rich/_wrap.py` 和 `rich/cells.py` 中对双宽度字符的处理。用户观察到行末的字符被直接丢弃，导致输出内容不完整。

**示例**  
以下代码在宽度为 20 的控制台中输出：
```python
from rich.console import Console
console = Console(width=20)
console.print("アプリケーションは1670万色を使用でき")
```
当前错误输出（`7` 消失）：
```
アプリケーションは16
0万色を使用でき
```

另一示例：
```python
console.print("TextualはPythonの高速アプリケーション開発フレームワークです")
```
错误输出（末尾 `ムワークです` 消失）：
```
TextualはPy
thonの高速アプリ
ケーション開発フレー
```

**受影响组件**  
- `rich/_wrap.py`：换行算法  
- `rich/cells.py`：单元格宽度计算（需正确处理东亚双宽度字符）  
- `.gitignore`、`CHANGELOG.md` 也可能涉及版本记录调整

**期望行为**  
修复后，上述两个示例应输出完整文本，所有字符均被保留，行末字符正确换行到下一行。例如第一个示例应输出类似：
```
アプリケーションは16
70万色を使用でき
```
第二个示例应输出：
```
TextualはPythonの高
速アプリケーション開
発フレームワークです
```
（具体换行位置可根据双宽度字符规则微调，但不得丢失任何字符。）

**验收标准**  
1. 执行 `console.print("アプリケーションは1670万色を使用でき", width=20)` 时，输出包含全部 16 个字符（含数字和假名），无任何字符被遗漏。  
2. 执行 `console.print("TextualはPythonの高速アプリケーション開発フレームワークです", width=20)` 时，输出包含完整句子，末尾字符不缺失。  
3. 现有相关单元测试（如 `tests/test_cells.py` 中的 `test_chop_cells`、`test_chop_cells_double_width_boundary`、`test_chop_cells_mixed_width`，以及 `tests/test_text.py` 中的 `test_wrap_cjk_mixed`）均通过，不因本次修改而失效。  
4. 修复不破坏其他语言（如英文、韩文）的换行行为。