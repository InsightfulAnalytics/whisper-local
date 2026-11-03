# test_audio_recovery.py
# Drives AudioRecorder's capture loop against a fake sounddevice, so stream
# stalls, reconnects and device renumbering can be reproduced without hardware.
# Needs the app's own dependencies (sounddevice, soxr), so CI's lean smoke job skips it.

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from whisper_key import audio_recorder as recorder_module
except ImportError:  # sounddevice/soxr missing: nothing to test against
    recorder_module = None


# ---- Fake PortAudio ----

class FakeStream:
    """Calls back every few ms until stalled or closed, like a WASAPI stream."""

    def __init__(self, fake_sd, callback, blocksize=None, **_kwargs):
        if fake_sd.open_failures_left > 0:
            fake_sd.open_failures_left -= 1
            raise fake_sd.PortAudioError("Error opening InputStream: Device unavailable")
        self.callback = callback
        self.frames = blocksize or 768
        self.stalled = False
        self.closed = False
        self.callback_count = 0
        fake_sd.streams.append(self)

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while not self.closed:
            if not self.stalled:
                self.callback(np.full((self.frames, 1), 0.1, dtype=np.float32), self.frames, None, None)
                self.callback_count += 1
            time.sleep(0.005)

    def abort(self):
        self.closed = True

    def close(self):
        self.closed = True


class FakeSoundDevice:
    PortAudioError = RuntimeError

    def __init__(self, device_names):
        self.device_names = list(device_names)
        self.streams = []
        self.reloads = 0
        self.open_failures_left = 0
        self.names_after_reload = None

    def _device(self, index):
        return {'name': self.device_names[index], 'index': index, 'hostapi': 0,
                'max_input_channels': 2, 'default_samplerate': 48000.0}

    def query_devices(self, device=None, kind=None):
        if kind == 'input':
            return self._device(0)
        if device is None:
            return [self._device(i) for i in range(len(self.device_names))]
        return self._device(device)

    def query_hostapis(self, index=None):
        wasapi = {'name': 'Windows WASAPI', 'default_input_device': 0}
        return [wasapi] if index is None else wasapi

    def InputStream(self, **kwargs):
        return FakeStream(self, **kwargs)

    def sleep(self, ms):
        time.sleep(ms / 1000)

    def _terminate(self):
        pass

    # A reload is where PortAudio renumbers devices after a replug.
    def _initialize(self):
        self.reloads += 1
        if self.names_after_reload is not None:
            self.device_names = self.names_after_reload


# ---- Tests ----

