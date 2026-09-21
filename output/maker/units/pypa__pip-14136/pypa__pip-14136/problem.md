# Option errors print usage with Rich markup unrendered

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
### Description

Any option-parsing error prints the usage block with the Rich markup unrendered.

`[optparse.groups]Usage:[/]` and `\[options]` show literally. Happens on every command's error path; normal output is unaffected.

Not in 25.3, appears in 26.0. 

possibly related to #13649.

### Expected behavior

Usage rendered (or plain), same as `--help`.

### pip version

26.0~26.1.2 and main

### Python version

3.14

### OS

macOS (any)

### How to Reproduce

```bash
pip install --hi        # < - - - - wrong option
pip help --wrong-option # < - - - - wrong option
```

### Output

```bsah
$ pip install --hi
[optparse.groups]Usage:[/]
  pip install \[options] <requirement specifier> \[package-index-options] ...
  pip install \[options] -r <requirements file> \[package-index-options] ...
  ...
no such option: --hi

$ pip help --wrong-option
[optparse.groups]Usage:[/]
  pip help <command>

no such option: --wrong-option
```

### Code of Conduct

- [x] I agree to follow the [PSF Code of Conduct](

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：6989a79f97a4。