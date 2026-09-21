# Allow customizing fail message for invalid choice in `click.types.Choice`

## 项目上下文
pallets/click（Python 项目），涉及模块：CHANGES.rst, docs, src, tests。

## 问题描述
Move the fail art of `convert()` in the `Choice` class to a new method `get_invalid_choice_fail_message(self)` so in my subclass of `click.Choice` I can customize the way it shows the failing value for the choice

Some CLI option choices are multi-part meaning they are separated by some value, like a comma separated list for example. Maybe each section of this value represents a different part of a schema and it is nice to show a custom message about the specific part.

Contrived version:
Let says my choices are `["maine::goat", "maine::themepark"]` and I give it "maine::toast"`, it'd be nice to say the `maine` part was correct and the `toast` part was not.

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：1787497713fa。