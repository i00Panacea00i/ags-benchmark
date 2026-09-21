# Need an escape hatch for corrupted cache.

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
### Description

If the pip wheel_cache json file is corrupted, users get a confusing error and there does not seem to be a recovery mode other than finding and removing the cache.

`pip cache purge` does not resolve such a problem.

It is not completely clear how the file became corrupted in this case, but it may have been related to an instance of a disk quota being exceeded.

### Expected behavior

* The JSON decoder exception should be caught.
* Either `pip` should automatically remove / regenerate the cache data file or `pip` should advise the user on how to proceed.

In this case, the exception propagated from `pip/_internal/cache.py::WheelCache.record_download_origin()`, which called `DirectUrl.from_json()`. Letting the  JSONDecoderError propagate through `DirectUrl.from_json()` seems appropriate. It also seems reasonable to let it propagate through `WheelCache.record_download_origin()`.

I think one of the following would be an appropriate place for additional error handling.
* `pip/_internal/wheel_builder.py::build()` produces a `build_failures` list, but does not catch exceptions for conversion to "build_failures".
* `pip/_internal/commands/install.py::InstallCommand.run()` calls `build` in a `try` block, but only OSError is caught.

It also seems reasonable that `pip cache purge` could reinitialize state files more completely.

### pip version

main, as of 20 April 2023

### Python version

all

### OS

all

### How to Reproduce

`pip install` a package from a source distribution, producing a cachable "wheel", but with invalid JSON files in the pip cache.

### Output

```
Building wheels for collected packages: ...
  Stored in directory: /.../.cache/pip/wheels/e4/50/f2/fddc95515d81964ea105d53c75210d0c94388d80faf5e0b797
ERROR: Exception:
Traceback (most recent call last):
  File "/.../lib/python3.9/site-packages/pip/_internal/cli/base_command.py", line 169, in exc_logging_wrapper
    status = run_func(*args)
  

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：b0a8317ffbcc。