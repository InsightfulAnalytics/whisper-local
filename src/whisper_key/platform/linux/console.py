# console.py (Linux)
# Mirrored no-op: the console show/hide controls exist for the Windows pyapp
# build. On Linux the app runs as a user service or in a terminal the user owns.


def setup():
    pass


def owns_console():
    return False


def hide():
    pass


def show():
    pass


def is_minimized():
    return False


def start_minimize_monitor(on_minimize):
    pass
