# File permissions for cache shared between multiple users

## 项目上下文
pypa/pip（Python 项目），涉及模块：news, src, tests。

## 问题描述
### What's the problem this feature will solve?

On a shared Linux system, we want to share pip's cache between multiple users, so packages are not downloaded 50 times when 50 users install the same package.

Currently on unix, when I set the cache directory to a directory which is readable and writable by a group and has the setgid bit set, the cache folders are created with permissions suitable for group-use when I set a correct umask (so, with umask 0002, I get permissions `drwxrwsr-x` on the `http` folder and its subfolders). However, all cache files are only readable and writable by the user who downloaded the file in question last. So, if the same user installs the same package multiple times, everything is nicely cached, but if another user installs the same package, it is not cached.

As far as understand, this happens because [`adjacent_tmp_file` uses `NamedTemporaryFile`]( which has file mode 0o600 hard coded for security reasons, irrespective of the umask.

### Describe the solution you'd like

Ideally, a config option would be added which uses settings suitable for shared caches, something like `cache-shared=True` or `cache-shared-group=my-shared-group-name` or so.

### Alternative Solutions

We could probably run a `chmod` periodically or something like this, but if it doesn't happen within pip itself, there will always be a delay between when the cache is created and when the cache is available for all users.

### Additional context

If the feature was generally welcome, I could also develop a pull request.

### Code of Conduct

- [X] I agree to follow the [PSF Code of Conduct](

## 期望行为
上述缺陷场景应被修复且不引入回归（以仓库测试套件为准）。

## 环境信息
仓库分支基准 commit：420435903ff2。