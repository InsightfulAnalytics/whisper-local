# glow_shape.py (Linux)
# The edge glow's maths, kept free of GTK so it can be tested anywhere: where
# the glow sits on screen, which colour it takes from the Omarchy theme, the
# shapes drawn each frame, and the one-line commands the app sends the helper
# process (glow_helper.py) that draws it.

import math
import os
import tomllib
from collections import namedtuple
from pathlib import Path


# ---------------------------------------------------------------------------
# Commands (app -> helper, one per line on the helper's stdin)
# ---------------------------------------------------------------------------

# "recording 0.42" carries the voice level (0 to 1); the others ignore it.
STATES = ('recording', 'processing', 'success', 'failure', 'hide')


def format_command(state: str, level: float = 0.0) -> str:
    return f'{state} {max(0.0, min(1.0, level)):.3f}\n'


# Returns (state, level), or None for a line that isn't a command.
def parse_command(line: str):
    parts = line.split()
    if not parts or parts[0] not in STATES:
        return None
    try:
        level = float(parts[1]) if len(parts) > 1 else 0.0
    except ValueError:
        level = 0.0
    return parts[0], max(0.0, min(1.0, level))


# ---------------------------------------------------------------------------
# Placement: a band across the bottom of the focused window
# ---------------------------------------------------------------------------

BAND_FRACTION = 0.2  # of the window's height
BAND_MIN = 120
BAND_MAX = 300

# monitor: connector name ("DP-1"); left/top: logical pixels from the monitor's
# top-left corner, as a layer-shell surface's margins are measured.
Band = namedtuple('Band', 'monitor left top width height')


def band_height(window_height: int) -> int:
    wanted = max(BAND_MIN, min(BAND_MAX, round(window_height * BAND_FRACTION)))
    return max(1, min(window_height, wanted))


# A monitor's size in logical pixels (Hyprland reports physical pixels).
def _logical_size(monitor):
    scale = monitor.get('scale') or 1.0
    width, height = monitor['width'] / scale, monitor['height'] / scale
    if monitor.get('transform', 0) % 2 == 1:  # rotated a quarter turn
        width, height = height, width
    return round(width), round(height)


# window and monitors are Hyprland's "j/activewindow" and "j/monitors" replies.
# With no focused window (an empty workspace) the band spans the bottom of the
# focused monitor instead, so recording still shows. Returns None when there
# is nowhere to draw.
def band_rect(window, monitors):
    monitor = None
    if window and window.get('size'):
        monitor = next((m for m in monitors if m.get('id') == window.get('monitor')), None)
    if monitor is None:
        window = None
        monitor = next((m for m in monitors if m.get('focused')), None)
    if monitor is None:
        return None

    monitor_width, monitor_height = _logical_size(monitor)
    if window:
        left = window['at'][0] - monitor['x']
        top = window['at'][1] - monitor['y']
        right = left + window['size'][0]
        bottom = top + window['size'][1]
    else:
        left, top, right, bottom = 0, 0, monitor_width, monitor_height

    # Clip to the monitor, so a window hanging off one still glows on screen.
    left, top = max(0, left), max(0, top)
    right, bottom = min(monitor_width, right), min(monitor_height, bottom)
    if right <= left or bottom <= top:
        return None
    height = band_height(bottom - top)
    return Band(monitor['name'], left, bottom - height, right - left, height)


# ---------------------------------------------------------------------------
# Colour: the Omarchy theme's accent, as Omarchy's own widgets use
# ---------------------------------------------------------------------------

DEFAULT_ACCENT = '#33c3ff'
SUCCESS_COLOR = '#3fb950'
FAILURE_COLOR = '#f85149'


def _theme_files(environ):
    home = Path(environ.get('HOME') or Path.home())
    state = Path(environ.get('XDG_STATE_HOME') or home / '.local' / 'state')
    config = Path(environ.get('XDG_CONFIG_HOME') or home / '.config')
    return (state / 'omarchy' / 'current' / 'theme' / 'colors.toml',
            config / 'omarchy' / 'current' / 'theme' / 'colors.toml')


