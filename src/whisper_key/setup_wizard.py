import os
import platform
import shutil
import sys
from pathlib import Path

from ruamel.yaml import YAML

from .utils import get_user_app_data_path

GREEN = "\033[32m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
RESET = "\033[0m"

DEFAULT_MODELS = [
    ("tiny", "Tiny (75MB, fast, basic accuracy)", "any CPU"),
    ("base", "Base (140MB, good balance)", "modern CPU"),
    ("small", "Small (460MB, great accuracy)", "8+ cores or GPU"),
    ("medium", "Medium (1.5GB, very accurate)", "GPU recommended"),
    ("large-v3-turbo", "Large v3 Turbo (1.5GB, best accuracy + fast)", "GPU strongly recommended"),
]


def run_wizard() -> int:
    print(f"\n{BOLD}{CYAN}Whisper Local — Setup Wizard{RESET}")
    print(f"{DIM}Press Ctrl+C any time to abort. Nothing is saved until the final step.{RESET}\n")

    overrides = {}

    overrides.setdefault('whisper', {})['model'] = _ask_model()
    overrides.setdefault('hotkey', {})['recording_mode'] = _ask_mode()
    mic_id = _ask_mic()
    if mic_id is not None:
        overrides.setdefault('audio', {})['input_device'] = mic_id

    print(f"\n{BOLD}Summary{RESET}")
    print(f"  model:          {overrides['whisper']['model']}")
    print(f"  recording_mode: {overrides['hotkey']['recording_mode']}")
    if 'input_device' in overrides.get('audio', {}):
        print(f"  input_device:   {overrides['audio']['input_device']}")
    print()

    confirm = input(f"Write to user_settings.yaml? [Y/n] ").strip().lower()
    if confirm in ('n', 'no'):
        print("Aborted; no changes made.")
        return 0

    _merge_into_user_settings(overrides)
    print(f"\n{GREEN}✓ Settings written.{RESET}  Restart whisper-local to pick them up.\n")
    return 0


def _ask_model() -> str:
    print(f"{BOLD}1. Which Whisper model?{RESET}")
    suggestion = _recommend_model()
    for i, (key, label, hint) in enumerate(DEFAULT_MODELS, 1):
        marker = f" {GREEN}← recommended for your hardware{RESET}" if key == suggestion else ""
        print(f"  {i}. {label}  {DIM}({hint}){RESET}{marker}")
    choice = input(f"\nChoose 1-{len(DEFAULT_MODELS)} [default: recommended]: ").strip()
    if not choice:
        return suggestion
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(DEFAULT_MODELS):
            return DEFAULT_MODELS[idx][0]
    except ValueError:
        pass
    return suggestion


def _ask_mode() -> str:
    print(f"\n{BOLD}2. Recording mode?{RESET}")
    print("  1. toggle        Press hotkey to start, press again (or stop key) to stop")
    print("  2. push_to_talk  Hold hotkey to record, release to stop (recommended)")
    choice = input("\nChoose 1 or 2 [default: 2]: ").strip()
    return 'toggle' if choice == '1' else 'push_to_talk'


def _ask_mic():
    try:
        import sounddevice as sd
    except ImportError:
        return None

    print(f"\n{BOLD}3. Which microphone?{RESET}")
    devices = []
    try:
        for idx, d in enumerate(sd.query_devices()):
            if d.get('max_input_channels', 0) > 0:
                devices.append((idx, d['name']))
    except Exception:
        return None

    if not devices:
        print(f"{DIM}(No input devices found, skipping){RESET}")
        return None

    try:
        default = sd.query_devices(kind='input')
        default_name = default.get('name', '')
    except Exception:
        default_name = ''

    print(f"  0. system default  {DIM}({default_name}){RESET}")
    for i, (idx, name) in enumerate(devices[:12], 1):
        print(f"  {i}. {name}")

    choice = input(f"\nChoose 0-{min(len(devices), 12)} [default: 0]: ").strip()
    if not choice or choice == '0':
        return 'default'
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(devices):
            return devices[idx][0]
    except ValueError:
        pass
    return 'default'


def _recommend_model() -> str:
    cores = os.cpu_count() or 4
    has_gpu = _detect_gpu()
    if has_gpu:
        return 'large-v3-turbo'
    if cores >= 8:
        return 'small'
    if cores >= 4:
        return 'base'
    return 'tiny'


def _detect_gpu() -> bool:
    if platform.system() != 'Windows':
        return False
    if shutil.which('nvidia-smi'):
        return True
    return False


def _merge_into_user_settings(overrides: dict):
    user_path = Path(get_user_app_data_path()) / 'user_settings.yaml'
    yaml = YAML()
    if user_path.exists():
        with open(user_path, encoding='utf-8') as f:
            existing = yaml.load(f) or {}
    else:
        existing = {}

    for section, values in overrides.items():
        if section not in existing or not isinstance(existing[section], dict):
            existing[section] = {}
        existing[section].update(values)

    with open(user_path, 'w', encoding='utf-8') as f:
        yaml.dump(existing, f)
