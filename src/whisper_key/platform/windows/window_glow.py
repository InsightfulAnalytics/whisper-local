# window_glow.py
# Mirrored no-op: the window-border glow indicator needs a compositor that can
# restyle another app's window (Hyprland on Linux). The level pill still shows.


def is_supported() -> bool:
    return False


def paint(gradient: str, border_size: int = 0):
    pass


def clear():
    pass
