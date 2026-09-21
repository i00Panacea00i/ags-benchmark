# Provide a way to get just pure Python tags

`packaging.tags.compatible_tags()` doesn't provide a way to ignore the `platform` argument such that you only get `py*-none-any` tags. Probably need a `pure_python_tags()`, `python_only_tags()`, or something.