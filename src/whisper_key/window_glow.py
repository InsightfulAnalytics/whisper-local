# window_glow.py
# A recording indicator drawn at the edge of the window you're dictating into.
# A glow in your theme's accent colour pools along the window's bottom edge
# and ripples with your voice; it breathes while transcribing and flashes
# green or red with the result. The platform backend draws it (on Linux a
# helper process with a Hyprland layer-shell overlay); elsewhere the backend
# reports itself unsupported and only the level pill shows.

import logging
import threading
import time

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Indicator (same calls as LevelOverlay, driven through RecordingIndicators)
# ---------------------------------------------------------------------------

def _load_backend():
    try:
        from .platform import window_glow
        return window_glow
    except ImportError:
        return None


# The backend draws; this class decides what to show. Each frame it sends the
# backend a state ("recording", "processing", "success" or "failure") and,
# while recording, the smoothed voice level from 0 to 1.
class WindowGlow:
    FPS = 30
    LEVEL_AMP = 25.0         # same scaling as LevelOverlay: normal speech reads as full
    DECAY = 0.85             # per frame; rises at once, falls over about a quarter second
    SUCCESS_S = 0.4
    FAILURE_S = 0.9

    def __init__(self, level_provider):
        self.level_provider = level_provider
        self._backend = _load_backend()
        self._mode = 'hidden'
        self._flash_state = None
        self._flash_until = 0.0
        self._smoothed = 0.0
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
        try:
            self._backend.start()  # warm up now, so the first recording shows at once
        except Exception as e:
            logger.warning(f"Window glow could not start: {e}")
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
        self._flash('success', self.SUCCESS_S)

    def flash_failure(self, message: str = None):
        self._flash('failure', self.FAILURE_S)

    def shutdown(self):
        self._running = False
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        self._clear()
        try:
            self._backend.stop()
        except Exception as e:
            logger.debug(f"Window glow stop failed: {e}")

    def _set_mode(self, mode: str):
        with self._lock:
            self._mode = mode
            if mode == 'recording':
                self._smoothed = 0.0
        self._wake.set()

    def _flash(self, state: str, seconds: float):
        with self._lock:
            self._mode = 'flash'
            self._flash_state = state
            self._flash_until = time.monotonic() + seconds
        self._wake.set()

    # Sends one frame per tick while a mode is showing; sleeps while hidden.
    def _run(self):
        while self._running:
            if self._mode == 'hidden':
                self._clear()
                self._wake.wait()
                self._wake.clear()
                continue

            frame = self._next_frame(time.monotonic())
            if frame is None:
                self._set_mode('hidden')
                continue
            try:
                self._backend.show(*frame)
                self._painted = True
            except Exception as e:
                logger.debug(f"Window glow frame failed: {e}")
            time.sleep(1.0 / self.FPS)

    # Returns (state, level) for this frame, or None once a flash has ended.
    def _next_frame(self, now: float):
        with self._lock:
            mode = self._mode
            flash_state = self._flash_state
            flash_until = self._flash_until

        if mode == 'flash':
            return None if now >= flash_until else (flash_state, 0.0)

        if mode == 'recording':
            try:
                level = float(self.level_provider())
            except Exception:
                level = 0.0
            target = min(1.0, max(0.0, level * self.LEVEL_AMP))
            self._smoothed = max(target, self._smoothed * self.DECAY)
            return ('recording', self._smoothed)

        if mode == 'processing':
            return ('processing', 0.0)

        return None

    def _clear(self):
        if not self._painted:
            return
        try:
            self._backend.clear()
        except Exception as e:
            logger.debug(f"Window glow clear failed: {e}")
        self._painted = False
