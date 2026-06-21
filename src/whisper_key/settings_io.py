import datetime
import shutil
from pathlib import Path

from .utils import get_user_app_data_path

# Every user-editable config file. Anything the user can customize must be here
# or backup/restore silently loses it. (Hotwords/dictionary live inside
# user_settings.yaml, so they're already covered.)
EXPORTABLE_FILES = [
    "user_settings.yaml",
    "commands.yaml",
    "profiles.yaml",
    "app_rules.yaml",
    "transforms.yaml",
]


def export_settings(dest: str) -> int:
    src_dir = Path(get_user_app_data_path())
    dest_dir = Path(dest).expanduser().resolve()

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    target = dest_dir if dest_dir.is_dir() or not dest_dir.exists() else dest_dir.parent / f"{dest_dir.name}-{stamp}"
    target.mkdir(parents=True, exist_ok=True)

    copied = []
    for name in EXPORTABLE_FILES:
        src = src_dir / name
        if src.exists():
            shutil.copy2(src, target / name)
            copied.append(name)

    if not copied:
        print("Nothing to export — no user settings found.")
        return 1

    manifest = target / "manifest.txt"
    manifest.write_text(
        f"Whisper Local settings export\nCreated: {datetime.datetime.now().isoformat()}\nFiles: {', '.join(copied)}\n",
        encoding="utf-8",
    )

    print(f"Exported {len(copied)} file(s) to {target}")
    for f in copied:
        print(f"  - {f}")
    return 0


def import_settings(src: str) -> int:
    src_dir = Path(src).expanduser().resolve()
    if not src_dir.is_dir():
        print(f"Not a directory: {src_dir}")
        return 1

    dest_dir = Path(get_user_app_data_path())
    dest_dir.mkdir(parents=True, exist_ok=True)

    backup = dest_dir / "_pre-import-backup"
    backup.mkdir(exist_ok=True)
    restored = []
    for name in EXPORTABLE_FILES:
        src_file = src_dir / name
        if not src_file.exists():
            continue
        dest_file = dest_dir / name
        if dest_file.exists():
            shutil.copy2(dest_file, backup / name)
        shutil.copy2(src_file, dest_file)
        restored.append(name)

    if not restored:
        print(f"No exportable files found in {src_dir}.")
        return 1

    print(f"Restored {len(restored)} file(s) from {src_dir} into {dest_dir}")
    for f in restored:
        print(f"  - {f}")
    print(f"Pre-import backup at {backup}")
    return 0
