<div align="center">

# Whisper Local

### Free, Open-Source, **100% Offline** AI Dictation for Windows & macOS

**Press a hotkey. Speak. Your words appear at the cursor.**
No cloud. No subscription. No telemetry. Powered by [OpenAI Whisper](https://github.com/openai/whisper).

[![Tests](https://github.com/InsightfulAnalytics/whisper-local/actions/workflows/test.yml/badge.svg)](https://github.com/InsightfulAnalytics/whisper-local/actions/workflows/test.yml)
[![Release](https://github.com/InsightfulAnalytics/whisper-local/actions/workflows/release.yml/badge.svg)](https://github.com/InsightfulAnalytics/whisper-local/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/whisper-local.svg)](https://pypi.org/project/whisper-local/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey.svg)](#-quick-start)
[![Code of Conduct](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

[**Quick Start**](#-quick-start) · [**Features**](#-features) · [**vs. Wispr Flow / Dragon**](#-why-whisper-local) · [**Voice Commands**](#-voice-commands) · [**Contributing**](#-contributing)

</div>

![Whisper Local — press, speak, type](docs/hero.svg)

<sub>Want a real screen-recording demo here? See [`docs/demo-recording.md`](docs/demo-recording.md) — drop a `docs/demo.gif` in and uncomment the line below.</sub>
<!-- ![Demo](docs/demo.gif) -->


Whisper Local is a **free, open-source, fully offline alternative to Wispr Flow, Dragon, and Otter** for anyone who wants **AI dictation without shipping their audio to the cloud**. It runs on [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) and drops **push-to-talk speech-to-text into any application** you can put a cursor in — chat windows, code editors, browsers, terminals, design tools, you name it. Self-hosted, hackable, and MIT-licensed.

**Looking for:** *Wispr Flow alternative*, *offline voice typing*, *local Whisper dictation*, *free Dragon NaturallySpeaking alternative*, *privacy-first speech-to-text*, *Windows voice dictation without cloud*, *macOS push-to-talk transcription*. You found it.

---

## 🌟 Why this exists

Most dictation tools work beautifully — right up until you read the privacy policy. Your audio is streamed to someone else's server, processed there, and sometimes kept around. And you're renting the whole thing by the month.

Whisper Local takes the opposite position: **privacy and accuracy shouldn't be a trade-off.**

- 🔒 Your voice never leaves the machine — not even metadata
- 🆓 Free for good — no account, no API key, no subscription
- 🔌 Runs offline, air-gapped, long after the Wi-Fi drops
- 🛠️ Fork it, hack it, ship your own build — MIT licensed
- 💡 The same Whisper models the cloud services use, running on your own GPU

It's a **community tool**, not a product — no support SLA, no roadmap committee, no marketing budget. If it helps you, brilliant. If something's broken, issues and PRs are welcome.

> **A note from the maintainer:** This is my own build of a tool I lean on every day — a fork of Pin Wang's original Whisper dictation project, tuned to the way I actually work and shared **for anyone who wants it**. No strings attached: use it, fork it, rebrand it, ship your own version. The one ask is that you keep the LICENSE attribution intact (to Pin Wang, the original author). If you build something interesting on top of it, tell me about it in a [Discussion](https://github.com/InsightfulAnalytics/whisper-local/discussions) — but you don't owe anyone anything.
>
> — **Tim**

---

## ✨ Why Whisper Local?

| Feature | **Whisper Local** | Wispr Flow | Dragon / Dragon Anywhere | Otter.ai | Windows Speech Recognition |
|---|:---:|:---:|:---:|:---:|:---:|
| **Runs 100% offline** | ✅ | ❌ | ❌ (Anywhere) | ❌ | ✅ |
| **Audio never leaves your machine** | ✅ | ❌ | ❌ | ❌ | partial |
| **Free / open source** | ✅ | ❌ | ❌ ($$$/yr) | ❌ ($$/mo) | ✅ |
| **Modern AI accuracy (Whisper)** | ✅ | ✅ | partial | ✅ | ❌ |
| **Works in any app via hotkey** | ✅ | ✅ | partial | ❌ | partial |
| **Customisable voice commands** | ✅ | partial | ✅ | ❌ | ❌ |
| **Push-to-talk + auto-paste + auto-send** | ✅ | ✅ | partial | ❌ | ❌ |
| **GPU acceleration (NVIDIA & AMD)** | ✅ | n/a | n/a | n/a | ❌ |
| **AI rephrase / transforms (Ollama)** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Hackable / MIT licensed** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **No account required** | ✅ | ❌ | ❌ | ❌ | ✅ |

---

## 🎯 Features

- 🎙️ **Global push-to-talk hotkey** — start recording from any app with `Ctrl+Win` (Windows) or `Fn+Ctrl` (macOS)
- ⚡ **Pre-roll buffer + warmup** — captures the 500 ms before you press the key *and* pre-loads Whisper at boot, so the first word is never clipped and the first recording feels instant
- 🔵 **Floating level overlay** — a small pill at the screen edge shows you're being heard, with the transcript appearing next to the level bar (Wispr Flow–style). Optional [real-time streaming preview](docs/streaming.md) shows words *as you speak*.
- 📝 **Inline voice formatting** — say "comma", "period", "question mark", "new paragraph", "open quote", etc. mid-sentence. **Fully customizable** for any language via `postprocess.inline_formatting_replacements` (e.g. map Polish phrases to punctuation, or "arrow" → →)
- 🤖 **AI rephrase** — dedicated `Ctrl+Shift+Win` hotkey: select text, hold, speak your instruction, release — local Ollama rewrites it in place
- 🌐 **Translation mode** — speak any language, get English; tray → Profile → Translate
- 🔁 **Continuous dictation mode** — for long-form notes, the app auto-restarts recording after each delivery
- 📋 **Fallback window** — if no text field is focused, the transcript appears in a small window (pre-selected, copy button, already on clipboard)
- ⏸ **Pause-all hotkey** — `Ctrl+Alt+Win` disables every Whisper Local hotkey until you press it again
- 📋 **Auto-paste at cursor** — transcript lands wherever you're typing, optionally followed by Enter (auto-send)
- 🔒 **100 % local & private** — no network calls during use; Whisper models cached on disk
- 🚀 **GPU acceleration** — NVIDIA CUDA and AMD ROCm supported, CPU works out of the box
- 🗣️ **Voice commands** — say a trigger phrase to send a hotkey, type pre-written text, or run a shell command
- 🔁 **Hot-reload** — edit `commands.yaml` and your change applies on the next transcription, no restart
- 🩺 **Built-in diagnostics** — `whisper-local --doctor` checks audio devices, model cache, hotkeys, and recent errors
- 🎛️ **Profiles** — switch between Dictation / Chat / Code / Notes presets from the tray
- 🪟 **Per-app rules** — different behaviour *and* formatting per foreground app: auto-send in Slack, copy-only + verbatim (no auto-caps/periods) in VS Code, full sentences in email, suppress in 1Password
- ⌨️ **Type-as-you-speak** *(experimental, opt-in)* — `streaming.deliver_to_cursor` commits finalized phrases to the cursor live, Wispr-Flow style (trades full-Whisper accuracy for latency; see [docs/streaming.md](docs/streaming.md))
- 🧹 **Optional LLM cleanup** — pipe transcripts through a local [Ollama](https://ollama.ai) model for punctuation / capitalisation polish (off by default, fully local)
- 📜 **Recent transcriptions** — last 10 results in the tray menu, click to copy back
- 🔧 **Settings backup/restore** — `--export-settings` / `--import-settings` for portability
- 🖥️ **Settings UI** — `whisper-local --settings` opens a GUI settings window (no YAML editing required)
- 📜 **Transcript history** — `whisper-local --history` opens a searchable log of everything you've dictated
- 🔔 **Opt-in update notifications** — daily GitHub release check, fully offline by default (`update_check.enabled: true` to opt in)
- 🎚️ **Noise suppression** — spectral gating via `noisereduce`, off by default (`pip install 'whisper-local[noise]'`)
- 🩺 **`--selftest`** — one-command sanity check (mic, model, transcription, clipboard) — perfect for first-launch
- 🎯 **Hotkey cheat sheet** — `whisper-local --cheat-sheet` or tray menu — shows your *current* configured hotkeys at a glance
- 📦 **`--bundle-logs`** — zip up redacted logs + diagnostics for bug reports with one command
- 🌐 **Local OpenAI-compatible API** — `whisper-local --serve` exposes `POST /v1/audio/transcriptions` on `localhost:7777` for Cursor, Open WebUI, anything that speaks OpenAI Whisper API
- 🛡️ **Auto-recovery** — silently reconnects when a USB mic is unplugged mid-recording
- 🛡️ **Crash reports** — uncaught errors write a self-contained dump to disk
- 🪟 **System tray UI** — model selection, mic selection, profile switch, diagnostics
- 🍎 **Cross-platform** — Windows 10+, macOS

---

## 🚀 Quick Start

### Option 1 — Standalone Windows app (no Python needed)

1. Download **`whisper-local.exe`** from the [latest release](https://github.com/InsightfulAnalytics/whisper-local/releases/latest).
2. Double-click it. Windows SmartScreen will warn because the app isn't code-signed (a paid certificate) — click **More info → Run anyway**. The source is fully open if you'd rather audit first.
3. First launch takes a few minutes: it sets up a private Python runtime, then downloads the Whisper model. Every launch after that is instant.

### Option 2 — pip (Windows / macOS, Python 3.11–3.13)

```bash
pip install whisper-local
whisper-local
```

### Option 3 — from source

```bash
git clone https://github.com/InsightfulAnalytics/whisper-local.git
cd whisper-local
pip install -e .
```

### Launch

| | |
|---|---|
| **Terminal** | `whisper-local` (or `wl` for short) |
| **Double-click** | `whisper-local.cmd` (Windows) |
| **Start on login** | Tick **Start on login** in the tray menu (or the first-run welcome), or run `whisper-local --enable-autostart`. Disable anytime the same way. |

First launch downloads the default [`base`](https://huggingface.co/Systran/faster-whisper-base) Whisper model (~141 MB) into your HuggingFace cache. After that, **everything runs offline**. (Prefer a smaller/faster download? Set `whisper.model: tiny` — ~75 MB.)

### Use it

| Action | Windows | macOS |
|---|---|---|
| Hold to record | `Ctrl+Win` | `Fn+Ctrl` |
| Stop & paste | release key (push-to-talk) or `Ctrl` | release or `Fn` |
| Stop & auto-send (Enter) | `Alt` | `Option` |
| Cancel | `Esc` | `Shift` |
| Voice command mode | `Alt+Win` | `Fn+Command` |

### Verify everything works

```bash
whisper-local --doctor
```

Runs through Python version, dependencies, config validation, audio devices, model cache, hotkey backend, and recent log errors. Exit 0 = clean.

---

## 🗣️ Voice Commands

Speak a trigger to run keyboard shortcuts, type snippets, or launch programs. Defined in:

- **Windows:** `%APPDATA%\whisperkey\commands.yaml`
- **macOS:** `~/.whisperkey/commands.yaml`

```yaml
commands:
  # Send a keyboard shortcut
  - trigger: "undo"
    hotkey: "ctrl+z"

  # Deliver pre-written text
  - trigger: "my email"
    type: "user@example.com"

  # Run a shell command
  - trigger: "open notepad"
    run: 'notepad.exe'
```

Edits hot-reload — no app restart required. See **[docs/voice-commands.md](docs/voice-commands.md)** for the full guide.

> ⚠️ Voice commands with `run:` execute through your system shell with your user privileges. Only add commands you trust.

---

## ⚡ GPU Acceleration

On first launch, Whisper Local detects your GPU and offers one-press install of the required runtime libraries. Supports **NVIDIA CUDA** and **AMD ROCm**.

For manual setup or AMD RDNA 1, see **[docs/gpu-setup.md](docs/gpu-setup.md)**.

---

## 🌐 Local OpenAI-Compatible API

Whisper Local doubles as a **drop-in local replacement for the OpenAI Whisper API** — fully offline. Point any tool that speaks `POST /v1/audio/transcriptions` at it (Cursor, VS Code Continue, Open WebUI, n8n, custom scripts, anything else).

```bash
whisper-local --serve            # listens on http://127.0.0.1:7777
whisper-local --serve --serve-port 8080
```

```bash
# Drop-in compatible with the OpenAI SDK:
curl -X POST http://127.0.0.1:7777/v1/audio/transcriptions \
  -F file=@audio.wav -F model=whisper-1 -F response_format=text
```

Same Whisper model you use for dictation. Same GPU. No API key. No rate limit. No outgoing traffic.

---

## 🎛️ Profiles

Switch between presets from the tray icon → **Profile**:

| Profile | Behaviour |
|---|---|
| **Dictation** | General-purpose voice typing, auto-paste on |
| **Chat** | Push-to-talk, auto-paste + auto-send via `Alt` |
| **Code** | Copy-only mode for editors, never auto-sends |
| **Notes** | Quiet copy-to-clipboard, voice commands disabled |

Edit or add new profiles in `%APPDATA%\whisperkey\profiles.yaml`.

---

## 🪟 Per-app rules

Different apps want different behaviour. Whisper Local detects the
foreground window before delivering each transcription and matches it
against rules in `%APPDATA%\whisperkey\app_rules.yaml`:

```yaml
rules:
  # Chat apps: send the message immediately
  - match: ["slack.exe", "discord.exe"]
    auto_send: true

  # Code editors: copy only, and keep it verbatim (no auto-caps or trailing period)
  - match: ["code.exe", "cursor.exe"]
    auto_paste: false
    capitalize_first: false
    ensure_punctuation: false

  # Password managers: skip delivery entirely
  - match: ["1password.exe", "bitwarden.exe"]
    suppress: true
```

A rule can override delivery (`auto_send`, `auto_paste`, `suppress`), Whisper
context (`initial_prompt`, `language`, `task`), **and** formatting
(`capitalize_first`, `ensure_punctuation`, `strip_trailing_period`,
`inline_formatting`). Hot-reloads — edit and the next transcription picks it up.

## 🧹 Optional LLM cleanup

If you have [Ollama](https://ollama.ai) running locally, Whisper Local can
pipe each transcript through a small local model for punctuation and
capitalisation polish. **Off by default and fully local** — set
`postprocess.ollama.enabled: true` in `user_settings.yaml` to enable.

```yaml
postprocess:
  capitalize_first: true        # works without Ollama
  ensure_punctuation: true      # works without Ollama
  strip_filler_words: true      # works without Ollama
  ollama:
    enabled: false              # set true to opt in
    endpoint: http://localhost:11434
    model: llama3.2
    timeout: 5
```

## ⚙️ Configuration

Local settings live at:

- **Windows:** `%APPDATA%\whisperkey\user_settings.yaml`
- **macOS:** `~/.whisperkey/user_settings.yaml`

Delete the file and restart to reset to defaults. Highlights:

| Option | Default | Notes |
|---|---|---|
| `whisper.model` | `base` | Any model from `whisper.models`. `tiny` = smallest/fastest, larger = more accurate/slower |
| `whisper.device` | `cpu` | `cpu` or `cuda` (NVIDIA/AMD) |
| `whisper.compute_type` | `int8` | `int8`/`float16`/`float32` |
| `whisper.language` | `auto` | Auto-detect or specific language code |
| `whisper.hotwords` | `[]` | Words the model should favour — names, jargon |
| `hotkey.recording_hotkey` | `ctrl+win` | Configurable |
| `hotkey.recording_mode` | `push_to_talk` | `push_to_talk` (hold to talk) or `toggle` |
| `vad.vad_realtime_enabled` | `true` | Auto-stop on silence |
| `clipboard.auto_paste` | `true` | `false` = copy only |
| `clipboard.delivery_method` | `paste` | `paste` (Ctrl+V) or `type` (direct injection) |
| `voice_commands.enabled` | `true` | Enable command mode |
| `audio.host` | `null` | `WASAPI` recommended on Windows for low latency |

Full reference: [`config.defaults.yaml`](src/whisper_key/config.defaults.yaml).

---

## 🛠️ CLI Reference

```bash
whisper-local                      # Run the app (or use `wl`)
whisper-local --setup              # Interactive setup wizard (model, mode, mic)
whisper-local --doctor             # Run diagnostics
whisper-local --stats              # Transcription history & time saved
whisper-local --version            # Print version
whisper-local --quit               # Stop the running instance
whisper-local --export-settings DIR        # Back up user_settings + commands
whisper-local --import-settings DIR        # Restore from a backup
whisper-local --export-transcripts FILE    # Dump history (.txt/.md/.csv)
whisper-local --import-vocab FOLDER        # Mine a folder for hotwords
whisper-local --settings           # Open the settings GUI (no YAML editing required)
whisper-local --history            # Browse and search transcript history
whisper-local --cheat-sheet        # Show your currently configured hotkeys
whisper-local --selftest           # Run an automated self-test (mic, model, transcription)
whisper-local --bundle-logs        # Create a redacted diagnostic zip for bug reports
whisper-local --serve              # Run a local OpenAI-compatible Whisper API on :7777
whisper-local --enable-autostart   # Launch automatically at login (--disable-autostart to undo)
whisper-local --test               # Run a separate test instance (own mutex)
```

Launching while an instance is already running **takes over** — the old one is replaced cleanly, no manual quit needed.

---

## 🏗️ How it works

```
┌─────────────────────┐  ┌──────────────────┐  ┌─────────────────────┐
│  global-hotkeys /   │  │   sounddevice +  │  │  faster-whisper /   │
│  NSEvent (macOS)    │─▶│  500ms ring buf  │─▶│  ctranslate2 (GPU)  │
└─────────────────────┘  │  + TEN VAD       │  └──────────┬──────────┘
                         └──────────────────┘             │
                                                          ▼
                         ┌──────────────────┐  ┌─────────────────────┐
                         │  Voice command   │◀─│  Transcribed text   │
                         │  matcher         │  │                     │
                         └──────────────────┘  └──────────┬──────────┘
                                                          ▼
                                                ┌─────────────────────┐
                                                │  ctypes SendInput / │
                                                │  Quartz CGEvent     │
                                                │  → cursor           │
                                                └─────────────────────┘
```

---

## 🔒 Privacy pledge

Whisper Local makes the following network calls and **no others**:

1. **First launch only:** downloads the Whisper model from `huggingface.co` into your local cache.
2. **GPU onboarding (opt-in):** if you accept the GPU setup prompt, `pip install` pulls CUDA / ROCm runtime packages from PyPI / `repo.radeon.com`.

After setup, **zero network traffic**. Confirm by running `whisper-local --doctor` and inspecting the source — every network entry point lives in [`onboarding.py`](src/whisper_key/onboarding.py) and is gated behind explicit user prompts.

---

## 📦 Tech stack

`faster-whisper` · `ctranslate2` · `sounddevice` · `ten-vad` · `pyperclip` · `pystray` · `ruamel.yaml` · `playsound3`
**Windows-only:** `global-hotkeys` · `pywin32` · ctypes `SendInput`
**macOS-only:** `pyobjc-framework-Quartz` · `pyobjc-framework-ApplicationServices`

---

## 📚 Documentation

- **[docs/troubleshooting.md](docs/troubleshooting.md)** — symptom → cause → fix table for the most common issues
- **[docs/faq.md](docs/faq.md)** — privacy, comparisons (Whisper.cpp / WSR / Wispr Flow / Dragon), model picks, GPU notes
- **[docs/distribution.md](docs/distribution.md)** — how releases work (standalone `.exe`, PyPI, winget, Homebrew) and how to ship one
- **[docs/voice-commands.md](docs/voice-commands.md)** — the full voice command DSL
- **[docs/gpu-setup.md](docs/gpu-setup.md)** — manual GPU setup for NVIDIA / AMD
- **[CHANGELOG.md](CHANGELOG.md)** — release notes

Hit a wall? Run `whisper-local --doctor` or `whisper-local --selftest` first — they catch 90% of issues.

---

## 🤝 Contributing

Contributions of all kinds are welcome — bug fixes, new features, docs improvements, or just opening an issue with a clear reproduction. This project is maintained on a best-effort basis with no SLA; please be patient with response times.

```bash
git clone https://github.com/InsightfulAnalytics/whisper-local.git
pip install -e .
python -m unittest tests.test_smoke   # smoke suite — should report OK
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards. By contributing you agree your code will be MIT licensed. Found a security issue? See [SECURITY.md](SECURITY.md) — please don't open a public issue.

Good first issues are tagged [here](https://github.com/InsightfulAnalytics/whisper-local/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22). The full credit list is in [AUTHORS.md](AUTHORS.md).

---

## ☕ Support

Whisper Local is free, and it'll stay that way. If it saves you time — or a monthly subscription — the best thanks is a ⭐ on the repo and a word to anyone else who'd find it useful. That's how small projects like this one get discovered.

No pressure, though. It's yours to use either way.

---

## 🙏 Credit

Built on [whisper-key-local](https://github.com/PinW/whisper-key-local) by **Pin Wang** — thank you for the original project this fork stands on. Every open-source library Whisper Local depends on is credited in [`AUTHORS.md`](AUTHORS.md).

MIT licensed; the original copyright is preserved in [`LICENSE`](LICENSE).

---

<div align="center">

### ⭐ If this is useful to you, [star the repo](https://github.com/InsightfulAnalytics/whisper-local) — it's the easiest way to help others find it.

**Maintained by Tim ([@InsightfulAnalytics](https://github.com/InsightfulAnalytics))**

[GitHub](https://github.com/InsightfulAnalytics) · [Discussions](https://github.com/InsightfulAnalytics/whisper-local/discussions) · [Report a bug](https://github.com/InsightfulAnalytics/whisper-local/issues/new?template=bug_report.yml) · [Request a feature](https://github.com/InsightfulAnalytics/whisper-local/issues/new?template=feature_request.yml)

<sub>Tags: whisper · dictation · speech-to-text · voice-typing · transcription · ai-dictation · local-ai · offline · push-to-talk · voice-recognition · accessibility · faster-whisper · privacy · self-hosted · wispr-flow-alternative · dragon-naturallyspeaking-alternative · otter-alternative · ollama · voice-commands · windows · macos · python</sub>

</div>
