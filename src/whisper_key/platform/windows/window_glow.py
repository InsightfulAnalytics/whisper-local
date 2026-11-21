# window_glow.py
# Mirrored no-op: the edge glow indicator needs a compositor that lets an app
# draw a click-through overlay at another window's edge (Hyprland on Linux).
# The level pill still shows.


def is_supported() -> bool:
    return False


def start():
    pass


def show(state: str, level: float = 0.0):
    pass


def clear():
    pass


def stop():
    pass
