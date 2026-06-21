# autostart.py
# Enable/disable launching Whisper Local automatically at login. Opt-in: nothing
# here runs unless the user ticks the first-run prompt, the tray "Start on login"
# item, or passes --enable-autostart.
#
# Windows: a value under HKCU\...\CurrentVersion\Run (stdlib winreg, no extra dep,
#          visible in Task Manager → Startup). Launches windowless (pythonw / the
#          GUI-subsystem .exe) so there's no console flash at boot.
# macOS:   a LaunchAgent plist in ~/Library/LaunchAgents.
# Other:   not supported — returns a clear message; the caller falls back to docs.

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_WIN_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_WIN_VALUE_NAME = "WhisperLocal"
_MAC_LABEL = "com.drajb.whisper-local"


def is_supported() -> bool:
    return sys.platform in ("win32", "darwin")


# Build the command Whisper Local should be relaunched with at login. We prefer a
# windowless launch so the user doesn't get a console window every boot.
def _launch_command() -> list:
    exe = sys.executable

    # Running as the standalone pyapp .exe: the executable IS the app launcher.
    if os.environ.get("PYAPP") or getattr(sys, "frozen", False) or exe.lower().endswith("whisper-local.exe"):
        return [exe]

    # pip / source install: relaunch the module with the windowless interpreter
    # (pythonw on Windows) so there's no console window at login.
    if sys.platform == "win32":
        pythonw = Path(exe).with_name("pythonw.exe")
        runner = str(pythonw) if pythonw.exists() else exe
        return [runner, "-m", "whisper_key.main"]
    return [exe, "-m", "whisper_key.main"]


def _win_command_string() -> str:
    # winreg Run values are a single command string; quote each part with spaces.
    parts = _launch_command()
    return " ".join(f'"{p}"' if " " in p else p for p in parts)


# ── Windows (registry Run key) ──

def _win_is_enabled() -> bool:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WIN_RUN_KEY) as key:
            winreg.QueryValueEx(key, _WIN_VALUE_NAME)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def _win_enable() -> bool:
    import winreg
    cmd = _win_command_string()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WIN_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, _WIN_VALUE_NAME, 0, winreg.REG_SZ, cmd)
    logger.info(f"Autostart enabled (Run key): {cmd}")
    return True


def _win_disable() -> bool:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WIN_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _WIN_VALUE_NAME)
    except FileNotFoundError:
        pass
    logger.info("Autostart disabled (Run key removed)")
    return True


# ── macOS (LaunchAgent) ──

def _mac_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{_MAC_LABEL}.plist"


def _mac_is_enabled() -> bool:
    return _mac_plist_path().exists()


def _mac_enable() -> bool:
    from xml.sax.saxutils import escape
    args = _launch_command()
    # Escape &, <, > — a username/path containing them would otherwise produce an
    # invalid plist that launchd silently refuses to load.
    args_xml = "\n".join(f"        <string>{escape(a)}</string>" for a in args)
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        '<dict>\n'
        '    <key>Label</key>\n'
        f'    <string>{_MAC_LABEL}</string>\n'
        '    <key>ProgramArguments</key>\n'
        '    <array>\n'
        f'{args_xml}\n'
        '    </array>\n'
        '    <key>RunAtLoad</key>\n'
        '    <true/>\n'
        '</dict>\n'
        '</plist>\n'
    )
    path = _mac_plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plist, encoding="utf-8")
    logger.info(f"Autostart enabled (LaunchAgent): {path}")
    return True


def _mac_disable() -> bool:
    path = _mac_plist_path()
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    logger.info("Autostart disabled (LaunchAgent removed)")
    return True


# ── public API ──

def is_enabled() -> bool:
    try:
        if sys.platform == "win32":
            return _win_is_enabled()
        if sys.platform == "darwin":
            return _mac_is_enabled()
    except Exception as e:
        logger.debug(f"autostart.is_enabled check failed: {e}")
    return False


# Returns True on success. Never raises — callers surface a friendly message.
def enable() -> bool:
    try:
        if sys.platform == "win32":
            return _win_enable()
        if sys.platform == "darwin":
            return _mac_enable()
        logger.warning("Autostart not supported on this platform")
        return False
    except Exception as e:
        logger.error(f"Failed to enable autostart: {e}")
        return False


def disable() -> bool:
    try:
        if sys.platform == "win32":
            return _win_disable()
        if sys.platform == "darwin":
            return _mac_disable()
        return False
    except Exception as e:
        logger.error(f"Failed to disable autostart: {e}")
        return False


def toggle() -> bool:
    # Returns the achieved state, not the intended one — if enable()/disable()
    # fails (e.g. permissions), the caller sees the truth.
    if is_enabled():
        disable()
        return is_enabled()
    enable()
    return is_enabled()
