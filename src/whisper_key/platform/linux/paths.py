# paths.py (Linux)
# Where Whisper Local keeps its settings, logs and history on Linux: the XDG
# config directory, the counterpart of %APPDATA%\whisperkey on Windows.

import os
import subprocess
from pathlib import Path


def get_app_data_path():
    config_home = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    return Path(config_home) / 'whisperkey'


# Opens a file or folder in the desktop's default app. Detached so a slow
# editor launch never blocks the caller (often the tray menu thread).
def open_file(path):
    subprocess.Popen(['xdg-open', str(path)], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
