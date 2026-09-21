# cache uses filenames that might be too long on some systems

## 项目上下文
psf/black（Python 项目），涉及模块：CHANGES.md, src, tests。

## 问题描述
**Describe the bug**

Running black 24.1.0 (without --check) can produce filenames in user's cache folder that are too long for some filesystems e.g. eCryptFS only allows filenames that are 143 chars long

The resulting error is:

```
Traceback (most recent call last):
  File "/home/hottwaj/.pyenv/versions/3.10.2/envs/test-venv/bin/black", line 8, in <module>
    sys.exit(patched_main())
  File "src/black/__init__.py", line 1593, in patched_main
  File "/home/hottwaj/.pyenv/versions/3.10.2/envs/test-venv/lib/python3.10/site-packages/click/core.py", line 1130, in __call__
    return self.main(*args, **kwargs)
  File "/home/hottwaj/.pyenv/versions/3.10.2/envs/test-venv/lib/python3.10/site-packages/click/core.py", line 1055, in main
    rv = self.invoke(ctx)
  File "/home/hottwaj/.pyenv/versions/3.10.2/envs/test-venv/lib/python3.10/site-packages/click/core.py", line 1404, in invoke
    return ctx.invoke(self.callback, **ctx.params)
  File "/home/hottwaj/.pyenv/versions/3.10.2/envs/test-venv/lib/python3.10/site-packages/click/core.py", line 760, in invoke
    return __callback(*args, **kwargs)
  File "/home/hottwaj/.pyenv/versions/3.10.2/envs/test-venv/lib/python3.10/site-packages/click/decorators.py", line 26, in new_func
    return f(get_current_context(), *args, **kwargs)
  File "src/black/__init__.py", line 703, in main
  File "/home/hottwaj/.pyenv/versions/3.10.2/envs/test-venv/lib/python3.10/site-packages/black/concurrency.py", line 101, in reformat_many
    loop.run_until_complete(
  File "/home/hottwaj/.pyenv/versions/3.10.2/lib/python3.10/asyncio/base_events.py", line 641, in run_until_complete
    return future.result()
  File "/home/hottwaj/.pyenv/versions/3.10.2/envs/test-venv/lib/python3.10/site-packages/black/concurrency.py", line 137, in schedule_formatting
    cache = Cache.read(mode)
  File "src/black/cache.py", line 67, in read
  File "/home/hottwaj/.pyenv/versions/3.10.2/lib/python3.10/pathlib.py", line 1288, in exists
  

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：659c29a41c7c。