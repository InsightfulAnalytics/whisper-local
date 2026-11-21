# keyboard.py (Linux)
# Synthesises keys for paste, copy and Enter through Hyprland's send_key_state
# dispatcher, which delivers the chord with explicit modifiers to the focused
# surface whatever the user is physically holding. Typed delivery uses wtype
# (the Wayland virtual-keyboard protocol).

import logging
import shutil
import subprocess

from . import hyprland

logger = logging.getLogger(__name__)

# Gap between a synthetic key's press and release, in seconds. Omarchy's own
# universal clipboard uses 50 ms; send_key_state can leave a key stuck or
# repeating when both edges arrive together.
_delay = 0.05

_MODIFIERS = {
    'ctrl': 'CTRL', 'control': 'CTRL',
    'shift': 'SHIFT',
    'alt': 'ALT', 'option': 'ALT',
    'win': 'SUPER', 'super': 'SUPER', 'cmd': 'SUPER', 'command': 'SUPER',
}

# Key names used across the app, as XKB keysym names.
_KEYSYMS = {
    'enter': 'Return', 'return': 'Return', 'tab': 'Tab', 'space': 'space',
    'backspace': 'BackSpace', 'delete': 'Delete', 'escape': 'Escape', 'esc': 'Escape',
    'up': 'Up', 'down': 'Down', 'left': 'Left', 'right': 'Right',
    'home': 'Home', 'end': 'End', 'pageup': 'Prior', 'pagedown': 'Next', 'insert': 'Insert',
}
_KEYSYMS.update({f'f{n}': f'F{n}' for n in range(1, 13)})

# Ctrl+C and Ctrl+V in a terminal interrupt the running program and insert a
# literal ^V. Following Omarchy's universal clipboard (bindings/clipboard.lua),
# these chords gain Shift when the focused window carries the "terminal" tag.
_CLIPBOARD_KEYS = {'C', 'V', 'X'}

_LUA_TERMINAL_CHECK = """
local window = hl.get_active_window()
local terminal = false
for _, tag in ipairs(window and window.tags or {}) do
  if tag:gsub("%*$", "") == "terminal" then terminal = true end
end
"""


def validate_delivery_method(method: str) -> str:
    if method == "type" and not shutil.which('wtype'):
        print("   ✗ delivery_method 'type' needs wtype (pacman -S wtype), using 'paste'")
        return "paste"
    return method


def set_delay(delay: float):
    global _delay
    _delay = max(delay, 0.02)


def _keysym(key: str) -> str:
    name = key.lower()
    if name in _KEYSYMS:
        return _KEYSYMS[name]
    if len(name) == 1:
        return name.upper()
    return key


# Builds the Lua that presses then releases one chord. `mods` is a Lua
# expression so the terminal check can choose it at dispatch time.
def _chord_lua(mods_expression: str, keysym: str) -> str:
    delay_ms = int(_delay * 1000)
    return f"""
local mods = {mods_expression}
hl.dispatch(hl.dsp.send_key_state({{ mods = mods, key = "{keysym}", state = "down" }}))
hl.timer(function()
  hl.dispatch(hl.dsp.send_key_state({{ mods = mods, key = "{keysym}", state = "up" }}))
end, {{ timeout = {delay_ms}, type = "oneshot" }})
"""


def send_key(key: str):
    if key.lower() == 'media_play_pause':
        _toggle_media()
        return
    keysym = _keysym(key)
    logger.debug(f"Sending key: {keysym}")
    hyprland.eval_lua(_chord_lua('""', keysym))


def send_hotkey(*keys: str):
    mods = [_MODIFIERS[k.lower()] for k in keys if k.lower() in _MODIFIERS]
    regular = [_keysym(k) for k in keys if k.lower() not in _MODIFIERS]
    if len(regular) != 1:
        logger.error(f"Cannot send hotkey {'+'.join(keys)}: expected exactly one non-modifier key")
        return
    keysym = regular[0]
    plain_mods = ' '.join(mods)

    if mods == ['CTRL'] and keysym in _CLIPBOARD_KEYS:
        mods_expression = f'terminal and "CTRL SHIFT" or "{plain_mods}"'
        lua = _LUA_TERMINAL_CHECK + _chord_lua(mods_expression, keysym)
    else:
        lua = _chord_lua(f'"{plain_mods}"', keysym)

    logger.debug(f"Sending hotkey: {'+'.join(keys)}")
    hyprland.eval_lua(lua)


# Types text into the focused window. wtype reads it from stdin, so any text
# (quotes, leading dashes, newlines) reaches the app unchanged.
def type_text(text: str):
    if not text:
        return
    subprocess.run(['wtype', '-'], input=text.encode('utf-8'), check=True, timeout=30)


# The media keys are compositor bindings, which a synthetic key never reaches,
# so ask the players over MPRIS instead.
def _toggle_media():
    if not shutil.which('playerctl'):
        logger.debug("Media pause skipped: playerctl is not installed")
        return
    subprocess.run(['playerctl', 'play-pause'], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=2)
