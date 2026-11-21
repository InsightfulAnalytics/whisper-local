# foreground.py (Linux)
# Reports the focused window for per-app rules and the "is there a text field"
# check. Hyprland's window class plays the part of the Windows exe name.

import json
import logging

from . import hyprland

logger = logging.getLogger(__name__)


def get_foreground_app() -> dict:
    try:
        window = json.loads(hyprland.request('j/activewindow') or '{}')
    except Exception as e:
        logger.debug(f"Foreground app probe failed: {e}")
        return {}
    # An empty workspace has no active window: Hyprland answers "{}".
    if not window.get('class'):
        return {}
    return {
        'exe': window['class'].lower(),
        'path': '',
        'title': window.get('title', ''),
    }
