import logging
import threading
from pathlib import Path
from typing import List, Optional

from ruamel.yaml import YAML

from .utils import get_user_app_data_path

logger = logging.getLogger(__name__)
USER_SETTINGS = "user_settings.yaml"


def list_hotwords() -> List[str]:
    user_path = Path(get_user_app_data_path()) / USER_SETTINGS
    if not user_path.exists():
        return []
    try:
        with open(user_path, encoding='utf-8') as f:
            data = YAML().load(f) or {}
        return list((data.get('whisper') or {}).get('hotwords') or [])
    except Exception as e:
        logger.warning(f"Could not read hotwords: {e}")
        return []


def add_word(word: str) -> bool:
    word = (word or '').strip()
    if not word:
        return False
    user_path = Path(get_user_app_data_path()) / USER_SETTINGS
    yaml = YAML()
    if user_path.exists():
        with open(user_path, encoding='utf-8') as f:
            data = yaml.load(f) or {}
    else:
        data = {}
    whisper = data.setdefault('whisper', {})
    current = list(whisper.get('hotwords') or [])
    if word in current:
        print(f"   '{word}' already in dictionary")
        return False
    current.append(word)
    whisper['hotwords'] = current
    with open(user_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f)
    print(f"   ✓ Added '{word}' to whisper.hotwords ({len(current)} total)")
    return True


def remove_word(word: str) -> bool:
    word = (word or '').strip()
    if not word:
        return False
    user_path = Path(get_user_app_data_path()) / USER_SETTINGS
    if not user_path.exists():
        return False
    yaml = YAML()
    with open(user_path, encoding='utf-8') as f:
        data = yaml.load(f) or {}
    whisper = data.get('whisper') or {}
    current = list(whisper.get('hotwords') or [])
    if word not in current:
        print(f"   '{word}' not found in dictionary")
        return False
    current.remove(word)
    whisper['hotwords'] = current
    data['whisper'] = whisper
    with open(user_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f)
    print(f"   ✓ Removed '{word}' from dictionary ({len(current)} left)")
    return True


def show_dictionary() -> int:
    words = list_hotwords()
    if not words:
        print("Dictionary is empty. Add words with: whisper-local --add-word NAME")
        return 0
    print(f"\nWhisper Local — Dictionary ({len(words)} word{'s' if len(words) != 1 else ''})\n")
    for w in sorted(words, key=str.lower):
        print(f"  • {w}")
    print()
    print("Edit via:")
    print("  whisper-local --add-word NAME")
    print("  whisper-local --remove-word NAME")
    print(f"  Or open {Path(get_user_app_data_path()) / USER_SETTINGS} directly\n")
    return 0


def show_add_word_dialog(on_added=None):
    def run():
        try:
            import tkinter as tk
        except ImportError:
            logger.info("Tkinter unavailable for add-word dialog")
            return
        try:
            root = tk.Tk()
            root.title("Whisper Local — Add Word")
            root.configure(bg='#0d1117')
            try:
                root.attributes('-topmost', True)
            except Exception:
                pass

            w, h = 380, 160
            try:
                root.update_idletasks()
                sw = root.winfo_screenwidth()
                sh = root.winfo_screenheight()
                root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
            except Exception:
                root.geometry(f"{w}x{h}")

            outer = tk.Frame(root, bg='#0d1117', padx=14, pady=12)
            outer.pack(fill='both', expand=True)

            tk.Label(outer, text="Add to your hotword dictionary",
                     bg='#0d1117', fg='#3fb950',
                     font=('Segoe UI Semibold', 11),
                     anchor='w').pack(fill='x')
            tk.Label(outer, text="Names, jargon, acronyms — anything Whisper mishears",
                     bg='#0d1117', fg='#7d8590',
                     font=('Segoe UI', 9),
                     anchor='w').pack(fill='x', pady=(2, 10))

            entry_var = tk.StringVar()
            entry = tk.Entry(outer, textvariable=entry_var,
                             bg='#161b22', fg='#c9d1d9',
                             insertbackground='#c9d1d9',
                             relief='flat', bd=0,
                             font=('Segoe UI', 11))
            entry.pack(fill='x', ipady=6, pady=(0, 12))
            entry.focus_set()

            status_var = tk.StringVar(value="")
            tk.Label(outer, textvariable=status_var,
                     bg='#0d1117', fg='#7d8590',
                     font=('Segoe UI', 9),
                     anchor='w').pack(fill='x', pady=(0, 8))

            def commit(_=None):
                word = entry_var.get().strip()
                if not word:
                    status_var.set("Type a word first.")
                    return
                ok = add_word(word)
                if ok:
                    status_var.set(f"Added '{word}'. Restart Whisper Local to apply.")
                    entry_var.set("")
                    if on_added:
                        try: on_added(word)
                        except Exception: pass
                else:
                    status_var.set(f"'{word}' is already in the dictionary.")

            def close(_=None):
                try: root.destroy()
                except Exception: pass

            buttons = tk.Frame(outer, bg='#0d1117')
            buttons.pack(fill='x')

            tk.Button(buttons, text="Close", command=close,
                      bg='#161b22', fg='#c9d1d9',
                      activebackground='#30363d', activeforeground='#c9d1d9',
                      bd=0, relief='flat', padx=14, pady=6,
                      font=('Segoe UI', 9), cursor='hand2').pack(side='right', padx=(8, 0))
            tk.Button(buttons, text="Add", command=commit,
                      bg='#3fb950', fg='#0d1117',
                      activebackground='#46c155', activeforeground='#0d1117',
                      bd=0, relief='flat', padx=14, pady=6,
                      font=('Segoe UI Semibold', 9), cursor='hand2').pack(side='right')

            root.bind('<Return>', commit)
            root.bind('<Escape>', close)
            root.mainloop()
        except Exception as e:
            logger.warning(f"Add-word dialog failed: {e}")

    threading.Thread(target=run, daemon=True, name='add-word-dialog').start()
