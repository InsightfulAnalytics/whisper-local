# window_glow.py
# A recording indicator drawn on the focused window itself. While you dictate,
# the window's border glows in a flowing gradient that brightens and speeds up
# with your voice; it pulses amber while transcribing and flashes green or red
# with the result. Needs a compositor that can restyle a window's border
# (Hyprland on Linux); elsewhere the platform backend reports it unsupported.

import logging
import math
import threading
import time

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Frame maths (pure, so the look can be tested without a compositor)
# ---------------------------------------------------------------------------

RECORDING_COLORS = ('00e5ff', '7c4dff', '00e5ff')  # cyan to violet and back, so the turn is seamless
PROCESSING_COLOR = 'ffb000'
SUCCESS_COLOR = '3fb950'
FAILURE_COLOR = 'f85149'


def _mix_towards_white(hex_color: str, amount: float) -> str:
    channels = [int(hex_color[i:i + 2], 16) for i in (0, 2, 4)]
    mixed = [round(c + (255 - c) * amount) for c in channels]
    return ''.join(f'{c:02x}' for c in mixed)


def _alpha_hex(alpha: float) -> str:
    return f'{round(max(0.0, min(1.0, alpha)) * 255):02x}'


# Hyprland gradient syntax: "rgba(rrggbbaa) rgba(rrggbbaa) ... <angle>deg".
def gradient(colors, alpha: float, angle: float) -> str:
    stops = ' '.join(f'rgba({color}{_alpha_hex(alpha)})' for color in colors)
    return f'{stops} {int(angle) % 360}deg'


# Louder speech: brighter, more opaque, and the colours flare towards white.
def recording_gradient(level: float, angle: float) -> str:
    level = max(0.0, min(1.0, level))
    colors = [_mix_towards_white(color, 0.35 * level) for color in RECORDING_COLORS]
    return gradient(colors, 0.35 + 0.65 * level, angle)


# A slow breathing pulse, phase in seconds.
def processing_gradient(phase: float, angle: float) -> str:
    breath = 0.5 + 0.5 * math.sin(phase * 2 * math.pi * 1.2)
    return gradient((PROCESSING_COLOR, _mix_towards_white(PROCESSING_COLOR, 0.4)), 0.45 + 0.4 * breath, angle)


# ---------------------------------------------------------------------------
# Indicator (same calls as LevelOverlay, driven through RecordingIndicators)
# ---------------------------------------------------------------------------

def _load_backend():
    try:
        from .platform import window_glow
        return window_glow
    except ImportError:
        return None


class WindowGlow:
    FPS = 30
    LEVEL_AMP = 25.0         # same scaling as LevelOverlay: normal speech reads as full
    DECAY = 0.85             # per frame; rises at once, falls over about a quarter second
    BASE_SPEED_DEG = 40.0    # gradient turn per second in silence
    VOICE_SPEED_DEG = 400.0  # extra turn per second at full level
    SUCCESS_S = 0.4
    FAILURE_S = 0.9

    def __init__(self, level_provider, border_size: int = 0):
        self.level_provider = level_provider
        self.border_size = max(0, int(border_size or 0))
        self._backend = _load_backend()
        self._mode = 'hidden'
        self._flash_color = None
        self._flash_until = 0.0
        self._mode_started = 0.0
        self._smoothed = 0.0
        self._angle = 0.0
        self._painted = False
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._running = False
        self._thread = None

    @property
    def available(self) -> bool:
        try:
            return self._backend is not None and self._backend.is_supported()
        except Exception:
            return False

    def start(self):
        if self._thread or not self.available:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name='window-glow')
        self._thread.start()
        logger.info("Window glow indicator enabled")

    def show_recording(self):
        self._set_mode('recording')

    def show_processing(self):
        self._set_mode('processing')

    def hide(self):
        self._set_mode('hidden')

    def flash_success(self):
        self._flash(SUCCESS_COLOR, self.SUCCESS_S)

    def flash_failure(self, message: str = None):
        self._flash(FAILURE_COLOR, self.FAILURE_S)

    def shutdown(self):
        self._running = False
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        self._clear()

    def _set_mode(self, mode: str):
        with self._lock:
            self._mode = mode
            self._mode_started = time.monotonic()
            if mode == 'recording':
                self._smoothed = 0.0
        self._wake.set()

    def _flash(self, color: str, seconds: float):
        with self._lock:
            self._mode = 'flash'
            self._flash_color = color
            self._flash_until = time.monotonic() + seconds
        self._wake.set()

    # Paints one frame per tick while a mode is showing; sleeps while hidden.
    def _run(self):
        last = time.monotonic()
        while self._running:
            if self._mode == 'hidden':
                self._clear()
                self._wake.wait()
                self._wake.clear()
                last = time.monotonic()
                continue

            now = time.monotonic()
            frame = self._next_frame(now, now - last)
            last = now
            if frame is None:
                self._set_mode('hidden')
                continue
            try:
                self._backend.paint(frame, self.border_size)
                self._painted = True
            except Exception as e:
                logger.debug(f"Window glow paint failed: {e}")
            time.sleep(1.0 / self.FPS)

    def _next_frame(self, now: float, dt: float):
        with self._lock:
            mode = self._mode
            started = self._mode_started
            flash_color = self._flash_color
            flash_until = self._flash_until

        if mode == 'flash':
            if now >= flash_until:
                return None
            return gradient((flash_color, flash_color), 1.0, 0)

        if mode == 'recording':
            try:
                level = float(self.level_provider())
            except Exception:
                level = 0.0
            target = min(1.0, max(0.0, level * self.LEVEL_AMP))
            self._smoothed = max(target, self._smoothed * self.DECAY)
            self._angle = (self._angle + (self.BASE_SPEED_DEG + self.VOICE_SPEED_DEG * self._smoothed) * dt) % 360
            return recording_gradient(self._smoothed, self._angle)

        if mode == 'processing':
            self._angle = (self._angle + self.BASE_SPEED_DEG * dt) % 360
            return processing_gradient(now - started, self._angle)

        return None

    def _clear(self):
        if not self._painted:
            return
        try:
            self._backend.clear()
        except Exception as e:
            logger.debug(f"Window glow clear failed: {e}")
        self._painted = False