@unittest.skipIf(recorder_module is None, "audio dependencies not installed")
class StreamRecoveryTests(unittest.TestCase):

    def setUp(self):
        self.fake_sd = FakeSoundDevice(["Microphone Array", "Desktop Microphone (AI-Micro)"])
        self.fingerprint = frozenset({"mic-array", "ai-micro"})
        fast_timings = {'STALL_SECONDS': 0.3, 'DEVICE_CHECK_SECONDS': 0.1,
                        'REOPEN_RETRY_SECONDS': 0.1, 'LOOP_SLEEP_MS': 20}
        patches = [mock.patch.object(recorder_module, 'sd', self.fake_sd),
                   mock.patch.object(recorder_module.AudioRecorder, '_read_endpoint_fingerprint',
                                     lambda _self: self.fingerprint)]
        patches += [mock.patch.object(recorder_module.AudioRecorder, name, value)
                    for name, value in fast_timings.items()]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.recorder = None

    def tearDown(self):
        if self.recorder:
            self.recorder.shutdown()

    def make_recorder(self, device=None):
        vad_manager = mock.Mock()
        vad_manager.is_available.return_value = False
        self.recorder = recorder_module.AudioRecorder(on_vad_event=lambda _event: None,
                                                      vad_manager=vad_manager, device=device)
        return self.recorder

    def wait_for(self, condition, timeout=3.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if condition():
                return True
            time.sleep(0.01)
        return False

    def wait_for_live_stream(self, count):
        return self.wait_for(lambda: len(self.fake_sd.streams) >= count
                             and self.fake_sd.streams[count - 1].callback_count > 5)

    def test_stalled_stream_is_reopened(self):
        self.make_recorder()
        self.assertTrue(self.wait_for_live_stream(1))

        self.fake_sd.streams[0].stalled = True

        self.assertTrue(self.wait_for_live_stream(2), "stream was not reopened after a stall")
        self.assertTrue(self.fake_sd.streams[0].closed)
        self.assertGreaterEqual(self.fake_sd.reloads, 1)

    def test_recording_survives_a_stall(self):
        recorder = self.make_recorder()
        self.assertTrue(self.wait_for_live_stream(1))
        recorder.start_recording()
        time.sleep(0.1)

        self.fake_sd.streams[0].stalled = True
        time.sleep(0.05)
        chunks_before_stall = len(recorder._buffer)
        self.assertTrue(self.wait_for_live_stream(2))

        self.assertTrue(recorder.get_recording_status())
        audio = recorder.stop_recording()
        self.assertIsNotNone(audio)
        # Kept what was recorded before the stall, plus audio from the new stream.
        samples_per_chunk = 768 // 3  # 48 kHz chunks resampled to 16 kHz
        self.assertGreater(len(audio), chunks_before_stall * samples_per_chunk)

    def test_idle_preroll_is_dropped_on_reopen(self):
        recorder = self.make_recorder()
        self.assertTrue(self.wait_for_live_stream(1))
        self.fake_sd.streams[0].stalled = True
        self.assertTrue(self.wait_for(lambda: self.fake_sd.reloads >= 1))
        self.assertTrue(self.wait_for_live_stream(2))

        # Every buffered chunk must have come from the new stream (+1: a callback
        # may have appended but not yet been counted).
        self.assertLessEqual(len(recorder._buffer), self.fake_sd.streams[1].callback_count + 1)

    def test_microphone_change_reopens_only_when_idle(self):
        recorder = self.make_recorder()
        self.assertTrue(self.wait_for_live_stream(1))
        recorder.start_recording()

        self.fingerprint = frozenset({"mic-array"})
        time.sleep(0.4)
        self.assertEqual(len(self.fake_sd.streams), 1, "reopened in the middle of a recording")

        recorder.stop_recording()
        self.assertTrue(self.wait_for_live_stream(2), "did not reopen after microphones changed")

    def test_chosen_device_is_found_again_after_renumbering(self):
        recorder = self.make_recorder(device=1)
        self.assertTrue(self.wait_for_live_stream(1))

        self.fake_sd.names_after_reload = ["Microphone Array", "Webcam", "Desktop Microphone (AI-Micro)"]
        self.fake_sd.streams[0].stalled = True

        self.assertTrue(self.wait_for_live_stream(2))
        self.assertEqual(recorder.device, 2)

    def test_chosen_device_missing_falls_back_to_host_default(self):
        recorder = self.make_recorder(device=1)
        self.assertTrue(self.wait_for_live_stream(1))

        self.fake_sd.names_after_reload = ["Microphone Array"]
        self.fake_sd.streams[0].stalled = True

        self.assertTrue(self.wait_for_live_stream(2))
        self.assertEqual(recorder.device, 0)

    def test_chosen_device_is_reclaimed_when_plugged_back_in(self):
        recorder = self.make_recorder(device=1)
        self.assertTrue(self.wait_for_live_stream(1))
        self.fake_sd.names_after_reload = ["Microphone Array"]
        self.fake_sd.streams[0].stalled = True
        self.assertTrue(self.wait_for_live_stream(2))

        self.fake_sd.names_after_reload = ["Microphone Array", "Desktop Microphone (AI-Micro)"]
        self.fingerprint = frozenset({"mic-array", "ai-micro", "replugged"})

        self.assertTrue(self.wait_for_live_stream(3))
        self.assertEqual(recorder.device, 1)

    def test_open_failures_keep_retrying(self):
        self.fake_sd.open_failures_left = 5
        self.make_recorder()

        self.assertTrue(self.wait_for_live_stream(1), "gave up after repeated open failures")
        self.assertGreaterEqual(self.fake_sd.reloads, 5)


if __name__ == "__main__":
    unittest.main()
