# 任务描述

在 `psf/requests` 仓库中，处理 URL 时存在一个错误：当 URI 中斜杠后紧跟冒号（例如 `'http://v:h'`）会导致请求失败，抛出 `urllib3.exceptions.LocationParseError` 异常。该异常源于 `urllib3` 的 `url.py` 中 `_HOST_PORT_RE.match` 无法正确匹配 `host_port` 内容，最终在 `connectionpool.py` 的 `urlopen` 调用 `parse_url` 时通过 `source_url` 抛出 `LocationParseError: Failed to parse: //v:h`。

错误调用链为：用户调用 `requests.get(url)` 进入 `api.py` 的 `request` 函数，接着在 `sessions.py` 中执行 `self.send(prep, **send_kwargs)`，最终由 `adapter.send` 在 `adapters.py` 中发起连接。`adapter.send` 内部调用 `conn.urlopen` 触发 `connectionpool.py` 中的 `parsed_url = parse_url(url)`，进而导致解析失败。

**期望行为**：当 URL 包含类似 `'http://v:h'` 的格式（即路径或主机部分出现“斜杠后跟冒号”的模式）时，`requests.get` 应能正常返回响应（例如 `<Response [200]>`），而不抛出 `urllib3.exceptions.LocationParseError` 异常。

**验收标准**（满足任一即算修复）：
1. 执行 `requests.get('` 后成功返回状态码 200 的响应对象，无异常抛出。
2. 所有形如 `'http://<some-string>:<non-numeric-string>'` 的 URL 均不再触发 `urllib3.exceptions.LocationParseError`，而是被合法处理（例如作为有效主机/路径处理）。

**涉及文件**：`src/requests/adapters.py`、`src/requests/sessions.py`、`src/requests/api.py` 以及 `urllib3` 的 `connectionpool.py`、`url.py`。需在 `adapters.py` 或上游逻辑中处理此类畸形 URL 的传入，确保 `host_port` 能被正确解析或绕过。