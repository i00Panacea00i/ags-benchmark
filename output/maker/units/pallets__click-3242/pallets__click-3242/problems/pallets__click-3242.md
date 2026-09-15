# 任务：修复 `click.echo_via_pager` 的 stdin 刷新问题

## 问题描述
在 `click` 库中，`click.echo_via_pager` 函数用于将文本通过分页器（如 `less`）显示。当前实现中，当传入一个生成器（generator）作为输入时，分页器不会立即显示每次 `yield` 的内容，而是等待缓冲区填满（约 512 行）后才一次性输出。这导致实时性要求高的场景（如逐行输出进度）体验极差。

## 复现场景
以下代码演示了该问题：

```python
import click
import os
import time

def _generator():
    for i in range(10000):
        time.sleep(0.01)
        yield f"{i+1:07}\n"

@click.command()
def main():
    os.environ.setdefault("LESS", "-XFR")
    click.echo_via_pager(_generator())

main()
```

运行时，用户无法在分页器中看到逐行更新的数字，而必须等待约 512 行生成后才突然显示一批。

## 预期行为
`click.echo_via_pager` 应在每次向分页器的标准输入（stdin）写入数据后立即执行 `flush` 操作，确保分页器能实时读取并显示每一条内容。即：生成器每次 `yield` 的数据应立刻出现在分页器中，不依赖缓冲区大小。

## 修改范围
- 主要修改文件：`src/click/termui.py` 中 `echo_via_pager` 函数的实现。
- 确保现有测试 `tests/test_termui.py::test_echo_via_pager_streams_each_write` 仍能通过。

## 验收标准
1. **实时可见性**：使用上述示例代码运行时，分页器中应每秒约显示 100 行（与 `time.sleep(0.01)` 对应），而不是等待 512 行后才出现第一批内容。
2. **兼容性**：所有已有的 `echo_via_pager` 相关测试（包括 `test_echo_via_pager_streams_each_write`）保持通过。
3. **不引入副作用**：对于非生成器输入（如字符串或列表），行为不应改变；对于普通分页器调用（如不使用 `LESS` 环境变量），修复后不应导致崩溃或性能异常。

## 备注
- 请勿修改 `CHANGES.rst` 和测试文件，只关注实现代码。
- 不依赖任何外部库或复杂 `flush` 策略，仅确保每次 `write` 后对要写入的流（`sys.stdin` ？实际上是分页器的输入管道）执行 `flush`。注意：分页器通常通过管道读取，需刷新的是写入端（即写入分页器 stdin 的流）。