import datetime
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Optional

from .utils import get_user_app_data_path

STATS_FILE = "stats.jsonl"

GREEN = "\033[32m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

WPM_TYPING_BASELINE = 40
CHARS_PER_WORD = 5

logger = logging.getLogger(__name__)


def record_transcription(char_count: int, duration_seconds: float, app: Optional[str] = None):
    if char_count <= 0:
        return
    try:
        entry = {
            'ts': datetime.datetime.now().isoformat(timespec='seconds'),
            'chars': char_count,
            'duration_s': round(float(duration_seconds), 2),
            'app': (app or '').lower(),
        }
        path = Path(get_user_app_data_path()) / STATS_FILE
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        logger.debug(f"Stats record failed: {e}")


def export_transcripts(dest: str) -> int:
    path = Path(get_user_app_data_path()) / STATS_FILE
    if not path.exists():
        print("No transcription history to export.")
        return 1

    dest_path = Path(dest).expanduser().resolve()
    fmt = dest_path.suffix.lower()
    if fmt not in ('.txt', '.md', '.csv'):
        print(f"Unknown extension '{fmt}'. Use .txt, .md, or .csv")
        return 1

    entries = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    try:
        if fmt == '.csv':
            import csv
            with open(dest_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'app', 'duration_seconds', 'characters'])
                for e in entries:
                    writer.writerow([e.get('ts', ''), e.get('app', ''),
                                     e.get('duration_s', ''), e.get('chars', '')])
        elif fmt == '.md':
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(f"# Whisper Local — Transcription Log\n\n")
                f.write(f"| Time | App | Seconds | Chars |\n|---|---|---|---|\n")
                for e in entries:
                    f.write(f"| {e.get('ts','')} | {e.get('app','')} | {e.get('duration_s',''):.1f} | {e.get('chars',0)} |\n")
        else:
            with open(dest_path, 'w', encoding='utf-8') as f:
                for e in entries:
                    f.write(f"{e.get('ts','')}\t{e.get('app','')}\t{e.get('duration_s',0)}s\t{e.get('chars',0)} chars\n")
    except OSError as e:
        print(f"Write failed: {e}")
        return 1

    print(f"Exported {len(entries)} entries to {dest_path}")
    return 0


def show_stats() -> int:
    path = Path(get_user_app_data_path()) / STATS_FILE
    if not path.exists():
        print("No transcription history yet — go dictate something!")
        return 0

    entries = []
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError as e:
        print(f"Could not read {path}: {e}")
        return 1

    if not entries:
        print("Stats file is empty.")
        return 0

    total = len(entries)
    total_chars = sum(int(e.get('chars', 0)) for e in entries)
    total_seconds = sum(float(e.get('duration_s', 0)) for e in entries)
    words = total_chars // CHARS_PER_WORD
    minutes_typing = words / WPM_TYPING_BASELINE
    minutes_speaking = total_seconds / 60
    saved_minutes = max(0.0, minutes_typing - minutes_speaking)

    by_app = Counter(e.get('app') or '<unknown>' for e in entries)
    last_week_cutoff = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    last_week = [e for e in entries if e.get('ts', '') >= last_week_cutoff]

    print(f"\n{BOLD}Whisper Local — Stats{RESET}\n{'=' * 23}\n")
    print(f"{GREEN}{BOLD}{total:>7}{RESET}  transcriptions")
    print(f"{GREEN}{BOLD}{total_chars:>7,}{RESET}  characters delivered")
    print(f"{GREEN}{BOLD}{words:>7,}{RESET}  words (≈ {CHARS_PER_WORD} chars/word)")
    print(f"{GREEN}{BOLD}{minutes_speaking:>7.1f}{RESET}  minutes spoken")
    print(f"{GREEN}{BOLD}{minutes_typing:>7.1f}{RESET}  minutes you would have typed at {WPM_TYPING_BASELINE} wpm")
    print(f"{GREEN}{BOLD}{saved_minutes:>7.1f}{RESET}  minutes saved")

    print(f"\n{BOLD}Last 7 days:{RESET} {len(last_week)} transcriptions")

    if by_app:
        print(f"\n{BOLD}Top apps:{RESET}")
        for app, count in by_app.most_common(8):
            label = app if app else '<unknown>'
            print(f"  {count:>5}  {DIM}{label}{RESET}")

    if entries:
        first_ts = entries[0].get('ts', '?')
        last_ts = entries[-1].get('ts', '?')
        print(f"\n{DIM}First entry: {first_ts}{RESET}")
        print(f"{DIM}Latest entry: {last_ts}{RESET}\n")

    return 0
