# NameError: name '_DISTUTILS_PATCH' is not defined

## 项目上下文
pypa/virtualenv（Python 项目），涉及模块：docs, src, tests。

## 问题描述
**Issue**

I'm using `uv` and initialized my venv with `uv venv`, I'm not sure I should report here or in uv.

I'm using a marimo notebook, and I occasionally run into this error:

```
Process Process-1:
Traceback (most recent call last):
  File "/nix/store/zsbkvanzzx4dd5va9ivsx83rs12d4dsv-python3-3.12.11/lib/python3.12/multiprocessing/process.py", line 314, in _bootstrap
    self.run()
  File "/nix/store/zsbkvanzzx4dd5va9ivsx83rs12d4dsv-python3-3.12.11/lib/python3.12/multiprocessing/process.py", line 108, in run
    self._target(*self._args, **self._kwargs)
  File "/.../.venv/lib/python3.12/site-packages/marimo/_runtime/runtime.py", line 3071, in launch_kernel
    asyncio.run(control_loop(kernel))
  File "/nix/store/zsbkvanzzx4dd5va9ivsx83rs12d4dsv-python3-3.12.11/lib/python3.12/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/nix/store/zsbkvanzzx4dd5va9ivsx83rs12d4dsv-python3-3.12.11/lib/python3.12/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/nix/store/zsbkvanzzx4dd5va9ivsx83rs12d4dsv-python3-3.12.11/lib/python3.12/asyncio/base_events.py", line 691, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/.../.venv/lib/python3.12/site-packages/marimo/_runtime/runtime.py", line 3065, in control_loop
    await kernel.handle_message(request)
  File "/.../.venv/lib/python3.12/site-packages/marimo/_runtime/runtime.py", line 2257, in handle_message
    await self.request_handler.handle(request)
  File "/.../.venv/lib/python3.12/site-packages/marimo/_runtime/runtime.py", line 2878, in handle
    return await handler(request)
           ^^^^^^^^^^^^^^^^^^^^^^
  File "/.../.venv/lib/python3.12/site-packages/marimo/_runtime/runtime.py", line 2139, in handle_execute_multiple
    await self.run(request.execution_requests)
  File "/.../.venv/lib/python3.12/site-packages/marimo/_runtime/runtime.py", lin

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：e9fd90db8fca。