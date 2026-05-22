import logging

logger = logging.getLogger(__name__)

BG = '#0d1117'
BG2 = '#161b22'
BG3 = '#21262d'
FG = '#c9d1d9'
FG_DIM = '#8b949e'
ACCENT = '#1f6feb'
SEP = '#30363d'


def run_settings_window():
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        logger.error("Tkinter not available")
        return

    from .config_manager import ConfigManager
    cm = ConfigManager(quiet=True)

    root = tk.Tk()
    root.title("Whisper Local — Settings")
    root.geometry("540x580")
    root.resizable(False, False)
    root.configure(bg=BG)
    try:
        root.attributes('-topmost', True)
    except Exception:
        pass

    _apply_style(root)

    nb = ttk.Notebook(root)
    nb.pack(fill='both', expand=True, padx=8, pady=8)

    vars_ = {}

    _build_general_tab(nb, cm, vars_)
    _build_audio_tab(nb, cm, vars_)
    _build_hotkeys_tab(nb, cm, vars_)
    _build_postprocess_tab(nb, cm, vars_)

    sep = tk.Frame(root, bg=SEP, height=1)
    sep.pack(fill='x', padx=8)

    btns = tk.Frame(root, bg=BG)
    btns.pack(fill='x', padx=8, pady=8)

    def save():
        _save_all(cm, vars_)
        messagebox.showinfo(
            "Saved",
            "Settings saved.\n\nHotkey and device changes take effect on the next app restart.",
            parent=root,
        )
        root.destroy()

    tk.Button(btns, text='Save', command=save,
              bg=ACCENT, fg='white', relief='flat',
              padx=18, pady=5, font=('Segoe UI', 9)).pack(side='right', padx=(4, 0))
    tk.Button(btns, text='Cancel', command=root.destroy,
              bg=BG3, fg=FG, relief='flat',
              padx=18, pady=5, font=('Segoe UI', 9)).pack(side='right')

    root.mainloop()


def _apply_style(root):
    try:
        import tkinter.ttk as ttk
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', background=BG, foreground=FG, borderwidth=0)
        style.configure('TNotebook', background=BG, borderwidth=0)
        style.configure('TNotebook.Tab', background=BG3, foreground=FG_DIM,
                         padding=[10, 4])
        style.map('TNotebook.Tab',
                  background=[('selected', BG2)],
                  foreground=[('selected', FG)])
        style.configure('TFrame', background=BG)
        style.configure('TLabel', background=BG, foreground=FG)
        style.configure('TCheckbutton', background=BG, foreground=FG)
        style.configure('TEntry', fieldbackground=BG2, foreground=FG,
                         insertcolor=FG, bordercolor=SEP)
        style.configure('TCombobox', fieldbackground=BG2, foreground=FG,
                         selectbackground=BG2, selectforeground=FG)
        style.configure('TSeparator', background=SEP)
    except Exception:
        pass


def _frame(nb, title):
    f = ttk.Frame(nb)
    f.columnconfigure(1, weight=1)
    nb.add(f, text=title)
    return f


def _row(parent, label, widget_fn, row, note=None):
    ttk.Label(parent, text=label, foreground=FG_DIM,
              font=('Segoe UI', 9)).grid(
        row=row, column=0, sticky='w', padx=(12, 6), pady=4)
    w = widget_fn(parent)
    w.grid(row=row, column=1, sticky='ew', padx=(0, 12), pady=4)
    if note:
        ttk.Label(parent, text=note, foreground=FG_DIM,
                  font=('Segoe UI', 8)).grid(
            row=row + 1, column=0, columnspan=2, sticky='w',
            padx=(12, 12), pady=(0, 4))
    return w


def _check(parent, label, var, row):
    cb = ttk.Checkbutton(parent, text=label, variable=var)
    cb.grid(row=row, column=0, columnspan=2, sticky='w', padx=(12, 12), pady=3)
    return cb


def _combo(parent, var, values):
    import tkinter.ttk as ttk
    cb = ttk.Combobox(parent, textvariable=var, values=values,
                      state='readonly', width=22)
    return cb


def _entry(parent, var):
    import tkinter as tk
    return tk.Entry(parent, textvariable=var,
                    bg=BG2, fg=FG, insertbackground=FG,
                    relief='flat', bd=4, font=('Consolas', 9), width=24)


def _v(cfg, *path, default=''):
    obj = cfg
    for k in path:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(k, default)
    return obj if obj is not None else default


