# Force Exclude does not work with symlinks

## 项目上下文
psf/black（Python 项目），涉及模块：CHANGES.md, src, tests。

## 问题描述
**Describe the bug**
I use the `force-exclude` feature to exclude files living in symlinked directories.
However, it looks like `black` uses the regexp from `force-exclude` **after** the symlink is resolved (not the symlinked path).

```
$ black -v /path_2_file/application/api/lib/dir_symlinked/__init__.py
Identified `/path_2_file` as project root containing a .git directory.
Using configuration from project root.
line_length: 135
target_version: ['py39']
force_exclude: (?:.*?application/api(?:-ext)?/lib/dir_symlinked/.+)

skip_string_normalization: True
Found input source: "application/lib/ref_dir/__init__.py"
/path_2_file/application/api/lib/dir_symlinked/__init__.py wasn't modified on disk since last run.

All done! ✨ 🍰 ✨
1 file left unchanged.
```

The resulting error is:

It should have ignored the file based on this path `/path_2_file/application/api/lib/dir_symlinked/__init__.py` rather than including it based on this path `application/lib/ref_dir/__init__.py`.
Said differently it used the resolved/resulting path rather than the path through the symlink

**Environment**

- Black's version: 23.7.0
- OS and Python version: MacOS Ventura 13.4.1, Python 3.9.12, 

**Additional context**

I would be equally happy if I could simply tell `black` **not** to follow symlinks.

Thank you in advance for your help!

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：e2f2bd076fbc。