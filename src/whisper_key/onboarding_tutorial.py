# onboarding_tutorial.py
# One-time console welcome banner shown on first launch (gated by a marker file
# in the app-data dir). Prints the core hotkeys + tips. Distinct from first_run.py,
# which shows the graphical welcome window.

import logging
from pathlib import Path
from typing import Callable, Optional

from .utils import get_user_app_data_path

MARKER_FILE = "onboarding-complete.txt"

GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

logger = logging.getLogger(__name__)


def _marker_path() -> Path:
    return Path(get_user_app_data_path()) / MARKER_FILE


def needs_tutorial() -> bool:
    return not _marker_path().exists()


def mark_complete():
    try:
        _marker_path().write_text("done\n", encoding="utf-8")
    except OSError as e:
        logger.debug(f"Could not write onboarding marker: {e}")


def show_console_welcome(hotkey_summary: Optional[str] = None,
                         notify: Optional[Callable[[str], None]] = None):
    print()
    print(f"{CYAN}{BOLD}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}{BOLD}║                  Welcome to Whisper Local!                   ║{RESET}")
    print(f"{CYAN}{BOLD}╚══════════════════════════════════════════════════════════════╝{RESET}")
    print()
    print(f"  {BOLD}First time using this?{RESET} Here's everything you need.\n")
    print(f"  {GREEN}▸{RESET} {BOLD}Hold Ctrl+Win{RESET} → record")
    print(f"  {GREEN}▸{RESET} {BOLD}Release the keys{RESET} → text appears at your cursor")
    print(f"  {GREEN}▸{RESET} {BOLD}Hold Ctrl+Shift+Win{RESET} → AI rephrase (after selecting text)")
    print(f"  {GREEN}▸{RESET} {BOLD}Press Alt+Win{RESET} → voice command mode")
    print(f"  {GREEN}▸{RESET} {BOLD}Press Esc{RESET} → cancel current recording")
    print(f"  {GREEN}▸{RESET} {BOLD}Press Ctrl+Alt+Win{RESET} → pause all Whisper Local hotkeys\n")
    print(f"  {DIM}{BOLD}Tips{RESET}{DIM}:{RESET}")
    print(f"  {DIM}• Say \"comma\", \"period\", \"new paragraph\" mid-sentence{RESET}")
    print(f"  {DIM}• Right-click the tray icon for Profile, Language, Recent transcripts{RESET}")
    print(f"  {DIM}• Run {RESET}{YELLOW}whisper-local --doctor{RESET}{DIM} anytime to verify your setup{RESET}")
    print(f"  {DIM}• Run {RESET}{YELLOW}whisper-local --stats{RESET}{DIM} to see your dictation history{RESET}")
    print(f"  {DIM}• Edit {RESET}{YELLOW}%APPDATA%\\whisperkey\\commands.yaml{RESET}{DIM} for voice macros{RESET}\n")

    if notify:
        try:
            notify("Welcome! Hold Ctrl+Win to start dictating.")
        except Exception:
            pass

    mark_complete()