def _build_general_tab(nb, cm, vars_):
    import tkinter as tk
    f = _frame(nb, 'General')
    cfg = cm.config
    whisper = cfg.get('whisper', {})

    models = list((whisper.get('models') or {}).keys())
    v = tk.StringVar(value=_v(cfg, 'whisper', 'model', default='tiny'))
    vars_['whisper.model'] = v
    _row(f, 'Model', lambda p: _combo(p, v, models), 0)

    langs = ['auto', 'en', 'es', 'fr', 'de', 'it', 'pt', 'nl', 'pl',
             'ru', 'ja', 'zh', 'ko', 'hi', 'ar']
    v = tk.StringVar(value=_v(cfg, 'whisper', 'language', default='auto'))
    vars_['whisper.language'] = v
    _row(f, 'Language', lambda p: _combo(p, v, langs), 2)

    modes = ['toggle', 'push_to_talk']
    v = tk.StringVar(value=_v(cfg, 'hotkey', 'recording_mode', default='toggle'))
    vars_['hotkey.recording_mode'] = v
    _row(f, 'Recording mode', lambda p: _combo(p, v, modes), 4)

    devs = ['cpu', 'cuda']
    v = tk.StringVar(value=_v(cfg, 'whisper', 'device', default='cpu'))
    vars_['whisper.device'] = v
    _row(f, 'Compute device', lambda p: _combo(p, v, devs), 6)

    ctypes = ['int8', 'float16', 'float32']
    v = tk.StringVar(value=_v(cfg, 'whisper', 'compute_type', default='int8'))
    vars_['whisper.compute_type'] = v
    _row(f, 'Compute type', lambda p: _combo(p, v, ctypes), 8)

    v = tk.StringVar(value=str(_v(cfg, 'whisper', 'beam_size', default=5)))
    vars_['whisper.beam_size'] = v
    _row(f, 'Beam size (1–10)', lambda p: _entry(p, v), 10)

    v = tk.StringVar(value=str(_v(cfg, 'whisper', 'initial_prompt', default='')))
    vars_['whisper.initial_prompt'] = v
    _row(f, 'Initial prompt', lambda p: _entry(p, v), 12)

    v = tk.BooleanVar(value=bool(_v(cfg, 'whisper', 'prompt_from_selection', default=False)))
    vars_['whisper.prompt_from_selection'] = v
    _check(f, 'Seed prompt from selected text at recording start', v, 14)

    v = tk.BooleanVar(value=bool(_v(cfg, 'clipboard', 'auto_paste', default=True)))
    vars_['clipboard.auto_paste'] = v
    _check(f, 'Auto-paste at cursor after transcription', v, 15)

    v = tk.BooleanVar(value=bool(_v(cfg, 'audio', 'continuous_mode', default=False)))
    vars_['audio.continuous_mode'] = v
    _check(f, 'Continuous dictation mode (auto-restarts recording)', v, 16)


def _build_audio_tab(nb, cm, vars_):
    import tkinter as tk
    f = _frame(nb, 'Audio')
    cfg = cm.config
    ns = (cfg.get('audio') or {}).get('noise_suppression') or {}

    v = tk.BooleanVar(value=bool(ns.get('enabled', False)))
    vars_['audio.noise_suppression.enabled'] = v
    _check(f, 'Noise suppression  (pip install noisereduce)', v, 0)

    v = tk.StringVar(value=str(ns.get('strength', 0.75)))
    vars_['audio.noise_suppression.strength'] = v
    _row(f, 'Noise strength (0.0 – 1.0)', lambda p: _entry(p, v), 1)

    v = tk.BooleanVar(value=bool(_v(cfg, 'audio', 'pause_media_on_record', default=False)))
    vars_['audio.pause_media_on_record'] = v
    _check(f, 'Pause media player when recording starts', v, 3)

    v = tk.StringVar(value=str(_v(cfg, 'audio', 'max_duration', default=900)))
    vars_['audio.max_duration'] = v
    _row(f, 'Max recording duration (s)', lambda p: _entry(p, v), 4)

    v = tk.BooleanVar(value=bool(_v(cfg, 'vad', 'vad_realtime_enabled', default=True)))
    vars_['vad.vad_realtime_enabled'] = v
    _check(f, 'Auto-stop on silence (realtime VAD)', v, 6)

    v = tk.StringVar(value=str(_v(cfg, 'vad', 'vad_silence_timeout_seconds', default=30.0)))
    vars_['vad.vad_silence_timeout_seconds'] = v
    _row(f, 'Silence timeout (s)', lambda p: _entry(p, v), 7)

    v = tk.BooleanVar(value=bool(_v(cfg, 'audio_feedback', 'enabled', default=True)))
    vars_['audio_feedback.enabled'] = v
    _check(f, 'Audio feedback sounds (start / stop beeps)', v, 9)


