import datetime
import io
import logging
import os
import re
import sys
import zipfile
from pathlib import Path

from .utils import get_user_app_data_path, get_version

logger = logging.getLogger(__name__)

_REDACTIONS = [
    (re.compile(r'(C:\\Users\\)([^\\]+)', re.IGNORECASE), r'\1<USER>'),
    (re.compile(r'(/Users/)([^/]+)'), r'\1<USER>'),
    (re.compile(r'(/home/)([^/]+)'), r'\1<USER>'),
    (re.compile(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b'), '<EMAIL>'),
]


def bundle_logs(output_path: str = None) -> int:
    app_data = Path(get_user_app_data_path())

    if not output_path:
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        output_path = str(Path.cwd() / f"whisper-local-bundle-{stamp}.zip")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    bundled = []
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('about.txt', _build_about())
        bundled.append('about.txt')

        zf.writestr('doctor.txt', _capture_doctor())
        bundled.append('doctor.txt')

        log_path = app_data / 'app.log'
        if log_path.exists():
            tail = _tail_lines(log_path, 500)
            zf.writestr('app.log', _redact(tail))
            bundled.append('app.log')

        for older in sorted(app_data.glob('app.log.*'))[-2:]:
            try:
                content = older.read_text(encoding='utf-8', errors='replace')
                zf.writestr(older.name, _redact(content))
                bundled.append(older.name)
            except Exception:
                pass

        settings = app_data / 'user_settings.yaml'
        if settings.exists():
            try:
                zf.writestr('user_settings.yaml',
                            _redact(settings.read_text(encoding='utf-8', errors='replace')))
                bundled.append('user_settings.yaml')
            except Exception:
                pass

        crash_dir = app_data / 'crashes'
        if crash_dir.exists():
            cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
            for crash_file in sorted(crash_dir.iterdir())[-10:]:
                try:
                    mtime = datetime.datetime.fromtimestamp(crash_file.stat().st_mtime)
                    if mtime < cutoff:
                        continue
                    content = crash_file.read_text(encoding='utf-8', errors='replace')
                    zf.writestr(f'crashes/{crash_file.name}', _redact(content))
                    bundled.append(f'crashes/{crash_file.name}')
                except Exception:
                    pass

    print(f"\n📦 Diagnostic bundle written to: {output}")
    print(f"   {len(bundled)} files included:")
    for f in bundled:
        print(f"   • {f}")
    print("\n   ℹ Personal paths (usernames, email addresses) have been redacted.")
    print("   ℹ Review the zip before sharing if you've enabled log_transcriptions.\n")
    return 0


def _build_about() -> str:
    return (
        f"Whisper Local diagnostic bundle\n"
        f"Generated: {datetime.datetime.now().isoformat()}\n"
        f"Version: {get_version()}\n"
        f"Python: {sys.version}\n"
        f"Platform: {sys.platform}\n\n"
        "Contents:\n"
        "  about.txt        — this file\n"
        "  doctor.txt       — output of `whisper-local --doctor`\n"
        "  app.log          — last ~500 lines of the main log (redacted)\n"
        "  app.log.N        — last 2 rotated logs if present\n"
        "  user_settings.yaml  — your settings (redacted)\n"
        "  crashes/*        — last 10 crash reports from the past 7 days\n\n"
        "Privacy:\n"
        "  Usernames in paths and any email-shaped strings have been replaced\n"
        "  with placeholders. Transcript text is NOT in the log unless you\n"
        "  enabled `logging.log_transcriptions: true`. Please review before sharing.\n"
    )


def _capture_doctor() -> str:
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        from .doctor import run_doctor
        run_doctor()
    except Exception as e:
        buf.write(f"\n[bundle-logs: doctor crashed: {e}]\n")
    finally:
        sys.stdout = old_stdout
    return _redact(buf.getvalue())


def _tail_lines(path: Path, n: int) -> str:
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        return ''.join(lines[-n:])
    except Exception as e:
        return f"[bundle-logs: could not read {path}: {e}]"


def _redact(text: str) -> str:
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text
