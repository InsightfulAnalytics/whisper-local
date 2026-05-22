import datetime
import json
import logging
import threading
from pathlib import Path

from .utils import get_user_app_data_path, get_version

logger = logging.getLogger(__name__)

_API_URL = 'https://api.github.com/repos/drajb/whisper-local/releases/latest'
_LAST_CHECK_FILE = 'last_update_check.txt'


def maybe_check_for_update(notify_callback, config: dict):
    if not (config or {}).get('enabled', False):
        return
    threading.Thread(
        target=_check_in_background,
        args=(notify_callback,),
        daemon=True,
        name='update-check',
    ).start()


def _check_in_background(notify_callback):
    last_file = Path(get_user_app_data_path()) / _LAST_CHECK_FILE
    today = datetime.date.today().isoformat()

    if last_file.exists():
        try:
            if last_file.read_text(encoding='utf-8').strip() == today:
                return
        except Exception:
            pass

    try:
        import urllib.request
        current = get_version()
        req = urllib.request.Request(
            _API_URL,
            headers={'User-Agent': f'whisper-local/{current}'},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        latest_tag = data.get('tag_name', '').lstrip('v')
        if latest_tag and _is_newer(latest_tag, current):
            notify_callback(
                f"Update available: v{latest_tag} — run: pip install --upgrade whisper-local"
            )
        try:
            last_file.write_text(today, encoding='utf-8')
        except Exception:
            pass
    except Exception as e:
        logger.debug(f"Update check failed: {e}")


def _is_newer(latest: str, current: str) -> bool:
    try:
        def _parts(v):
            return tuple(int(x) for x in v.split('.')[:3])
        return _parts(latest) > _parts(current)
    except Exception:
        return False