def _build_hotkeys_tab(nb, cm, vars_):
    import tkinter as tk
    f = _frame(nb, 'Hotkeys')
    cfg = cm.config

    pairs = [
        ('hotkey.recording_hotkey', 'Record hotkey'),
        ('hotkey.stop_key', 'Stop key'),
        ('hotkey.auto_send_key', 'Auto-send key'),
        ('hotkey.cancel_combination', 'Cancel'),
        ('hotkey.command_hotkey', 'Command mode'),
        ('hotkey.rephrase_hotkey', 'Rephrase (PTT)'),
        ('hotkey.pause_hotkey', 'Pause all hotkeys'),
    ]
    for row, (path, label) in enumerate(pairs):
        parts = path.split('.')
        v = tk.StringVar(value=str(_v(cfg, *parts, default='')))
        vars_[path] = v
        _row(f, label, lambda p, var=v: _entry(p, var), row * 2)

    ttk.Label(f, text='Hotkey changes take effect on next app restart.',
              foreground=FG_DIM, font=('Segoe UI', 8)).grid(
        row=len(pairs) * 2 + 2, column=0, columnspan=2,
        sticky='w', padx=12, pady=(10, 4))


def _build_postprocess_tab(nb, cm, vars_):
    import tkinter as tk
    f = _frame(nb, 'Post-process')
    cfg = cm.config
    pp = cfg.get('postprocess') or {}

    checks = [
        ('postprocess.strip_filler_words', 'Strip filler words  (um, uh, like, you know)', 'strip_filler_words'),
        ('postprocess.capitalize_first', 'Capitalize first letter', 'capitalize_first'),
        ('postprocess.ensure_punctuation', 'Ensure sentence ends with punctuation', 'ensure_punctuation'),
        ('postprocess.strip_trailing_period', 'Strip trailing period', 'strip_trailing_period'),
        ('postprocess.inline_formatting', 'Inline voice formatting  (say "comma", "period")', 'inline_formatting'),
    ]
    for row, (var_key, label, cfg_key) in enumerate(checks):
        v = tk.BooleanVar(value=bool(pp.get(cfg_key, False)))
        vars_[var_key] = v
        _check(f, label, v, row)

    ttk.Separator(f, orient='horizontal').grid(
        row=len(checks), column=0, columnspan=2,
        sticky='ew', padx=12, pady=8)

    ollama = pp.get('ollama') or {}
    base = len(checks) + 1

    v = tk.BooleanVar(value=bool(ollama.get('enabled', False)))
    vars_['postprocess.ollama.enabled'] = v
    _check(f, 'Ollama polish  (local LLM punctuation cleanup)', v, base)

    v = tk.StringVar(value=str(ollama.get('endpoint', 'http://localhost:11434')))
    vars_['postprocess.ollama.endpoint'] = v
    _row(f, 'Ollama endpoint', lambda p: _entry(p, v), base + 1)

    v = tk.StringVar(value=str(ollama.get('model', 'llama3.2')))
    vars_['postprocess.ollama.model'] = v
    _row(f, 'Ollama model', lambda p: _entry(p, v), base + 3)

    v = tk.StringVar(value=str(ollama.get('timeout', 5)))
    vars_['postprocess.ollama.timeout'] = v
    _row(f, 'Ollama timeout (s)', lambda p: _entry(p, v), base + 5)


def _save_all(cm, vars_):
    pending_nested = {}

    for path, var in vars_.items():
        raw = var.get()
        value = _coerce(var, raw)
        parts = path.split('.')

        if len(parts) == 2:
            try:
                cm.update_user_setting(parts[0], parts[1], value)
            except Exception as e:
                logger.warning(f"Could not save {path}: {e}")

        elif len(parts) == 3:
            key = (parts[0], parts[1])
            if key not in pending_nested:
                parent = cm.config.get(parts[0], {})
                pending_nested[key] = dict(parent.get(parts[1]) or {})
            pending_nested[key][parts[2]] = value

    for (section, sub_key), sub_dict in pending_nested.items():
        try:
            cm.update_user_setting(section, sub_key, sub_dict)
        except Exception as e:
            logger.warning(f"Could not save {section}.{sub_key}: {e}")


def _coerce(var, raw):
    import tkinter as tk
    if isinstance(var, tk.BooleanVar):
        return bool(raw)
    try:
        return int(raw)
    except (ValueError, TypeError):
        pass
    try:
        return float(raw)
    except (ValueError, TypeError):
        pass
    return raw
