import logging
import threading
from pathlib import Path

from .utils import get_user_app_data_path

logger = logging.getLogger(__name__)

_FLAG_FILE = 'first_run_complete.txt'


def is_first_run() -> bool:
    return not (Path(get_user_app_data_path()) / _FLAG_FILE).exists()


def mark_first_run_complete():
    try:
        path = Path(get_user_app_data_path())
        path.mkdir(parents=True, exist_ok=True)
        (path / _FLAG_FILE).write_text("ok", encoding='utf-8')
    except Exception as e:
        logger.debug(f"Could not write first-run flag: {e}")


def show_welcome_window(on_close=None, hotkey_label: str = "Ctrl+Win"):
    threading.Thread(
        target=_run_welcome,
        args=(on_close, hotkey_label),
        daemon=True,
        name='welcome-window',
    ).start()


def _run_welcome(on_close, hotkey_label):
    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError:
        logger.warning("Tkinter unavailable — skipping welcome window")
        if on_close:
            on_close()
        return

    BG = '#0d1117'
    BG2 = '#161b22'
    FG = '#c9d1d9'
    FG_DIM = '#8b949e'
    ACCENT = '#1f6feb'

    root = tk.Tk()
    root.title("Welcome to Whisper Local")
    root.geometry("560x460")
    root.configure(bg=BG)
    root.resizable(False, False)
    try:
        root.attributes('-topmost', True)
    except Exception:
        pass

    container = tk.Frame(root, bg=BG)
    container.pack(fill='both', expand=True, padx=24, pady=20)

    tk.Label(container, text="👋  Welcome to Whisper Local",
             bg=BG, fg=FG, font=('Segoe UI', 16, 'bold')).pack(anchor='w')
    tk.Label(container, text="Free, fully offline AI dictation. Three quick things:",
             bg=BG, fg=FG_DIM, font=('Segoe UI', 10)).pack(anchor='w', pady=(2, 14))

    items = [
        ("1.", f"Hold {hotkey_label} anywhere, speak, release.",
         "Your words appear at the cursor in any app — chat, code, browser, terminal."),
        ("2.", "The tray icon shows status & settings.",
         "On Windows the tray hides icons by default — click the ^ arrow on the taskbar "
         "and drag the Whisper Local icon out for one-click access."),
        ("3.", "Run --doctor or --selftest if anything's off.",
         "Both ship with the app and surface common issues (mic permissions, missing model, etc.)."),
    ]

    for num, title, body in items:
        row = tk.Frame(container, bg=BG2, bd=0)
        row.pack(fill='x', pady=4)
        inner = tk.Frame(row, bg=BG2)
        inner.pack(fill='x', padx=14, pady=10)
        tk.Label(inner, text=num, bg=BG2, fg=ACCENT,
                 font=('Segoe UI', 12, 'bold')).pack(side='left', anchor='n')
        body_frame = tk.Frame(inner, bg=BG2)
        body_frame.pack(side='left', fill='x', expand=True, padx=(10, 0))
        tk.Label(body_frame, text=title, bg=BG2, fg=FG,
                 font=('Segoe UI', 10, 'bold'),
                 anchor='w', justify='left', wraplength=440).pack(fill='x')
        tk.Label(body_frame, text=body, bg=BG2, fg=FG_DIM,
                 font=('Segoe UI', 9),
                 anchor='w', justify='left', wraplength=440).pack(fill='x', pady=(2, 0))

    tk.Label(container,
             text="No audio or transcripts ever leave your machine. Promise.",
             bg=BG, fg=FG_DIM, font=('Segoe UI', 9, 'italic')).pack(anchor='w', pady=(14, 0))

    btn_frame = tk.Frame(container, bg=BG)
    btn_frame.pack(fill='x', pady=(14, 0))

    def _done():
        mark_first_run_complete()
        try:
            root.destroy()
        except Exception:
            pass
        if on_close:
            on_close()

    tk.Button(btn_frame, text="Got it — let's dictate",
              command=_done, bg=ACCENT, fg='white', relief='flat',
              padx=22, pady=6, font=('Segoe UI', 10, 'bold')).pack(side='right')

    root.protocol("WM_DELETE_WINDOW", _done)
    root.mainloop()
