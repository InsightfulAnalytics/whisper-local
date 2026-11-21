# app.py (Linux)
# Process-level hooks the entry point calls: a native-runtime preflight (nothing
# to check on Linux), the main loop the tray icon needs, and a raw single-key
# read for the terminal prompts.

import sys


# Mirrored no-op of the Windows MSVC-runtime preflight: Linux wheels link
# against the system C++ runtime, which the package manager keeps current.
def native_runtime_status():
    return ("", None)


def setup():
    pass


# The tray icon (pystray's AppIndicator backend, started with run_detached)
# only registers with the bar while a GLib main loop runs, so the main thread
# runs one, as macOS runs its NSApplication loop. The 100 ms check is also what
# lets Python's SIGINT/SIGTERM handlers run while the loop sits in C code.
def run_event_loop(shutdown_event):
    try:
        from gi.repository import GLib
    except ImportError:
        while not shutdown_event.wait(timeout=0.1):
            pass
        return

    loop = GLib.MainLoop()

    def quit_on_shutdown():
        if shutdown_event.is_set():
            loop.quit()
            return False
        return True

    GLib.timeout_add(100, quit_on_shutdown)
    loop.run()


# Reads one keypress without waiting for Enter, for terminal_ui prompts.
def getch():
    import termios
    import tty
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
