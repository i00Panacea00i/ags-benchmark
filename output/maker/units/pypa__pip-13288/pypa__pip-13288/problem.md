# 修复 pip 在使用 truststore 与代理时可能使用错误 ssl_context 的问题

启用 truststore 并通过代理安装包时，pip 的 HTTPS 请求可能未对代理连接和目标连接使用同一个 ssl_context，导致证书验证失败。

在 Linux 设置 HTTP_PROXY 和 HTTPS_PROXY，使用 Python 3.10 与 pip 25.0.1 执行 `python -m pip install <package>` 时，会出现：

```
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection broken by 'SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1007)'))': /simple/scipy/
```

将 SSL_CERT_FILE 指向 cacert.pem 可规避，但不是修复。

相关逻辑在 `src/pip/_internal/network/session.py`：truststore 的 ssl_context 传入 `PipSession`；`PipSession` 使用 `HTTPAdapter` 或 `CacheControlAdapter`（缓存与否均触发）。`HTTPAdapter` 由 `_SSLContextAdapterMixin` 与 `requests` 的 `HTTPAdapter` 组合；ssl_context 由构造函数传入，`requests` 的 `HTTPAdapter` 不使用该 kwargs，而由 `_SSLContextAdapterMixin` 保存并在 `init_poolmanager` 时使用。`init_poolmanager` 在 `requests` 构造函数中调用，把 Adapter 的 `self.poolmanager` 初始化为使用上述 ssl_context 的 `urllib3` `PoolManager`。`send` 调用 `get_connection_with_tls_context`，并用 `build_connection_pool_key_attributes` 获取 `pool_kwargs`，该过程使用已构造的 `self.poolmanager`。

问题：通过 HTTPS_PROXY 时，HTTPS 请求有两条 TLS 连接（到代理的一跳和经 CONNECT 隧道到目标主机的一跳）。当前实现未保证两条连接都使用同一个 truststore ssl_context，导致一条回退默认验证并出现 CERTIFICATE_VERIFY_FAILED。

需修改 `src/pip/_internal/network/session.py`，使代理场景下 HTTPS 请求的两条连接（both legs）都使用同一个 ssl_context（即传入 `PipSession` 并由 `_SSLContextAdapterMixin` 保存的 ssl_context），并补充 `news/13465.bugfix.rst` 的 bugfix 条目。

## 验收标准

- 设置 HTTP_PROXY 和 HTTPS_PROXY 且启用 truststore 时，`python -m pip install <package>` 不再出现上述 SSLCertVerificationError / CERTIFICATE_VERIFY_FAILED 重试警告，能正常完成请求与下载。
- 经 HTTPS 代理的 HTTPS 请求中，代理连接（proxy leg）与目标主机连接（tunneled leg）必须使用同一个 ssl_context，不得一条用 truststore ssl_context 而另一条用默认上下文。
- 不设置代理时行为不变；SSL_CERT_FILE 相关行为不受影响。
- 单元测试 `tests/unit/test_network_session.py::TestSSLContextAdapterMixinProxy::test_https_proxy_uses_same_ssl_context_for_both_legs` 通过。
- `news/13465.bugfix.rst` 中存在描述该修复的 bugfix 条目。