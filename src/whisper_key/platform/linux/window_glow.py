# window_glow.py (Linux)
# Backend for the WindowGlow indicator. A helper process draws the glow
# (glow_helper.py): it needs GTK 4 with layer-shell, and the tray icon has
# already loaded GTK 3 into this process, which can't hold both. This module
# starts the helper with libgtk4-layer-shell preloaded (it has to load before
# libwayland-client) and sends it one short command per frame on its stdin.

import ctypes.util
import logging
import os
import subprocess
import threading
import time

from ...utils import python_module_command
from . import glow_shape, hyprland

logger = logging.getLogger(__name__)

_HELPER_MODULE = 'whisper_key.platform.linux.glow_helper'
_MAX_STARTS = 3          # a helper that keeps dying is given up on for the session
_RESTART_DELAY_S = 5.0   # and is not restarted more often than this

_lock = threading.Lock()
_process = None
_starts = 0
_last_start = 0.0
_layer_shell = None      # library name, looked up once


def _layer_shell_library() -> str:
    global _layer_shell
    if _layer_shell is None:
        _layer_shell = ctypes.util.find_library('gtk4-layer-shell') or ''
    return _layer_shell


def is_supported() -> bool:
    return hyprland.is_available() and bool(_layer_shell_library())


def _helper_command():
    return python_module_command(_HELPER_MODULE)


# ---------------------------------------------------------------------------
# Helper process (callers hold _lock)
# ---------------------------------------------------------------------------

def _running() -> bool:
    return _process is not None and _process.poll() is None


def _spawn():
    global _process, _starts, _last_start
    env = dict(os.environ)
    env['LD_PRELOAD'] = ' '.join(filter(None, (_layer_shell_library(), env.get('LD_PRELOAD'))))
    _starts += 1
    _last_start = time.monotonic()
    _process = subprocess.Popen(_helper_command(), stdin=subprocess.PIPE, env=env)
    # Never block a frame on a busy helper: a full pipe drops the frame instead.
    os.set_blocking(_process.stdin.fileno(), False)


# Starts the helper if it isn't running, unless it has died too often.
def _ensure_running() -> bool:
    if _running():
        return True
    if _process is not None:  # it was running and has died
        if _starts >= _MAX_STARTS:
            return False
        if time.monotonic() - _last_start < _RESTART_DELAY_S:
            return False
        logger.warning(f"Window glow helper exited ({_process.returncode}); restarting it")
    _spawn()
    return True


def _send(state: str, level: float = 0.0):
    with _lock:
        if not _ensure_running():
            return
        try:
            # Under PIPE_BUF bytes, so the write is all or nothing.
            os.write(_process.stdin.fileno(), glow_shape.format_command(state, level).encode('ascii'))
        except BlockingIOError:
            pass  # the helper is behind; the next frame catches up
        except OSError as e:
            logger.debug(f"Window glow helper unreachable: {e}")


# ---------------------------------------------------------------------------
# Backend API
# ---------------------------------------------------------------------------

def start():
    with _lock:
        _ensure_running()


# state: "recording", "processing", "success" or "failure"; level: 0 to 1.
def show(state: str, level: float = 0.0):
    _send(state, level)


def clear():
    with _lock:
        if not _running():
            return
    _send('hide')


# Closing stdin tells the helper to exit.
def stop():
    global _process
    with _lock:
        process, _process = _process, None
    if process is None:
        return
    try:
        process.stdin.close()
        process.wait(timeout=1.0)
    except (OSError, subprocess.TimeoutExpired):
        process.kill()
