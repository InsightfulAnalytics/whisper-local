#!/bin/bash

# Installs Whisper Local on Omarchy (Arch Linux, Hyprland) from this checkout:
# an editable install in its own virtual environment, the Omarchy dictation
# adapter, the Hyprland bindings and a systemd user service. Safe to re-run,
# and re-run it after a system Python upgrade. It does not switch dictation
# over; run `whisper-local-use whisper-local` for that.

set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
here="$repo/packaging/linux"
venv="${XDG_DATA_HOME:-$HOME/.local/share}/whisper-local/venv"
config="${XDG_CONFIG_HOME:-$HOME/.config}"
bin="$HOME/.local/bin"

# PortAudio for the microphone, libc++ for ten-vad, wl-clipboard for paste, Tk for the overlay and
# settings windows, PyGObject and Ayatana AppIndicator for the tray icon, gtk4-layer-shell for the
# edge glow.
missing=()
for package in portaudio libc++ wl-clipboard tk python-gobject libayatana-appindicator gtk4-layer-shell; do
  pacman -Q "$package" &>/dev/null || missing+=("$package")
done
if ((${#missing[@]})); then
  echo "Install these first: sudo pacman -S --needed ${missing[*]}" >&2
  exit 1
fi

# The system Python, with its site-packages visible, so the tray can use the
# system's PyGObject (it has no wheel). --seed adds pip for GPU onboarding.
uv venv --quiet --allow-existing --seed --python /usr/bin/python3 --system-site-packages "$venv"

# The CUDA extra brings CUDA 12's cuBLAS, which ctranslate2's wheel needs.
target="$repo"
if command -v nvidia-smi &>/dev/null; then
  target="$repo[cuda]"
fi
VIRTUAL_ENV="$venv" uv pip install --quiet --editable "$target"

mkdir -p "$bin"
ln -sf "$venv/bin/whisper-local" "$bin/whisper-local"
ln -sf "$venv/bin/whisper-local-ctl" "$bin/whisper-local-ctl"
install -m755 "$here/omarchy-dictation-whisper-local" "$here/whisper-local-use" "$bin/"
install -Dm644 "$here/shortcuts.lua" "$config/whisper-local/shortcuts.lua"
install -Dm644 "$here/whisper-local.service" "$config/systemd/user/whisper-local.service"
systemctl --user daemon-reload

echo "Whisper Local is installed. To dictate with it: whisper-local-use whisper-local"
