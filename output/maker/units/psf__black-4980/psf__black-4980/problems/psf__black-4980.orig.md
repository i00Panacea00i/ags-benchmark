# Internal error when targeting Python 3.14 but running with 3.12

**Describe the bug**

Running Black with Python 3.12 but targeting Python 3.14 on a file containing an `except` clause with multiple parenthesized exception types fails with an internal error.

**To Reproduce**

These steps:
```sh
python3.12 -m venv venv
source venv/bin/activate
pip install black
printf "%s\n" 'try:' ' 1 / 0' 'except (a, b):' ' pass' >test.py
black -t py314 test.py
```

result in this error:
```text
error: cannot format test.py: INTERNAL ERROR:
Black 26.1.0 on Python (CPython) 3.12.11 produced invalid code:
multiple exception types must be parenthesized (<unknown>, line 3).
Please report a bug on 
This invalid output might be helpful: /tmp/blk_t6kdrgtk.log

Oh no! 💥 💔 💥
1 file failed to reformat.
```

**Expected behavior**

No internal error (even if that means `--fast` has to be implied when targeting a different Python version?)

**Environment**

- Black's version: 26.1.0
- OS and Python version: Linux, Python 3.12.11