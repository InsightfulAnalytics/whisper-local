# hyprland.py (Linux)
# Minimal client for Hyprland's IPC socket, shared by the Linux backends. One
# request per connection, as hyprctl does, without spawning hyprctl itself:
# a paste goes through here, so it should cost microseconds, not a process.

import os
import socket

# Hyprland 0.56+ (Lua config) answers "eval <lua>" with "ok" or "error: ...".
_EVAL_OK = 'ok'


class HyprlandUnavailable(RuntimeError):
    pass


def _socket_path() -> str:
    signature = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE')
    runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
    if not signature or not runtime_dir:
        raise HyprlandUnavailable("Not running under Hyprland (HYPRLAND_INSTANCE_SIGNATURE unset)")
    return os.path.join(runtime_dir, 'hypr', signature, '.socket.sock')


def is_available() -> bool:
    try:
        return os.path.exists(_socket_path())
    except HyprlandUnavailable:
        return False


# Sends one command (for example "j/activewindow") and returns the full reply.
def request(command: str, timeout: float = 1.0) -> str:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        try:
            connection.connect(_socket_path())
        except OSError as e:
            raise HyprlandUnavailable(f"Cannot reach Hyprland's socket: {e}") from e
        connection.sendall(command.encode('utf-8'))
        chunks = []
        while True:
            chunk = connection.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    return b''.join(chunks).decode('utf-8', errors='replace')


# Runs a Lua snippet inside Hyprland. Raises when the snippet fails, so a
# paste that never happened is logged as a failure rather than a success.
def eval_lua(code: str):
    reply = request(f'eval {code}').strip()
    if reply != _EVAL_OK:
        raise RuntimeError(f"Hyprland rejected the Lua snippet: {reply}")
