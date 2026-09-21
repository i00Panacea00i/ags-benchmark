# Zipapp: pip outdated check compares against version installed in the environment and not the version in the zipapp

### Description

When running pip via the zipapp the version comparison for checking if pip is outdated is still done against pip installed in the environment.

This means you get a notification that pip is outdated when using an up to date zipapp if an older pip is installed in the venv. Also if you're using an outdated zipapp, but either pip in the venv is up to date or it is not installed you aren't notified that pip is outdated.

### Expected behavior

I'd expect to see a notification that the zipapp is outdated if running an old zipapp and no notification if the zipapp is up to date, even if there's an old version of pip installed in the environment.

### pip version

24.3.1

### Python version

3.13

### OS

Any

### How to Reproduce

1. Download the zipapps for 24.3.1 and 24.2 - 
2. Create a new venv with pip 24.2
3. Use the latest zipapp to install a package eg: `python pip-24.3.1.pyz install attrs -q --dry-run`
4. Outdated notice at the end
5. Uninstall pip from the env - `python pip-24.2.pyz uninstall pip -q -y`
6. Run the install command again, but using the older zipapp `python pip-24.2.pyz install attrs -q --dry-run`
7. No outdated notice
8. Install an up-to-date version of pip in the environment: `python pip-24.2.pyz install pip -q`
9. Run the install command yet again, still using the older zipapp `python pip-24.2.pyz install attrs -q --dry-run`
10. No outdated notice

### Output

On Linux, change the venv activation for Windows but it should otherwise be the same.

```bash
$ python -m venv .venv
$ source .venv/bin/activate

$ python -m pip list
Package Version
------- -------
pip     24.2

$ python pip-24.3.1.pyz install attrs -q --dry-run

[notice] A new release of pip is available: 24.2 -> 24.3.1
[notice] To update, run: pip install --upgrade pip

$ python pip-24.2.pyz uninstall pip -q -y
$ python pip-24.2.pyz install attrs -q --dry-run

$ python pip-24.2.pyz install pip -q
$ python pip-24.2.pyz install attrs -q --dry