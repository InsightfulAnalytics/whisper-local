# permissions.py (Linux)
# Mirrored no-op: Hyprland lets any client in the session synthesise the paste
# chord, so there is no accessibility permission to request.


def check_accessibility_permission() -> bool:
    return True


def handle_missing_permission(config_manager) -> bool:
    return True
