import logging
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

from ruamel.yaml import YAML

from .utils import get_user_app_data_path

logger = logging.getLogger(__name__)

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-']{4,30}")

COMMON_WORDS = {
    'about', 'after', 'again', 'against', 'because', 'before', 'being',
    'between', 'could', 'doing', 'during', 'either', 'every', 'first',
    'from', 'have', 'having', 'into', 'itself', 'just', 'might', 'never',
    'only', 'other', 'over', 'same', 'should', 'since', 'some', 'still',
    'such', 'than', 'that', 'their', 'them', 'then', 'there', 'these',
    'they', 'this', 'those', 'through', 'under', 'until', 'used', 'very',
    'were', 'what', 'when', 'where', 'which', 'while', 'with', 'within',
    'without', 'would', 'your',
}

TEXT_EXTENSIONS = {
    '.txt', '.md', '.markdown', '.rst', '.py', '.js', '.ts', '.tsx',
    '.jsx', '.go', '.rs', '.java', '.cs', '.cpp', '.c', '.h', '.hpp',
    '.rb', '.php', '.swift', '.kt', '.scala', '.lua', '.sh', '.bash',
    '.yaml', '.yml', '.toml', '.json', '.xml', '.html', '.css',
    '.tex', '.org', '.log', '.csv', '.tsv',
}


def import_vocab(source: str, top_n: int = 50, write: bool = True) -> int:
    src_path = Path(source).expanduser().resolve()
    if not src_path.exists():
        print(f"Path not found: {src_path}")
        return 1

    counter: Counter = Counter()
    files_scanned = 0
    for path in _iter_files(src_path):
        files_scanned += 1
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        for word in WORD_RE.findall(text):
            lower = word.lower()
            if lower in COMMON_WORDS:
                continue
            counter[word] += 1

    if not counter:
        print(f"No candidate words found across {files_scanned} files.")
        return 1

    candidates = [w for w, _ in counter.most_common(top_n * 4) if not w.islower()]
    if len(candidates) < top_n:
        candidates += [w for w, _ in counter.most_common(top_n * 4) if w.islower() and w not in candidates]
    picks = candidates[:top_n]

    print(f"\nScanned {files_scanned} file(s) under {src_path}")
    print(f"Suggested hotwords (top {len(picks)}, ranked by frequency, common words filtered):\n")
    for w in picks:
        print(f"  {counter[w]:>5}  {w}")

    if not write:
        return 0

    answer = input(f"\nMerge these into user_settings.yaml whisper.hotwords? [Y/n] ").strip().lower()
    if answer in ('n', 'no'):
        print("Aborted; no changes made.")
        return 0

    _merge_hotwords(picks)
    print(f"\nMerged {len(picks)} hotwords into user_settings.yaml. Restart whisper-local to apply.")
    return 0


def _iter_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
        return
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if any(part.startswith('.') for part in path.parts):
            continue
        if 'node_modules' in path.parts or 'venv' in path.parts or '__pycache__' in path.parts:
            continue
        yield path


def _merge_hotwords(words):
    user_path = Path(get_user_app_data_path()) / 'user_settings.yaml'
    yaml = YAML()
    if user_path.exists():
        with open(user_path, encoding='utf-8') as f:
            data = yaml.load(f) or {}
    else:
        data = {}
    whisper = data.setdefault('whisper', {})
    current = list(whisper.get('hotwords') or [])
    merged = list(dict.fromkeys(current + list(words)))
    whisper['hotwords'] = merged
    with open(user_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f)
