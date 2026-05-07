import logging
import os
import signal
import sys
import time
from pathlib import Path

from .platform import instance_lock
from .utils import get_user_app_data_path

logger = logging.getLogger(__name__)

_LOCK_RETRY_TIMEOUT = 5.0
_LOCK_RETRY_INTERVAL = 0.1


def _pid_file(app_name: str) -> Path:
    return Path(get_user_app_data_path()) / f"{app_name}.pid"


def _read_existing_pid(app_name: str):
    path = _pid_file(app_name)
    if not path.exists():
        return None
    try:
        return int(path.read_text().strip())
    except (ValueError, OSError):
        return None


def _write_pid(app_name: str):
    try:
        _pid_file(app_name).write_text(str(os.getpid()))
    except OSError as e:
        logger.warning(f"Could not write pid file: {e}")


def _terminate(pid: int) -> bool:
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except (ProcessLookupError, PermissionError, OSError) as e:
        logger.warning(f"Could not terminate PID {pid}: {e}")
        return False


def _wait_for_lock(app_name: str):
    deadline = time.monotonic() + _LOCK_RETRY_TIMEOUT
    while time.monotonic() < deadline:
        time.sleep(_LOCK_RETRY_INTERVAL)
        handle = instance_lock.acquire_lock(app_name)
        if handle is not None:
            return handle
    return None


def guard_against_multiple_instances(app_name: str = "WhisperKeyLocal"):
    try:
        handle = instance_lock.acquire_lock(app_name)

        if handle is None:
            existing_pid = _read_existing_pid(app_name)
            if existing_pid:
                print(f"\nWhisper Local already running (PID {existing_pid}); replacing it...")
                _terminate(existing_pid)
            else:
                print("\nWhisper Local lock held by unknown process; waiting...")

            handle = _wait_for_lock(app_name)
            if handle is None:
                _fail_takeover()

            print("Lock acquired. Continuing startup.\n")

        logger.info("Primary instance acquired mutex")
        _write_pid(app_name)
        return handle

    except Exception as e:
        logger.error(f"Error with single instance check: {e}")
        raise


def cleanup_pid_file(app_name: str = "WhisperKeyLocal"):
    try:
        path = _pid_file(app_name)
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _fail_takeover():
    print("\nCould not acquire lock — an unresponsive Whisper Local process may be running.")
    print("End the existing python / whisper-local process manually and try again.\n")
    sys.exit(1)
