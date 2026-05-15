import logging
import platform
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class LevelOverlay:
    WIDTH = 140
    HEIGHT = 18
    BG = '#0d1117'
    BAR = '#3fb950'
    DIM = '#30363d'
    BOTTOM_OFFSET_PX = 80
    LEVEL_AMP = 25.0
    UPDATE_HZ = 25

    def __init__(self, level_provider: Callable[[], float]):
        self.level_provider = level_provider
        self.root: Optional[object] = None
        self.canvas = None
        self._thread = None
        self._ready = threading.Event()
        self._showing = False
        self._smoothed = 0.0
        self._available = self._check_tk()

    def _check_tk(self) -> bool:
        try:
            import tkinter  # noqa
            return True
        except ImportError:
            logger.info("Tkinter not available; level overlay disabled")
            return False

    def start(self):
        if not self._available or (self._thread and self._thread.is_alive()):
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name='level-overlay')
        self._thread.start()
        self._ready.wait(timeout=2.0)

    def show(self):
        if not self._available or not self.root:
            return
        self._showing = True
        try:
            self.root.after(0, self._do_show)
        except Exception as e:
            logger.debug(f"Overlay show failed: {e}")

    def hide(self):
        if not self._available or not self.root:
            return
        self._showing = False
        try:
            self.root.after(0, self._do_hide)
        except Exception as e:
            logger.debug(f"Overlay hide failed: {e}")

    def shutdown(self):
        if not self.root:
            return
        try:
            self.root.after(0, self.root.destroy)
        except Exception:
            pass

    def _do_show(self):
        if self.root:
            self._smoothed = 0.0
            self.root.deiconify()
            self._update_loop()

    def _do_hide(self):
        if self.root:
            self.root.withdraw()

    def _run(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
            self.root.withdraw()
            self.root.overrideredirect(True)
            self.root.attributes('-topmost', True)
            try:
                self.root.attributes('-alpha', 0.92)
            except Exception:
                pass

            self.canvas = tk.Canvas(self.root, width=self.WIDTH, height=self.HEIGHT,
                                    bg=self.BG, highlightthickness=0,
                                    borderwidth=0)
            self.canvas.pack()

            self._position()
            self._make_click_through()
            self._ready.set()
            self.root.mainloop()
        except Exception as e:
            logger.warning(f"Level overlay thread crashed: {e}")
            self._available = False
            self._ready.set()

    def _position(self):
        try:
            self.root.update_idletasks()
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = (screen_w - self.WIDTH) // 2
            y = screen_h - self.BOTTOM_OFFSET_PX
            self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")
        except Exception as e:
            logger.debug(f"Position failed: {e}")

    def _make_click_through(self):
        if platform.system() != 'Windows':
            return
        try:
            import ctypes
            hwnd = self.root.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x80000
            WS_EX_TRANSPARENT = 0x20
            user32 = ctypes.windll.user32
            current = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        except Exception as e:
            logger.debug(f"Click-through setup failed: {e}")

    def _update_loop(self):
        if not self._showing or not self.root:
            return
        try:
            level = float(self.level_provider())
        except Exception:
            level = 0.0

        target = min(1.0, max(0.0, level * self.LEVEL_AMP))
        self._smoothed = self._smoothed * 0.55 + target * 0.45
        self._draw(self._smoothed)

        try:
            self.root.after(int(1000 / self.UPDATE_HZ), self._update_loop)
        except Exception:
            pass

    def _draw(self, level: float):
        if not self.canvas:
            return
        try:
            c = self.canvas
            c.delete('all')

            pad = 14
            bar_total_w = self.WIDTH - 2 * pad
            baseline_y = self.HEIGHT // 2

            c.create_rectangle(pad, baseline_y - 1, pad + bar_total_w, baseline_y + 1,
                               fill=self.DIM, outline='')

            fill_w = int(bar_total_w * level)
            if fill_w > 0:
                fill_h = max(3, int(self.HEIGHT * 0.6 * level + 3))
                top = baseline_y - fill_h // 2
                bottom = baseline_y + fill_h // 2
                center_x = pad + bar_total_w // 2
                left = center_x - fill_w // 2
                right = center_x + fill_w // 2
                c.create_rectangle(left, top, right, bottom,
                                   fill=self.BAR, outline='')
        except Exception:
            pass
