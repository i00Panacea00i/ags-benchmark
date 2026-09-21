# 修复 zipapp 中 pip 过时检查错误比较环境内已安装版本的问题

当通过 zipapp（例如 `pip-24.3.1.pyz`、`pip-24.2.pyz`）运行 pip 时，检查 pip 是否过时的版本比较仍然针对环境中已安装的 pip 版本，而不是 zipapp 自身的版本（报告环境：Python 3.13，OS Any）。在通过 `python -m venv .venv` 创建并激活（`source .venv/bin/activate`）的虚拟环境中，使用 `python -m pip list` 可见 pip 24.2；此时执行 `python pip-24.3.1.pyz install attrs -q --dry-run` 会错误输出：
```
[notice] A new release of pip is available: 24.2 -> 24.3.1
[notice] To update, run: pip install --upgrade pip
```
反之，执行 `python pip-24.2.pyz uninstall pip -q -y` 或 `python pip-24.2.pyz install pip -q` 后，再执行 `python pip-24.2.pyz install attrs -q --dry-run`，则不会收到任何过时通知。

预期行为：运行旧版 zipapp 时应提示 zipapp 自身过时；运行与最新发布一致的 zipapp 时不应提示过时，即使环境中存在旧版 pip 或未安装 pip。

涉及文件：`src/pip/_internal/self_outdated_check.py`、`src/pip/_internal/utils/misc.py`、`tests/unit/test_self_check_outdated.py`，以及新闻条目 `news/13084.bugfix.rst`。相关测试标识为 `tests/unit/test_self_check_outdated.py::test_fetch_zipapp_compares_running_version` 和 `tests/unit/test_self_check_outdated.py::test_fetch_zipapp_current_is_silent`。

验收标准（行为级）：
1. 使用 zipapp 运行 pip 时，过时检查必须基于 zipapp 自身的运行版本，而不是环境中已安装的 pip 版本。
2. 当 zipapp 版本低于最新可用版本时，无论环境中是否安装 pip、安装的是旧版还是新版，都应输出过时通知，例如 `[notice] A new release of pip is available: 24.2 -> 24.3.1`，并提示 `[notice] To update, run: pip install --upgrade pip`。
3. 当 zipapp 版本已是最新时，即使环境中存在旧版 pip（如 24.2）或环境中未安装 pip，也不应输出任何过时通知。
4. 行为需在 `tests/unit/test_self_check_outdated.py::test_fetch_zipapp_compares_running_version` 与 `tests/unit/test_self_check_outdated.py::test_fetch_zipapp_current_is_silent` 中通过验证，且不得依赖环境内 pip 的版本信息。