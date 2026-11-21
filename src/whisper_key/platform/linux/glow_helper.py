# glow_helper.py (Linux)
# The process that draws the edge glow. window_glow.py starts it with
# libgtk4-layer-shell preloaded and sends it one command per line on stdin
# ("recording 0.42", "processing", "success", "failure", "hide"); it exits when
# stdin closes. It keeps a click-through layer-shell surface (never focused,
# so pastes still reach the window) parked over the bottom of the focused
# window, and draws the glow there with GTK 4, blurred on the GPU.
#
# Run by hand for testing:
#   LD_PRELOAD=libgtk4-layer-shell.so.0 python -m whisper_key.platform.linux.glow_helper

import json
import math
import os
import sys
import time

import gi

gi.require_version('Gdk', '4.0')
gi.require_version('GLibUnix', '2.0')
gi.require_version('Gsk', '4.0')
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
gi.require_foreign('cairo')

import cairo  # noqa: E402  (after require_version, as gi needs)
from gi.repository import Gdk, GLib, GLibUnix, Gsk, Gtk  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

from . import glow_shape, hyprland  # noqa: E402

NAMESPACE = 'whisper-local-glow'  # matched by the no-animation layer rule in shortcuts.lua
TRACK_MS = 80          # how often the band follows focus, moves and resizes
FPS = 60               # frames drawn per second. Not the display's frame clock: under
                       # DisplayLink it ran at about 200 Hz and cost half a core.
FADE_IN_S = 0.12
FADE_OUT_S = 0.25
RISE_S = 0.15          # level smoothing towards louder, so the glow swells rather than jumps
FALL_S = 0.5           # and towards quieter
FLASH_LEVEL = 0.55     # how full the success and failure flashes look
OUTER_BLUR = 18.0      # the soft halo
OUTER_ALPHA = 0.75
CORE_BLUR = 4.0        # the brighter line hugging the edge
CORE_ALPHA = 0.8
CORE_SCALE = 0.35
CORE_LIGHTEN = 0.25    # towards white


def _log(message: str):
    print(f'glow-helper: {message}', file=sys.stderr, flush=True)


def _rgba(hex_color: str) -> Gdk.RGBA:
    color = Gdk.RGBA()
    color.parse(hex_color)
    return color


# A widget that hands its snapshot to the overlay's painter each frame.
class GlowArea(Gtk.Widget):
    def __init__(self, painter):
        super().__init__()
        self._painter = painter

    def do_snapshot(self, snapshot):
        self._painter(snapshot, self.get_width(), self.get_height())


