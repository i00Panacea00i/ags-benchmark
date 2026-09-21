# Requirement pickle drops specifier prereleases

```python
>>> import pickle
>>> from packaging.requirements import Requirement
>>> r = Requirement("foo>=1.0")
>>> r.specifier.prereleases = True
>>> pickle.loads(pickle.dumps(r)).specifier.prereleases is None
True
```

Expected: `loaded.specifier.prereleases == True`.