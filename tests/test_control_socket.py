# test_control_socket.py
# Covers the `whisper-local-ctl --bridge` handover: a new bridge must retire the
# one it replaces, because a Hyprland reload cannot always make the old one exit,
# and must never kill an unrelated process that reused the old bridge's PID.
# Standard library only, so CI's lean job can run it; Linux only (/proc).

import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from whisper_key import control_socket  # noqa: E402


# A stand-in process. Its command line names whisper-local-ctl and --bridge
# when asked to, which is all the retire check looks at.
def _start_sleeper(looks_like_bridge: bool) -> subprocess.Popen:
    args = [sys.executable, "-c", "import time; time.sleep(60)"]
    if looks_like_bridge:
        args += ["/home/user/.local/bin/whisper-local-ctl", "--bridge"]
    return subprocess.Popen(args)


@unittest.skipUnless(sys.platform.startswith("linux"), "reads /proc")
class RetirePreviousBridgeTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pid_path = Path(self.tmp.name) / "bridge.pid"
        self.processes = []

    def tearDown(self):
        for process in self.processes:
            process.kill()
            process.wait()
        self.tmp.cleanup()

    def _sleeper(self, looks_like_bridge: bool) -> subprocess.Popen:
        process = _start_sleeper(looks_like_bridge)
        self.processes.append(process)
        return process

    def test_previous_bridge_is_terminated_and_replaced(self):
        old_bridge = self._sleeper(looks_like_bridge=True)
        self.pid_path.write_text(str(old_bridge.pid))

        control_socket._retire_previous_bridge(self.pid_path)

        self.assertIsNotNone(old_bridge.wait(timeout=5))
        self.assertEqual(self.pid_path.read_text(), str(control_socket.os.getpid()))

    def test_recycled_pid_is_left_alone(self):
        unrelated = self._sleeper(looks_like_bridge=False)
        self.pid_path.write_text(str(unrelated.pid))

        control_socket._retire_previous_bridge(self.pid_path)

        self.assertIsNone(unrelated.poll())
        self.assertEqual(self.pid_path.read_text(), str(control_socket.os.getpid()))

    def test_missing_or_garbled_pid_file_is_tolerated(self):
        control_socket._retire_previous_bridge(self.pid_path)
        self.assertEqual(self.pid_path.read_text(), str(control_socket.os.getpid()))

        self.pid_path.write_text("not a pid")
        control_socket._retire_previous_bridge(self.pid_path)
        self.assertEqual(self.pid_path.read_text(), str(control_socket.os.getpid()))

    def test_pid_file_is_per_hyprland_instance(self):
        first = control_socket._bridge_pid_path(False, "abc_1_2")
        nested = control_socket._bridge_pid_path(False, "abc_3_4")
        test_instance = control_socket._bridge_pid_path(True, "abc_1_2")
        self.assertEqual(len({first, nested, test_instance}), 3)
        # A signature is only ever hex, digits and underscores; anything else
        # must not escape the runtime directory.
        hostile = control_socket._bridge_pid_path(False, "../../etc/x")
        self.assertEqual(hostile.parent, first.parent)


# Starts a real bridge the way Hyprland does: io.popen leaves the compositor's
# signal mask in place, and Hyprland blocks SIGTERM.
def _start_real_bridge(runtime_dir: str) -> subprocess.Popen:
    code = ("import sys; from whisper_key.control_socket import main; "
            "sys.exit(main(['--bridge', '--test']))")
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"), XDG_RUNTIME_DIR=runtime_dir,
                       HYPRLAND_INSTANCE_SIGNATURE="test_instance")
    return subprocess.Popen(
        [sys.executable, "-c", code, "/usr/bin/whisper-local-ctl", "--bridge"],
        stdin=subprocess.PIPE, env=environment,
        preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM}))


@unittest.skipUnless(sys.platform.startswith("linux"), "reads /proc")
class BridgeHandoverTests(unittest.TestCase):

    def test_new_bridge_retires_old_one_despite_inherited_sigterm_block(self):
        with tempfile.TemporaryDirectory() as runtime_dir:
            old_bridge = _start_real_bridge(runtime_dir)
            # Wait until the old bridge has registered itself.
            deadline = time.monotonic() + 5
            while not list(Path(runtime_dir).glob("*-bridge-*.pid")) and time.monotonic() < deadline:
                time.sleep(0.05)
            new_bridge = _start_real_bridge(runtime_dir)
            try:
                # stdin stays open, as when another process inherited the pipe.
                self.assertIsNotNone(old_bridge.wait(timeout=5))
                self.assertIsNone(new_bridge.poll())
            finally:
                for bridge in (old_bridge, new_bridge):
                    bridge.kill()
                    bridge.wait()
                    bridge.stdin.close()


if __name__ == "__main__":
    unittest.main()