class GlowOverlay:
    def __init__(self):
        self.state = 'hide'
        self.target_level = 0.0
        self.level = 0.0
        self.opacity = 0.0
        self.accent = glow_shape.DEFAULT_ACCENT
        self.band = None
        self.monitors = []
        self.clock_start = time.monotonic()
        self.phases = glow_shape.Phases(0.0, 0.0, 0.0)
        self.last_frame = 0.0
        self.tick_id = None
        self.track_id = None

        self.window = Gtk.Window()
        self.window.set_decorated(False)
        self.window.add_css_class('whisper-local-glow')
        LayerShell.init_for_window(self.window)
        LayerShell.set_namespace(self.window, NAMESPACE)
        LayerShell.set_layer(self.window, LayerShell.Layer.OVERLAY)
        LayerShell.set_anchor(self.window, LayerShell.Edge.LEFT, True)
        LayerShell.set_anchor(self.window, LayerShell.Edge.TOP, True)
        LayerShell.set_exclusive_zone(self.window, -1)  # place by the monitor, ignoring the bar
        LayerShell.set_keyboard_mode(self.window, LayerShell.KeyboardMode.NONE)

        css = Gtk.CssProvider()
        css.load_from_string('window.whisper-local-glow { background: none; }')
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.area = GlowArea(self._paint)
        self.window.set_child(self.area)
        self.window.connect('map', self._make_click_through)

    # -- commands -----------------------------------------------------------

    def command(self, state: str, level: float):
        if state == 'hide':
            self.state = 'hide'  # the tick fades out, then unmaps
            return
        if self.state == 'hide':
            self.accent = glow_shape.theme_accent()
        self.state = state
        if state == 'recording':
            self.target_level = glow_shape.voice_level(level)
        elif state in ('success', 'failure'):
            self.target_level = FLASH_LEVEL
        else:
            self.target_level = 0.0
        if self.track_id is None:
            self.track_id = GLib.timeout_add(TRACK_MS, self._track)
            self._track()

    # -- placement ----------------------------------------------------------

    def _query(self, command):
        try:
            return json.loads(hyprland.request(command))
        except (hyprland.HyprlandUnavailable, OSError, ValueError) as e:
            _log(f'Hyprland query failed: {e}')
            return None

    # Follows the focused window; stops once the glow has faded out.
    def _track(self):
        if self.state == 'hide' and self.opacity <= 0.0:
            self.track_id = None
            return GLib.SOURCE_REMOVE

        window = self._query('j/activewindow') or {}
        if not self.monitors or window.get('monitor') not in {m.get('id') for m in self.monitors}:
            self.monitors = self._query('j/monitors') or []
        band = glow_shape.band_rect(window, self.monitors)
        if band != self.band:
            self._place(band)
        return GLib.SOURCE_CONTINUE

    def _place(self, band):
        previous = self.band
        self.band = band
        if band is None:
            self.window.set_visible(False)
            return
        if previous is None or previous.monitor != band.monitor:
            monitor = self._gdk_monitor(band.monitor)
            if monitor is not None:
                LayerShell.set_monitor(self.window, monitor)
        LayerShell.set_margin(self.window, LayerShell.Edge.LEFT, band.left)
        LayerShell.set_margin(self.window, LayerShell.Edge.TOP, band.top)
        self.area.set_size_request(band.width, band.height)
        self.window.set_default_size(band.width, band.height)
        if not self.window.get_visible():
            self.window.set_visible(True)
        if self.tick_id is None:
            self.last_frame = time.monotonic()
            self.tick_id = GLib.timeout_add(round(1000 / FPS), self._tick)

    def _gdk_monitor(self, connector):
        monitors = Gdk.Display.get_default().get_monitors()
        for index in range(monitors.get_n_items()):
            monitor = monitors.get_item(index)
            if monitor.get_connector() == connector:
                return monitor
        return None

    # An empty input region lets every click fall through to the window below.
    def _make_click_through(self, *_):
        surface = self.window.get_surface()
        if surface is not None:
            surface.set_input_region(cairo.Region())

    # -- animation ----------------------------------------------------------

    def _tick(self):
        now = time.monotonic()
        dt = min(0.1, now - self.last_frame)
        self.last_frame = now

        rate = RISE_S if self.target_level > self.level else FALL_S
        self.level += (self.target_level - self.level) * min(1.0, dt / rate)
        self.phases = glow_shape.advance_phases(self.phases, self.level, dt,
                                                calm=self.state == 'processing')
        if self.state == 'hide':
            self.opacity = max(0.0, self.opacity - dt / FADE_OUT_S)
        else:
            self.opacity = min(1.0, self.opacity + dt / FADE_IN_S)

        if self.state == 'hide' and self.opacity <= 0.0:
            self.window.set_visible(False)
            self.band = None
            self.tick_id = None
            return GLib.SOURCE_REMOVE
        self.area.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _paint(self, snapshot, width, height):
        if self.opacity <= 0.0 or width <= 0 or height <= 0:
            return
        seconds = time.monotonic() - self.clock_start
        calm = self.state == 'processing'
        alpha = self.opacity
        if calm:  # a slow breath while transcribing
            alpha *= 0.55 + 0.3 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.9 * seconds))
        if self.state == 'success':
            color = glow_shape.SUCCESS_COLOR
        elif self.state == 'failure':
            color = glow_shape.FAILURE_COLOR
        else:
            color = self.accent

        self._layer(snapshot, width, height, calm, color, OUTER_ALPHA * alpha, OUTER_BLUR, 1.0)
        self._layer(snapshot, width, height, calm, glow_shape.lighten(color, CORE_LIGHTEN),
                    CORE_ALPHA * alpha, CORE_BLUR, CORE_SCALE)

    def _layer(self, snapshot, width, height, calm, color, alpha, blur, scale):
        rgba = _rgba(color)
        snapshot.push_opacity(alpha)
        snapshot.push_blur(blur)
        for polygon in glow_shape.glow_polygons(width, height, self.level, self.phases, calm=calm,
                                                scale=scale, overscan=2 * blur):
            builder = Gsk.PathBuilder.new()
            builder.move_to(*polygon[0])
            for point in polygon[1:]:
                builder.line_to(*point)
            builder.close()
            snapshot.append_fill(builder.to_path(), Gsk.FillRule.WINDING, rgba)
        snapshot.pop()
        snapshot.pop()


# ---------------------------------------------------------------------------
# Command input
# ---------------------------------------------------------------------------

class CommandReader:
    def __init__(self, overlay, loop):
        self.overlay = overlay
        self.loop = loop
        self.pending = b''
        self.fd = sys.stdin.fileno()
        os.set_blocking(self.fd, False)
        GLibUnix.fd_add_full(GLib.PRIORITY_DEFAULT, self.fd,
                             GLib.IOCondition.IN | GLib.IOCondition.HUP | GLib.IOCondition.ERR,
                             self._on_input)

    def _on_input(self, fd, condition):
        try:
            data = os.read(fd, 65536)
        except BlockingIOError:
            return GLib.SOURCE_CONTINUE
        except OSError:
            data = b''
        if not data:  # the app closed the pipe or exited
            self.loop.quit()
            return GLib.SOURCE_REMOVE
        *lines, self.pending = (self.pending + data).split(b'\n')
        for line in lines:
            command = glow_shape.parse_command(line.decode('utf-8', errors='replace'))
            if command:
                self.overlay.command(*command)
        return GLib.SOURCE_CONTINUE


def main() -> int:
    if 'gtk4-layer-shell' not in os.environ.get('LD_PRELOAD', ''):
        _log('needs LD_PRELOAD=libgtk4-layer-shell.so.0 (window_glow.py sets it)')
        return 2
    Gtk.init()
    if not LayerShell.is_supported():
        _log('this compositor has no layer-shell support')
        return 3
    loop = GLib.MainLoop()
    overlay = GlowOverlay()
    CommandReader(overlay, loop)
    loop.run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
