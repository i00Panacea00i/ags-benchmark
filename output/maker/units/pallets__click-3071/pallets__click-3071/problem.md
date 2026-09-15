# 编程任务描述

在 Click 库（版本 8.3.0）中，当使用多个 `@click.option` 装饰器共享同一个参数名（例如 `color`），并利用 `flag_value` 定义特性标志（feature flags）时，如果其中一个选项设置了 `default=True`，则该默认值的行为会依赖于选项在代码中声明的顺序，而非符合预期的固定行为。

例如，给定如下定义：

```python
@click.command()
@click.option("--red",   "color", flag_value="red")
@click.option("--green", "color", flag_value="green", default=True)
@click.option("--blue",  "color", flag_value="blue")
def main(color: str) -> None:
    print(repr(color))
```

在 Click 8.2.1 中，不传入任何参数运行时输出 `'green'`，这是正确的行为——`default=True` 的选项对应的 `flag_value` 应作为默认值被采用。但在 Click 8.3.0 中，上述代码输出 `None`；若将 `--green` 选项移到 `--red` 之前（即声明顺序改变），则 Click 8.3.0 又会输出 `'green'`。

**预期行为**：无论 `--red`、`--green`、`--blue` 三个选项在代码中的声明顺序如何，当用户不提供任何命令行参数时，程序应始终输出 `'green'`。即 `default=True` 的选项应优先提供其 `flag_value` 作为默认值，而不受其他同参数名选项的位置影响。

**验收标准**：
- 使用上述代码（或任意三个共享 `color` 参数名的选项，其中仅一个设置 `default=True`），运行时不传入任何参数，输出恒为 `'green'`。
- 改变选项的声明顺序（例如将 `--green` 放在 `--red` 之前或之后），输出仍为 `'green'`，不会变为 `None` 或其他值。
- 仅通过 `click` 库的正常接口行为验证，不依赖内部实现细节。