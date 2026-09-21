# pip with truststore and proxy can use incorrect ssl_context

### Description

Disclaimer:
I am not 100% sure if this issue is a bug in pip or rather requests or some other of the vendored library, but I am happy to work together to determine the right location and file the bug there.

Setup:
Linux with `HTTP_PROXY` and `HTTPS_PROXY` set and pip `25.0.1` on Python 3.10.

Issue:
When running `python -m pip install <package>` I receive following error messages:
```
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection broken by 'SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1007)'))': /simple/scipy/
```

Investigations on my side:
When setting `SSL_CERT_FILE` to `cacert.pem` it works.

Not being really happy with this workaround I did a debug session on pip and came up with this trail of events.

The truststore `ssl_context` is constructed here and then passed to the `PipSession`.

Inside the `PipSession` either the `HTTPAdapter` or the `CacheControlAdapter` are used:

For this case consider the no cache case, the issue happens in both cases. The `HTTPAdapter` here is a combination of the `_SSLContextAdapterMixin` in the same file and the request `HTTPAdapter`.  The `ssl_context` is passed in the constructor to this, the requests class does not use this kwargs. It is used in the `_SSLContextAdapterMixin` and stored for later use when `init_poolmanager` is called. 

The `init_poolmanger` is called from `requests` in the constructor:

This set up `self.poolmanager` of the Adapter to a poolmanager that will use the `ssl_context`. This is done by saving it ìnside the `urllib3` `PoolManager` see here:

When this adapter is used in `send` it will call `get_connection_with_tls_context`

Now we are approaching the issue location when in this location we use `build_connection_pool_key_attributes` to get the `pool_kwargs`. This will use the `self.poolmanager` (that was constructed before) in