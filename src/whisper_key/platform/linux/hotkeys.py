# hotkeys.py (Linux)
# Wayland gives no client a global keyboard grab, so on Linux the compositor
# owns the hotkeys: Hyprland binds them (see packaging/linux/shortcuts.lua) and
# sends start/stop/toggle/cancel to the app's control socket. This backend only
# accepts the bindings HotkeyListener registers, so the shared code runs as is.

import logging

logger = logging.getLogger(__name__)


def register(bindings: list):
    names = ', '.join(binding[0] for binding in bindings)
    logger.info(f"Hotkeys are bound by Hyprland, not the app; ignoring: {names}")


def start():
    pass


def stop():
    pass
