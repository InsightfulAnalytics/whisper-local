# Whisper Local on Linux (Omarchy)

Linux support targets [Omarchy](https://omarchy.org): Arch Linux with the Hyprland
compositor (0.56 or later, Lua config). Wayland lets no app watch the keyboard
globally, so Hyprland owns the hotkeys and forwards them to the app's control
socket. Whisper Local plugs into Omarchy's dictation backends, beside
Superwhisper and Voxtype, and uses the same keys they do.

## Install

```bash
sudo pacman -S --needed portaudio libc++ wl-clipboard tk python-gobject libayatana-appindicator uv
packaging/linux/install.sh
whisper-local-use whisper-local
```

`install.sh` makes an editable install in `~/.local/share/whisper-local/venv`, so
changes to this checkout take effect when the service restarts. With an NVIDIA
GPU it also installs CUDA 12's cuBLAS (`nvidia-cublas-cu12`, about 1 GB), which
ctranslate2 needs. Re-run it after Arch upgrades the system Python.

## Keys

| Key | Action | Bound by |
| --- | --- | --- |
| Alt+Space | Start or stop dictation | Omarchy |
| Hold Right Alt | Push to talk | Omarchy |
| Ctrl+Alt+Space | Start or stop dictation | `shortcuts.lua` |
| Escape | Cancel a recording (still reaches the app) | `shortcuts.lua` |

Omarchy's keys call `omarchy-dictation-whisper-local`. Edit
`~/.config/whisper-local/shortcuts.lua` to change the others, then
`hyprctl reload`. The `hotkey` section of `user_settings.yaml` does nothing on Linux.

## Switching backends

```bash
whisper-local-use                 # which backend is selected
whisper-local-use whisper-local
whisper-local-use superwhisper
```

The switch saves Omarchy's default dictation backend, stops the other backend's
service and turns off its start at login, starts this one, and reloads Hyprland
so the right `shortcuts.lua` is loaded. Nothing is uninstalled.

## Control from scripts

```bash
whisper-local-ctl toggle          # also start, stop, cancel, status
```

Exit status 3 means the app is not running.

## Files

| Path | What |
| --- | --- |
| `~/.config/whisperkey/` | Settings (`user_settings.yaml`), `app.log`, history |
| `~/.config/whisper-local/shortcuts.lua` | Hyprland bindings |
| `~/.config/systemd/user/whisper-local.service` | The service |
| `$XDG_RUNTIME_DIR/whisper-local.sock` | Control socket |

`journalctl --user -u whisper-local` shows the console output.

## How text reaches the app

Paste copies the text with `wl-copy`, then sends Ctrl+V through Hyprland's
`send_key_state` dispatcher, which works whatever keys are still held. In a
window tagged `terminal` it sends Ctrl+Shift+V (and Ctrl+Shift+C instead of
Ctrl+C), as Omarchy's universal clipboard does. `delivery_method: type` types
the text with `wtype` instead.
