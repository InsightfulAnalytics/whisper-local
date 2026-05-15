import datetime
import logging
from pathlib import Path
from typing import Optional

from .utils import get_user_app_data_path

AUDIT_FILE = "audit.log"

logger = logging.getLogger(__name__)


def record(event: str, text: Optional[str], app: Optional[str], enabled: bool):
    if not enabled:
        return
    try:
        path = Path(get_user_app_data_path()) / AUDIT_FILE
        ts = datetime.datetime.now().isoformat(timespec='seconds')
        char_count = len(text or '')
        line = f"{ts}\t{event}\tapp={app or '?'}\tchars={char_count}\n"
        with open(path, 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception as e:
        logger.debug(f"Audit record skipped: {e}")
