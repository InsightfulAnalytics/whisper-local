# Whisper Local - Speech-to-Text

Global hotkeys to record speech and transcribe directly to your cursor.

> **Personal fork.** This is `drajb`'s personal fork of [`PinW/whisper-key-local`](https://github.com/PinW/whisper-key-local). See attribution at the bottom.

## ✨ Features

- **Global Hotkey**: Start recording speech from any app
- **Auto-Paste**: Transcribe directly to cursor
- **Auto-Send**: Optionally auto-send with ENTER keypress
- **Local/Offline**: Voice data never leaves your computer
- **CPU Ready**: Small, efficient models available
- **GPU Ready**: Support for both NVIDIA & AMD cards
- **Cross-platform**: Works on Windows and macOS
- **Voice Commands**: Trigger shortcuts, text snippets, and shell commands by voice — [docs](docs/voice-commands.md)
- **Configurable**: Customize hotkeys, models, and [much more](#️-configuration)

## 🚀 Quick Start

### From Source (recommended for this fork)

Requires Python 3.11–3.13.

```bash
git clone https://github.com/drajb/whisper-local.git
cd whisper-local
pip install -e .
python whisper-local.py
```

After installation, the CLI is available as `whisper-local` (or `wl` for short).

### Windows App

Use the build script in [`pyapp-build/`](pyapp-build/) to produce a standalone exe — see [`pyapp-build/CLAUDE.md`](pyapp-build/CLAUDE.md).

## 🎤 Basic Usage

| Hotkey | Windows | macOS |
|--------|---------|-------|
| Start recording | `Ctrl+Win` | `Fn+Ctrl` |
| Stop & transcribe | `Ctrl` | `Fn` |
| Stop & auto-send | `Alt` | `Option` |
| Cancel recording | `Esc` | `Shift` |
| Voice command mode | `Alt+Win` | `Fn+Command` |

Open the system tray / menu bar icon to:
- Toggle auto-paste vs clipboard-only
- Change transcription model
- Select audio device

## 🗣️ Voice Commands

Speak trigger phrases to run shell commands and more. Define in:
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

See the **[Voice Commands Guide](docs/voice-commands.md)** for full details.

> **Heads-up on shell commands.** Voice commands with `run:` execute through your system shell. Only add commands you trust, since anything in `commands.yaml` will run with your user privileges.

## ⚡ GPU Acceleration

Whisper Local detects your GPU on first launch and offers one-press install of the required runtime libraries. Supports **NVIDIA** (CUDA) and **AMD** (ROCm).

> **Note on AMD ROCm wheels.** The optional AMD ROCm setup downloads CTranslate2 wheels from the upstream maintainer's GitHub releases ([`PinW/ctranslate2-rocm-wheels`](https://github.com/PinW/ctranslate2-rocm-wheels)). NVIDIA setup uses official `nvidia-*` packages from PyPI.

For manual setup or troubleshooting, see the **[GPU Setup Guide](docs/gpu-setup.md)**.

## ⚙️ Configuration

Local settings at:
- **Windows:** `%APPDATA%\whisperkey\user_settings.yaml`
- **macOS:** `~/.whisperkey/user_settings.yaml`

Delete this file and restart the app to reset to defaults.

| Option | Default | Notes |
|--------|---------|-------|
| **Whisper** |||
| `whisper.model` | `tiny` | Any model defined in `whisper.models` |
| `whisper.device` | `cpu` | cpu or cuda (NVIDIA/AMD GPU) — [setup guide](docs/gpu-setup.md) |
| `whisper.compute_type` | `int8` | int8/float16/float32 |
| `whisper.language` | `auto` | auto or language code (en, es, fr, etc.) |
| `whisper.beam_size` | `5` | Higher = more accurate but slower (1-10) |
| `whisper.models` | (see config) | Add custom HuggingFace or local models |
| **Hotkeys** |||
| `hotkey.recording_hotkey` | `ctrl+win` / `fn+ctrl` | Windows / macOS |
| `hotkey.stop_key` | `ctrl` / `fn` | Stop recording |
| `hotkey.auto_send_key` | `alt` / `option` | Stop + paste + Enter |
| `hotkey.cancel_combination` | `esc` / `shift` | Cancel recording |
| `hotkey.command_hotkey` | `alt+win` / `fn+command` | Voice command mode |
| **Voice Activity Detection** |||
| `vad.vad_precheck_enabled` | `true` | Prevent hallucinations on silence |
| `vad.vad_onset_threshold` | `0.7` | Speech detection start (0.0-1.0) |
| `vad.vad_offset_threshold` | `0.55` | Speech detection end (0.0-1.0) |
| `vad.vad_min_speech_duration` | `0.1` | Min speech segment (seconds) |
| `vad.vad_realtime_enabled` | `true` | Auto-stop on silence |
| `vad.vad_silence_timeout_seconds` | `30.0` | Seconds before auto-stop |
| **Audio** |||
| `audio.host` | `null` | Audio API (WASAPI, Core Audio, etc.) |
| `audio.channels` | `1` | 1 = mono, 2 = stereo |
| `audio.dtype` | `float32` | float32/int16/int24/int32 |
| `audio.max_duration` | `900` | Max recording seconds (0 = unlimited) |
| `audio.input_device` | `default` | Device ID or "default" |
| **Clipboard** |||
| `clipboard.auto_paste` | `true` | false = clipboard only |
| `clipboard.delivery_method` | `paste` | paste (Ctrl+V) or type (direct injection) |
| `clipboard.paste_hotkey` | `ctrl+v` / `cmd+v` | Paste key simulation |
| `clipboard.paste_preserve_clipboard` | `true` | Restore clipboard after paste |
| **Logging** |||
| `logging.level` | `INFO` | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `logging.file.enabled` | `true` | Write to app.log |
| `logging.console.enabled` | `true` | Print to console |
| `logging.console.level` | `WARNING` | Console verbosity |
| **Audio Feedback** |||
| `audio_feedback.enabled` | `true` | Play sounds on record/stop |
| `audio_feedback.transcription_complete_enabled` | `false` | Play sound on transcription complete |
| `audio_feedback.start_sound` | `assets/sounds/...` | Custom sound file path |
| `audio_feedback.stop_sound` | `assets/sounds/...` | Custom sound file path |
| `audio_feedback.cancel_sound` | `assets/sounds/...` | Custom sound file path |
| `audio_feedback.transcription_complete_sound` | `assets/sounds/...` | Custom sound file path |
| **System Tray** |||
| `system_tray.enabled` | `true` | Show tray icon |
| `system_tray.tooltip` | `Whisper Local` | Hover text |
| **Voice Commands** |||
| `voice_commands.enabled` | `true` | Enable voice command mode |

## 📁 Model Cache

Default path for transcription models (via HuggingFace):
- **Windows:** `%USERPROFILE%\.cache\huggingface\hub\`
- **macOS:** `~/.cache/huggingface/hub/`

## 📦 Dependencies

**Cross-platform:**
`faster-whisper` · `numpy` · `sounddevice` · `soxr` · `pyperclip` · `ruamel.yaml` · `pystray` · `Pillow` · `playsound3` · `ten-vad` · `hf-xet`

**Windows:** `global-hotkeys` · `pywin32`

**macOS:** `pyobjc-framework-Quartz` · `pyobjc-framework-ApplicationServices`

---

## 🙏 Attribution

This is a personal fork of **[whisper-key-local](https://github.com/PinW/whisper-key-local)** by **Pin Wang ([@PinW](https://github.com/PinW))**. All credit for the original design, implementation, and ongoing work goes to the upstream author. The original project is licensed under MIT and the original copyright is preserved in [`LICENSE`](LICENSE).

This fork exists for personal use and experimentation. For the official project, releases, community, and support, please visit the upstream repo.
