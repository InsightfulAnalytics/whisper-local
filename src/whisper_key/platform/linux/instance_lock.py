# instance_lock.py (Linux)
# Single-instance guard: an exclusive flock on a file in the user's runtime
# directory. The kernel drops the lock when the process dies, so a crash never
# leaves a stale lock behind.

import fcntl
import os
from pathlib import Path

_lock_file = None


def _lock_path(app_name: str) -> Path:
    runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
    base = Path(runtime_dir) if runtime_dir else Path.home()
    return base / f".{app_name}.lock"


def acquire_lock(app_name: str):
    global _lock_file
    try:
        _lock_file = open(_lock_path(app_name), 'w')
        fcntl.flock(_lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_file.write(str(os.getpid()))
        _lock_file.flush()
        return _lock_file
    except OSError:
        if _lock_file:
            _lock_file.close()
            _lock_file = None
        return None


def release_lock(handle):
    global _lock_file
    if handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
        except OSError:
            pass
    _lock_file = None
