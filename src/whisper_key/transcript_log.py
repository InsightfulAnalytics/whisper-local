# transcript_log.py
# Append-only journal of every successful transcription. Backs the
# `--history` browser window so users can search their dictation history.
# Separate from `stats.jsonl` (which only stores metadata) — this file
# contains the actual transcribed text and is auto-rotated to keep the
# last ~2000 entries.

import datetime
import json
import logging
from pathlib import Path

from .utils import get_user_app_data_path

logger = logging.getLogger(__name__)

# Newline-delimited JSON — one transcript per line. Append-only writes are
# atomic at typical sizes, so we don't need a lock.
_LOG_FILE = 'transcripts.jsonl'
_MAX_ENTRIES = 2000


# Called from state_manager._transcription_pipeline after every successful
# delivery. Silent no-op for empty text (which means a failed/silent recording).
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


# Reads the journal back into a list of dicts, newest-first. Used by the
# history window. Silently skips malformed lines so a single corrupted entry
# doesn't break the whole UI.
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


# Cap the journal at roughly _MAX_ENTRIES. We allow it to grow to 1.2× before
# truncating to amortise the cost — counting lines on every write would dominate
# the actual transcription work.
def _maybe_rotate(path: Path):
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
        if len(lines) > _MAX_ENTRIES * 1.2:
            trimmed = lines[-_MAX_ENTRIES:]
            path.write_text('\n'.join(trimmed) + '\n', encoding='utf-8')
    except Exception:
        pass
