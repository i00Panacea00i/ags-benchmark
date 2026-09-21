# 修复 `click.progressbar` 在 `show_pos=True` 与 `update_min_steps` 组合下未显示完整完成状态

在 Click 中，当 `click.progressbar` 同时设置 `show_pos=True` 且 `update_min_steps` 不是 `length` 的约数时，进度条结束（迭代完成或最后一次 `update` 调用后）不会显示完整完成位置，而是停留在最后一次中间更新值。

复现示例：

```python
import time

import click

with click.progressbar(
    range(20),
    show_pos=True,
    update_min_steps=7,
) as bar:
    for i in bar:
        time.sleep(0.1)
```

最终输出为：

```text
  [####################################]  14/20          
```

期望行为是最终显示 `20/20`；这与默认百分比格式一致，注释掉 `show_pos=True` 后最终输出为 `100%`。

需要修改 `src/click/_termui_impl.py` 中的进度条更新与渲染逻辑，并在 `CHANGES.md` 中记录变更；相关测试位于 `tests/test_termui.py`。

行为级验收标准：

1. 通过迭代方式（如 `for i in bar`）消费 `click.progressbar`，且 `show_pos=True`、`update_min_steps` 取 3、7、25 等非 `length` 约数时，最终渲染文本中的位置信息必须为 `length/length`（如 `20/20`），不得停留在 `14/20` 等中间值。
2. 通过手动调用 `update` 方式推进进度条，且 `show_pos=True`、`update_min_steps` 取 3、7、25 时，最终渲染文本中的位置信息同样必须为 `length/length`。
3. 关闭 `show_pos=True` 时，最终百分比仍为 `100%`，且其他进度条行为不被破坏。
4. 参数化测试 `tests/test_termui.py::test_progressbar_lands_on_final_position[iterate-25]`、`tests/test_termui.py::test_progressbar_lands_on_final_position[iterate-3]`、`tests/test_termui.py::test_progressbar_lands_on_final_position[iterate-7]`、`tests/test_termui.py::test_progressbar_lands_on_final_position[update-25]`、`tests/test_termui.py::test_progressbar_lands_on_final_position[update-3]`、`tests/test_termui.py::test_progressbar_lands_on_final_position[update-7]` 全部通过。