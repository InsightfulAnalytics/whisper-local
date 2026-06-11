# history_window.py
# Searchable browser over `transcripts.jsonl`. Launched by `whisper-local --history`
# or the tray "Transcript history..." item. Pure Tkinter, no external deps.
# Highlights matching rows live as the user types, with a click-to-copy action.

import logging
import threading

logger = logging.getLogger(__name__)

# Singleton — re-opening the window just raises the existing one.
_lock = threading.Lock()
_instance = None


# Public entry point. Spawns the window on a daemon thread so the caller
# (CLI or tray) doesn't block. The window manages its own lifecycle.
def show_history():
    global _instance
    with _lock:
        try:
            if _instance and _instance.winfo_exists():
                _instance.lift()
                _instance.focus_force()
                return
        except Exception:
            pass

    def _run():
        global _instance
        try:
            import tkinter as tk
            import pyperclip
        except ImportError:
            logger.warning("Tkinter not available for history window")
            return

        from .transcript_log import load_transcripts
        all_entries = load_transcripts()

        root = tk.Tk()
        with _lock:
            _instance = root

        # Reset the singleton on close so a later open creates a fresh root
        # instead of probing a destroyed one.
        def _clear_ref():
            global _instance
            with _lock:
                _instance = None
        root.protocol("WM_DELETE_WINDOW", lambda: (_clear_ref(), root.destroy()))

        root.title("Transcript History — Whisper Local")
        root.geometry("680x520")
        root.configure(bg='#0d1117')
        root.resizable(True, True)
        try:
            root.attributes('-topmost', True)
        except Exception:
            pass

        # ── search bar ──
        top = tk.Frame(root, bg='#0d1117')
        top.pack(fill='x', padx=10, pady=(10, 4))
        tk.Label(top, text='🔍', bg='#0d1117', fg='#8b949e',
                 font=('Segoe UI', 11)).pack(side='left')
        search_var = tk.StringVar()
        entry = tk.Entry(top, textvariable=search_var, bg='#161b22',
                         fg='#c9d1d9', insertbackground='#c9d1d9',
                         relief='flat', bd=4, font=('Segoe UI', 10))
        entry.pack(side='left', fill='x', expand=True, padx=(4, 0))
        entry.focus_set()

        # ── listbox ──
        mid = tk.Frame(root, bg='#0d1117')
        mid.pack(fill='both', expand=True, padx=10, pady=4)

        scroll = tk.Scrollbar(mid)
        scroll.pack(side='right', fill='y')
        listbox = tk.Listbox(mid, yscrollcommand=scroll.set,
                             bg='#161b22', fg='#c9d1d9',
                             selectbackground='#1f6feb',
                             relief='flat', bd=0,
                             font=('Consolas', 9),
                             activestyle='none')
        listbox.pack(fill='both', expand=True)
        scroll.config(command=listbox.yview)

        # ── preview pane ──
        preview_var = tk.StringVar(value='')
        preview = tk.Label(root, textvariable=preview_var,
                           bg='#161b22', fg='#8b949e',
                           font=('Segoe UI', 9), anchor='w',
                           wraplength=620, justify='left',
                           padx=8, pady=4)
        preview.pack(fill='x', padx=10, pady=(0, 4))

        # ── status + buttons ──
        status_var = tk.StringVar()
        tk.Label(root, textvariable=status_var, bg='#0d1117', fg='#58a6ff',
                 anchor='w', font=('Segoe UI', 8)).pack(fill='x', padx=10)

        btns = tk.Frame(root, bg='#0d1117')
        btns.pack(fill='x', padx=10, pady=(4, 10))

        visible = []

        def copy_selected():
            try:
                idx = listbox.curselection()[0]
                text = visible[idx].get('text', '')
                pyperclip.copy(text)
                status_var.set(f'Copied {len(text)} chars ✓')
                root.after(2500, lambda: _update_status())
            except IndexError:
                pass

        tk.Button(btns, text='Copy', command=copy_selected,
                  bg='#1f6feb', fg='white', relief='flat',
                  padx=14, pady=3,
                  font=('Segoe UI', 9)).pack(side='left')
        tk.Button(btns, text='Close', command=root.destroy,
                  bg='#21262d', fg='#c9d1d9', relief='flat',
                  padx=14, pady=3,
                  font=('Segoe UI', 9)).pack(side='right')

        def _update_status():
            status_var.set(f'{len(visible)} shown  ·  {len(all_entries)} total')

        def _refresh(query=''):
            q = query.lower().strip()
            del visible[:]
            visible.extend(
                e for e in all_entries
                if not q or q in (e.get('text') or '').lower()
            )
            listbox.delete(0, 'end')
            for e in visible:
                ts = (e.get('timestamp') or '')[:16].replace('T', ' ')
                app = e.get('app', '')
                app_hint = f' [{app}]' if app else ''
                text = (e.get('text') or '')
                snippet = text[:72] + ('…' if len(text) > 72 else '')
                listbox.insert('end', f'{ts}{app_hint}  {snippet}')
            _update_status()

        def _on_select(evt):
            try:
                idx = listbox.curselection()[0]
                text = visible[idx].get('text', '')
                preview_var.set(text[:300] + ('…' if len(text) > 300 else ''))
            except IndexError:
                preview_var.set('')

        listbox.bind('<<ListboxSelect>>', _on_select)
        search_var.trace_add('write', lambda *_: _refresh(search_var.get()))

        if not all_entries:
            status_var.set('No transcripts yet — start dictating!')
        else:
            _refresh()

        root.mainloop()

    threading.Thread(target=_run, daemon=True, name='history-window').start()
