import importlib as _importlib
import platform as _platform

# Resolve the platform once at import time. Whisper Local officially supports
# Windows and macOS; Linux is "best-effort import only" so smoke tests and the
# release toolchain on Linux CI can load most modules without exploding.
_system = _platform.system()
if _system == 'Darwin':
    PLATFORM = 'macos'
elif _system == 'Windows':
    PLATFORM = 'windows'
else:
    PLATFORM = 'unsupported'

IS_MACOS = PLATFORM == 'macos'
IS_WINDOWS = PLATFORM == 'windows'

# The mirrored backend API (see docs/platform-abstraction.md). Every name here
# exists as a module under both macos/ and windows/.
BACKEND_MODULES = ('instance_lock', 'keyboard', 'hotkeys', 'paths', 'app',
                   'permissions', 'icons', 'gpu', 'console', 'foreground')


# Bind `platform.<name>` to this OS's backend on FIRST USE (PEP 562) rather than
# at package import. Importing this package should cost nothing but two booleans:
# config_manager wants only IS_MACOS, and eagerly binding the whole native stack
# (global_hotkeys, Pillow, AppKit) made every lean environment — CI, a partial
# install — die at import instead of at first real use. Four separate one-off
# skipTest patches were paid for that before the cause was traced here.
#
# On an unsupported OS the names stay unresolvable, so code that actually USES
# platform functionality still fails clearly where it matters. Nothing is
# swallowed: a backend whose own dependency is missing raises that dependency's
# ModuleNotFoundError verbatim, naming the package the user has to install.
def __getattr__(name):
    if name in BACKEND_MODULES and PLATFORM != 'unsupported':
        module = _importlib.import_module(f'.{PLATFORM}.{name}', __name__)
        globals()[name] = module  # cache: __getattr__ only fires on a miss
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