# Read on every show, so a theme change applies from the next recording.
def theme_accent(environ=None) -> str:
    for path in _theme_files(os.environ if environ is None else environ):
        try:
            accent = tomllib.loads(path.read_text(encoding='utf-8')).get('accent', '')
        except (OSError, tomllib.TOMLDecodeError):
            continue
        if isinstance(accent, str) and len(accent) == 7 and accent.startswith('#'):
            try:
                int(accent[1:], 16)
            except ValueError:
                continue
            return accent.lower()
    return DEFAULT_ACCENT


def lighten(hex_color: str, amount: float) -> str:
    channels = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(c + (255 - c) * amount) for c in channels]
    return '#' + ''.join(f'{c:02x}' for c in mixed)


# ---------------------------------------------------------------------------
# Shapes: one frame of the glow
# ---------------------------------------------------------------------------

# Levels under this are room noise and draw as silence, so the glow rests
# still instead of twitching with every breath and keyboard click.
REST_GATE = 0.15


def voice_level(level: float) -> float:
    level = max(0.0, min(1.0, level))
    return max(0.0, (level - REST_GATE) / (1.0 - REST_GATE))


# Wave positions in radians. The helper advances them a frame at a time, so
# the voice changes how fast the waves flow, never where they are: computing
# them as speed x clock made every level change jump the waves.
Phases = namedtuple('Phases', 'long short sway')


def advance_phases(phases, level, dt, calm=False):
    level = 0.0 if calm else max(0.0, min(1.0, level))
    turn = 2 * math.pi
    return Phases((phases.long + (0.45 + 1.8 * level) * dt) % turn,
                  (phases.short + (0.3 + 1.2 * level) * dt) % turn,
                  (phases.sway + 0.6 * dt) % turn)


# One frame as filled polygons in band coordinates (y grows downwards and the
# window's bottom edge is y = height): a band along the bottom edge whose top
# ripples like a sound wave, and a tapering strip climbing each side.
#   level:    voice level, 0 to 1 (after voice_level); louder is thicker and taller
#   phases:   wave positions, from advance_phases
#   calm:     processing: no voice
#   scale:    thickness multiplier (the bright core is a thinner copy)
#   overscan: pixels the shapes run past the band's left, right and bottom,
#             so a blur doesn't fade at the band's edges
def glow_polygons(width, height, level, phases, calm=False, scale=1.0, overscan=0.0):
    level = 0.0 if calm else max(0.0, min(1.0, level))
    base = (9.0 + 12.0 * level) * scale
    ripple = (3.0 + 18.0 * level) * scale
    long_wave = max(220.0, width / 2.3)
    short_wave = max(120.0, width / 5.3)

    # Both waves flow the same way, so they swell and pass rather than wobble.
    steps = max(24, int(width / 16))
    top_edge = []
    for i in range(steps + 1):
        x = width * i / steps
        wave = 0.62 * math.sin(2 * math.pi * x / long_wave - phases.long) \
            + 0.38 * math.sin(2 * math.pi * x / short_wave - phases.short + 1.3)
        top_edge.append((x, height - (base + ripple * (0.5 + 0.5 * wave))))

    bottom = height + overscan
    band = [(-overscan, bottom), (-overscan, top_edge[0][1]), *top_edge,
            (width + overscan, top_edge[-1][1]), (width + overscan, bottom)]

    # Side strips: pool in the corners, rise with the voice and sway gently,
    # out of step with each other.
    rise_fraction = 0.4 if calm else 0.5 + 0.45 * level
    side_width = base * 2.4
    sides = []
    for side, offset in ((0, 0.0), (1, 2.1)):
        rise = height * rise_fraction * (1 + 0.05 * math.sin(phases.sway + offset))
        # Capped so the blur's halo still fits under the band's top edge.
        rise = max(0.0, min(height - overscan, rise))
        strip = [(-overscan, bottom), (-overscan, height - rise)]
        for i in range(1, 13):
            along = i / 12  # 0 at the top of the strip, 1 at the bottom
            strip.append((side_width * along ** 2.2, height - rise + rise * along))
        strip.append((side_width, bottom))
        if side == 1:  # mirror onto the right-hand edge
            strip = [(width - x, y) for x, y in strip]
        sides.append(strip)
    return [band, *sides]
