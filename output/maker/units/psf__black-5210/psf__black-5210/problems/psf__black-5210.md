# Invalid BLACK_NUM_WORKERS value can produce a raw ValueError traceback

## 项目上下文
psf/black（Python 项目），涉及模块：CHANGES.md, src, tests。

## 问题描述
### Summary

`BLACK_NUM_WORKERS` is documented in the `--workers` help as an alternate way to configure the same worker-count setting, but invalid environment variable values bypass the Click validation used by `--workers` and can produce a raw traceback.

### Reproduction

```bash
mkdir -p /tmp/black-workers-repro
printf 'x=1\n' >/tmp/black-workers-repro/a.py
printf 'y=2\n' >/tmp/black-workers-repro/b.py

BLACK_NUM_WORKERS=abc python -m black --check /tmp/black-workers-repro
```

### Actual behavior

The command fails with a Python traceback ending in:

```text
ValueError: invalid literal for int() with base 10: 'abc'
```

### Expected behavior

Since this is the environment-variable form of the same `workers` setting, invalid values should be reported as a user-facing configuration/parameter error rather than an internal traceback. For example, it could say that `BLACK_NUM_WORKERS` must be an integer greater than or equal to 1.

If the intended product semantics are that `BLACK_NUM_WORKERS` is only a best-effort low-level override and not equivalent to `--workers`, it may be worth documenting that explicitly; otherwise the help text currently suggests they share the same contract.

### Source of the mismatch

The CLI option is validated by Click as an integer range:

```python
.option(
    "-W",
    "--workers",
    type=click.IntRange(min=1),
    default=None,
    help=(
        "When Black formats multiple files, it may use a process pool to speed up"
        " formatting. This option controls the number of parallel workers. This can"
        " also be specified via the BLACK_NUM_WORKERS environment variable. Defaults"
        " to the number of CPUs in the system."
    ),
)
```

But the environment variable path parses the value directly:

```python
if workers is None:
    workers = int(os.environ.get("BLACK_NUM_WORKERS", 0))
    workers = workers or os.cpu_count() or 1
```

As a result, `--workers abc` is handled by Click's validation layer, while `BLACK_NUM_W

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：56ba38a484da。