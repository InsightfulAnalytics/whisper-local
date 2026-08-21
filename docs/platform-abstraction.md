## Structure

```
platform/
├── __init__.py        # sets `IS_MACOS` / `IS_WINDOWS`; resolves backends lazily
└── {macos,windows}/
    ├── assets/        # platform-specific assets
    └── *.py           # modules (mirrored API)
```

Module Contract:
- Mirrored with identical API (no-ops OK)
- Listed in `BACKEND_MODULES` in `__init__.py` — resolved on first use, not at package import
- No-op stubs are valid when a platform doesn't need the functionality 

## Usage

```python
from .platform import keyboard, hotkeys, app, paths, icons  # prefer
from .platform import IS_MACOS, IS_WINDOWS  # sparingly
```
