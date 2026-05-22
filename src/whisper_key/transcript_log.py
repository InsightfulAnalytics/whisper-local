import datetime
import json
import logging
from pathlib import Path

from .utils import get_user_app_data_path

logger = logging.getLogger(__name__)

_LOG_FILE = 'transcripts.jsonl'
_MAX_ENTRIES = 2000


def record_transcript(text: str, app: str = '', duration_s: float = 0.0):
    if not text:
        return
    entry = {
        'timestamp': datetime.datetime.now().isoformat(timespec='seconds'),
        'text': text,
        'app': app,
        'duration_s': round(duration_s, 2),
        'chars': len(text),
    }
    path = Path(get_user_app_data_path()) / _LOG_FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        _maybe_rotate(path)
    except Exception as e:
        logger.debug(f"Transcript log write failed: {e}")


def load_transcripts() -> list:
    path = Path(get_user_app_data_path()) / _LOG_FILE
    entries = []
    if not path.exists():
        return entries
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get('text'):
                        entries.append(obj)
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        logger.warning(f"Failed to load transcripts: {e}")
    return list(reversed(entries))


def _maybe_rotate(path: Path):
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
        if len(lines) > _MAX_ENTRIES * 1.2:
            trimmed = lines[-_MAX_ENTRIES:]
            path.write_text('\n'.join(trimmed) + '\n', encoding='utf-8')
    except Exception:
        pass
