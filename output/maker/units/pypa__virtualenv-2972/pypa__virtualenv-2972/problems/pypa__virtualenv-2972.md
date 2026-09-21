# cache issue: virtualenv 20.35.0 breaks hatch 1.14.2

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：docs, src, tests。

## 问题描述
**Issue**
When hatch [here]( calls 
```
virtualenv_discovery.get_interpreter(
                python_version, (), env=envs
            )
```
it doesn't set `cache` argument, which leads to this [place]( to fail (was added in this [pr]( Originally there was a check:
```
if cache is None:
        if app_data is None:
            app_data = AppDataDisabled()
        cache = FileCache(store_factory=app_data.py_info, clearer=app_data.py_info_clear)
```
but it was removed in this [PR](

**Environment**
virtualenv 20.35.0
hatch 1.14.2
Provide at least:

- OS: Macos 15.7
- Shell: zsh
- Python version and path:
- `pip list` of the host python where `virtualenv` is installed:

  ```console

  ```

**Output of the virtual environment creation**

Make sure to run the creation with `-vvv --with-traceback`:

```console

```

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：8e1ecc705a50。