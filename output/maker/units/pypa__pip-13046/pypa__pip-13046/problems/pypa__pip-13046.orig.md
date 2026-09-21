# pip mistakenly reports recursion error even when there is no recursion

### Description

I have three requirements files, as follows:

```
# requirements.txt
...
```
```
# test-requirements.txt
-r requirements.txt
...
```
```
# lint-requirements.txt
-r requirements.txt
-r test-requirements.txt
...
```
When attempting to `pip install -r lint-requirements.txt`, pip complains:
```console
ERROR: .../requirements.txt recursively references itself in .../test-requirements.txt and again in .../lint-requirements.txt
```
even though there is no recursive reference here. This used to work fine prior to pip 24.3.

### Expected behavior

pip should not report an error and instead should proceed with installation as usual.

### pip version

24.3

### Python version

3.9

### OS

Linux

### How to Reproduce

1. Place three example requirements files in a directory as above.
2. Run `pip install -r lint-requirements.txt`
3. Observe error.

### Output

```console
$ python3.9 -m pip install -r lint-requirements.txt -c constraints.txt
Defaulting to user installation because normal site-packages is not writeable
ERROR: <omitted>/requirements.txt recursively references itself in <omitted>/test-requirements.txt and again in <omitted>/lint-requirements.txt
```

### Code of Conduct

- [X] I agree to follow the [PSF Code of Conduct](