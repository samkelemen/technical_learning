# `beartype`

## Enabling beartype
### Enabling for a repo / directory
Place these two lines at the beginning of `__init__.py`
```
from beartype.claw import beartype_this_package

beartype_this_package()
```

