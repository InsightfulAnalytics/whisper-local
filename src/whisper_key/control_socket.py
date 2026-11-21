# control_socket.py
# Lets other processes drive dictation over a Unix socket: on Linux, Hyprland's
# key bindings and Omarchy's dictation adapter send start/stop/toggle/cancel
# here, since Wayland gives no app a global keyboard hook. Also the
# `whisper-local-ctl` command, a lean client that never loads the app itself.

import json
import logging
import os
import queue
import socket
import sys
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# Commands that change state run one at a time, in arrival order, on a worker
# thread: a "stop" transcribes before it returns, and a push-to-talk release
# must never overtake the press that started the recording.
ACTIONS = ('start', 'stop', 'toggle', 'cancel')
QUERIES = ('status',)

_SOCKET_NAME = 'whisper-local.sock'
_TEST_SOCKET_NAME = 'whisper-local-test.sock'
_MAX_COMMAND_BYTES = 256


def socket_path(test_instance: bool = False) -> Path:
    name = _TEST_SOCKET_NAME if test_instance else _SOCKET_NAME
    runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
    if runtime_dir:
        return Path(runtime_dir) / name
    from .utils import get_user_app_data_path
    return Path(get_user_app_data_path()) / name


def is_supported() -> bool:
    return hasattr(socket, 'AF_UNIX') and sys.platform != 'win32'


# ---------------------------------------------------------------------------
# Server (runs inside the app)
# ---------------------------------------------------------------------------

class ControlServer:
    def __init__(self, state_manager, test_instance: bool = False):
        self.state_manager = state_manager
        self.path = socket_path(test_instance)
        self._listener = None
        self._actions = queue.Queue()
        self._running = False

    def start(self):
        # The single-instance lock is already held, so a socket file left here
        # belongs to a dead process and is safe to replace.
        self.path.unlink(missing_ok=True)
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(self.path))
        os.chmod(self.path, 0o600)
        listener.listen(8)
        self._listener = listener
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True, name='control-accept').start()
        threading.Thread(target=self._action_loop, daemon=True, name='control-actions').start()
        logger.info(f"Control socket listening at {self.path}")

    def stop(self):
        self._running = False
        self._actions.put(None)
        if self._listener:
            try:
                self._listener.close()
            except OSError:
                pass
            self._listener = None
        self.path.unlink(missing_ok=True)

    def _accept_loop(self):
        while self._running:
            try:
                connection, _ = self._listener.accept()
            except OSError:
                return  # listener closed by stop()
            with connection:
                try:
                    self._serve(connection)
                except Exception as e:
                    logger.warning(f"Control socket request failed: {e}")

    # One command per connection: read a line, answer with one JSON line.
    def _serve(self, connection):
        connection.settimeout(1.0)
        command = _read_line(connection).strip().lower()
        if command in ACTIONS:
            self._actions.put(command)
            reply = {'ok': True, 'queued': command}
        elif command in QUERIES:
            reply = {'ok': True, 'state': self.state_manager.get_current_state()}
        else:
            reply = {'ok': False, 'error': f"unknown command {command!r}",
                     'commands': list(ACTIONS + QUERIES)}
        connection.sendall((json.dumps(reply) + '\n').encode('utf-8'))

    def _action_loop(self):
        while True:
            command = self._actions.get()
            if command is None:
                return
            try:
                self._run(command)
            except Exception as e:
                logger.error(f"Control command {command!r} failed: {e}", exc_info=True)

    def _run(self, command: str):
        state_manager = self.state_manager
        recording = state_manager.audio_recorder.get_recording_status()
        logger.info(f"Control command: {command} (recording={recording})")
        if command == 'start':
            if not recording:
                state_manager.start_recording()
        elif command == 'stop':
            state_manager.stop_recording()
        elif command == 'toggle':
            if recording:
                state_manager.stop_recording()
            else:
                state_manager.start_recording()
        elif command == 'cancel':
            state_manager.cancel_recording_hotkey_pressed()


def _read_line(connection) -> str:
    data = b''
    while b'\n' not in data and len(data) < _MAX_COMMAND_BYTES:
        chunk = connection.recv(_MAX_COMMAND_BYTES)
        if not chunk:
            break
        data += chunk
    return data.split(b'\n', 1)[0].decode('utf-8', errors='replace')


# ---------------------------------------------------------------------------
# Client (`whisper-local-ctl`)
# ---------------------------------------------------------------------------

class NotRunning(ConnectionError):
    pass


def send_command(command: str, test_instance: bool = False, timeout: float = 2.0) -> dict:
    path = socket_path(test_instance)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        try:
            connection.connect(str(path))
        except (FileNotFoundError, ConnectionRefusedError) as e:
            raise NotRunning(f"Whisper Local is not running (no listener at {path})") from e
        connection.sendall((command.strip() + '\n').encode('utf-8'))
        return json.loads(_read_line(connection) or '{}')


# Forwards each line of stdin as one command, for as long as stdin stays open.
# Hyprland's shortcuts.lua keeps one bridge open through io.popen, so a key
# press costs a pipe write instead of starting a process. Errors are swallowed:
# a bridge that exited would break every binding until Hyprland reloads.
def _run_bridge(test_instance: bool) -> int:
    for line in sys.stdin:
        command = line.strip()
        if not command:
            continue
        try:
            send_command(command, test_instance)
        except Exception:
            pass
    return 0


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog='whisper-local-ctl',
        description='Control a running Whisper Local (start, stop, toggle, cancel, status).')
    parser.add_argument('command', nargs='?', choices=ACTIONS + QUERIES)
    parser.add_argument('--bridge', action='store_true',
                        help='Forward one command per stdin line until stdin closes')
    parser.add_argument('--test', action='store_true', help='Talk to the --test instance')
    args = parser.parse_args(argv)

    if args.bridge:
        return _run_bridge(args.test)
    if not args.command:
        parser.error('a command is required unless --bridge is given')

    try:
        reply = send_command(args.command, args.test)
    except NotRunning as e:
        print(e, file=sys.stderr)
        return 3
    print(json.dumps(reply))
    return 0 if reply.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())
