# [Bug] On Windows, get_pager_file returns a typing.BinaryIO object NOT typing.TextIO

Inside `src/click/_termui_impl.py`, the function `get_pager_file` delegates the creation of a tempfile to `_tempfilepager`, which returns a `BinaryIO` object of the opened file:

```python
f = tempfile.NamedTemporaryFile(mode="wb", delete=False)
try:
    yield t.cast(t.BinaryIO, f), encoding, color
...
```
Which is called by _pager_contextmanager in
```python
...
if pager_cmd_parts:
        if WIN:
            return _tempfilepager(pager_cmd_parts, color)
        return _pipepager(pager_cmd_parts, color)
...
    if WIN or sys.platform.startswith("os2"):
        return _tempfilepager(["more"], color)
    return _pipepager(["less"], color)
```
In the end `get_pager_file`
```python
def get_pager_file(color: bool | None = None) -> t.Generator[t.TextIO, None, None]:
    ...
    with _pager_contextmanager(color=color) as (stream, encoding, color):
    # Split streams by capabilities rather than the abstract TextIO /
    # BinaryIO annotations: buffered text streams can be unwrapped to bytes,
    # while other streams are yielded as-is.
    wrapper: MaybeStripAnsi | None = None
        if _has_binary_buffer(stream):
            # Text stream backed by a binary buffer.
            wrapper = MaybeStripAnsi(stream.buffer, color=color, encoding=encoding)
            stream = wrapper
        try:
            # Narrow the BinaryIO | TextIO union that _pager_contextmanager
            # yields; the caller writes text to the pager.
            yield t.cast(t.TextIO, stream)
        ...
```
In the above `yield t.cast(t.TextIO, stream)` stream object will be `BinaryIO`, contradicting the `TextIO` annotation of the return value, all because it was created with the mode `"wb"` earlier.

Then if a caller tries: `stream.write("some text")` it will raise an exception:
`TypeError: a bytes-like object is required, not 'str'`

FIX:
In `_tempfilepager`, create the temp file with `mode='w'`
```python
f = tempfile.NamedTemporaryFile(mode="w", delete=False)
```
I went ahead and created a pull r