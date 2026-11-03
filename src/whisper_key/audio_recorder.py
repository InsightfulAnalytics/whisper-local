# audio_recorder.py
# Continuous-stream audio capture with a pre-roll ring buffer. Key design choices:
#
#   • A single sd.InputStream runs continuously from app startup. We do NOT
#     open/close streams per recording — that was the source of "first word
#     clipped" bugs and added 100-200ms of warmup latency on every press.
#
#   • The buffer is a deque trimmed to ~500ms when idle. When the user presses
#     record, the buffer already contains the recent past, so anything they
#     started saying before the OS finished routing the hotkey is captured.
#
#   • WASAPI on Windows runs at native rate (typically 48 kHz); we resample to
#     Whisper's 16 kHz only at stop time. This avoids resampling per chunk during
#     a recording, which would burn CPU.
#
#   • The stream is watched, not trusted. A WASAPI stream whose device vanished
#     (USB replug, a device reset, waking from Modern Standby) can stay "active"
#     without raising or calling back, so a stall is detected by the callbacks
#     stopping. Stalls, open errors and microphones being plugged in or removed
#     all reopen the stream on a freshly reloaded PortAudio device list, and the
#     loop keeps retrying for as long as no microphone is available.
#
#   • Silent-mic (peak amplitude near zero) surfaces a console warning on stop.

import collections
import logging
import threading
import time
from typing import Optional, Callable

import numpy as np
import sounddevice as sd
import soxr

from .voice_activity_detection import VadEvent, VAD_CHUNK_SIZE


class AudioRecorder:
    WHISPER_SAMPLE_RATE = 16000
    THREAD_JOIN_TIMEOUT = 2.0
    LOOP_SLEEP_MS = 100
    STREAM_DTYPE = np.float32
    PREROLL_SECONDS = 0.5
    TRAILING_SILENCE_TRIM_SECONDS = 0.4
    SILENCE_RMS_THRESHOLD = 0.005
    LONG_PAUSE_SECONDS = 2.0
    LONG_PAUSE_REPLACEMENT_SECONDS = 0.4
    # Stream health. Callbacks normally arrive every ~16 ms, so 2 s without one
    # is a dead stream, not a slow one.
    STALL_SECONDS = 2.0
    DEVICE_CHECK_SECONDS = 2.0
    REOPEN_RETRY_SECONDS = 2.0

    def __init__(self,
                 on_vad_event: Callable[[VadEvent], None],
                 channels: int = 1,
                 dtype: str = "float32",
                 max_duration: int = 30,
                 on_max_duration_reached: callable = None,
                 vad_manager=None,
                 streaming_manager=None,
                 on_streaming_result: Callable[[str, bool], None] = None,
                 device=None,
                 noise_suppression_config: Optional[dict] = None,
                 trim_long_pauses: bool = False,
                 debug_save_wav: bool = False):

        self.sample_rate = self.WHISPER_SAMPLE_RATE
        self.channels = channels
        self.dtype = dtype
        self.max_duration = max_duration
        self.on_max_duration_reached = on_max_duration_reached
        self.is_recording = False
        self.recording_start_time = None
        self.logger = logging.getLogger(__name__)
        self._noise_suppression_config = noise_suppression_config or {}
        # Interior-pause splicing is OFF by default: it cuts audio out of the middle
        # of a recording before Whisper ever sees it, which can destroy the words
        # either side of each cut. Opt in only after measuring.
        self.trim_long_pauses = trim_long_pauses
        self.debug_save_wav = debug_save_wav
        # PortAudio callback status is counted on the callback thread and reported
        # once at stop. Never log from the callback: a rotating-file write on the
        # realtime thread causes the very overflow it is reporting. Input overflow
        # means samples were dropped, which is the one that damages a transcript;
        # other flags are collected separately so they are not reported as data loss.
        self._overflow_count = 0
        self._other_status_flags = set()

        self.vad_manager = vad_manager
        self.on_vad_event = on_vad_event
        self.continuous_vad = self._setup_continuous_vad_monitoring()

        self.streaming_manager = streaming_manager
        self.on_streaming_result = on_streaming_result

        self.resolve_device(device)
        self._test_audio_source()

        self.continuous_streaming = self._setup_continuous_streaming()
        self._apply_device_rate()

        self._buffer = collections.deque()
        # Guards the ring buffer. The PortAudio callback appends/trims on its own
        # thread while stop/cancel/max-duration snapshot+clear from other threads;
        # list(deque) raises RuntimeError if the deque mutates mid-iteration, so
        # every buffer access is serialized through this lock. Held only for fast
        # ops (append, snapshot, clear), so it won't stall the audio callback.
        self._buffer_lock = threading.Lock()

        # Recovery state. The callback count is the stall detector's heartbeat;
        # the endpoint fingerprint is what "microphones changed" is compared to.
        self._callback_count = 0
        self._endpoint_fingerprint = self._read_endpoint_fingerprint()
        self._outage_reason = None
        self._outage_started = 0.0

        self._capture_running = False
        self._capture_thread = None
        self._current_level = 0.0
        self._start_capture()

    def _setup_continuous_vad_monitoring(self):
        if self.vad_manager.is_available():
            return self.vad_manager.create_continuous_detector(event_callback=self._handle_vad_event)
        return None

    def _setup_continuous_streaming(self):
        if self.streaming_manager and self.streaming_manager.is_available():
            # Its recording rate is set by _apply_device_rate, which also runs
            # whenever a reconnect lands on a device with a different rate.
            return self.streaming_manager.create_continuous_recognizer(
                result_callback=self._handle_streaming_result
            )
        return None

    def _handle_streaming_result(self, text: str, is_final: bool):
        if self.on_streaming_result:
            self.on_streaming_result(text, is_final)

    def resolve_device(self, device):
        # A chosen device is remembered by name as well as index: PortAudio
        # renumbers devices whenever the stream recovery reloads its list.
        self._preferred_device_name = None
        self._preferred_hostapi = None
        if device == "default" or device is None:
            self.device = None
            self._resolve_hostapi(None)
        elif isinstance(device, int):
            try:
                device_info = sd.query_devices(device)
                if device_info.get('max_input_channels', 0) > 0:
                    self.device = device
                    self._resolve_hostapi(device_info)
                    self._preferred_device_name = device_info['name']
                    self._preferred_hostapi = self.device_hostapi
                else:
                    self.logger.warning(f"Selected device {device} has no input channels; using default input instead")
                    self.device = None
                    self._resolve_hostapi(None)
            except Exception as e:
                self.logger.warning(f"Failed to load device {device}: {e}. Falling back to default input")
                self.device = None
                self._resolve_hostapi(None)
        else:
            self.logger.warning(f"Invalid device parameter: {device}, using default")
            self.device = None
            self._resolve_hostapi(None)

    def _resolve_hostapi(self, device_info):
        try:
            if device_info is None:
                device_info = sd.query_devices(kind='input')
            hostapi_index = device_info['hostapi']
            self.device_hostapi = sd.query_hostapis(hostapi_index)['name']
            self.device_native_rate = int(device_info['default_samplerate'])
        except Exception as e:
            self.logger.debug(f"Could not determine host API: {e}")
            self.device_hostapi = None
            self.device_native_rate = self.WHISPER_SAMPLE_RATE

    def _needs_resampling(self) -> bool:
        return self.device_hostapi and 'wasapi' in self.device_hostapi.lower()

    def _get_recording_sample_rate(self) -> int:
        if self._needs_resampling():
            return self.device_native_rate
        return self.WHISPER_SAMPLE_RATE

    # Derives every rate-dependent setting from the resolved device. Runs at
    # startup and again on each stream reopen, because a reconnect can land on
    # a device with a different native rate.
    def _apply_device_rate(self):
        self._recording_rate = self._get_recording_sample_rate()
        self._needs_resampling_cached = self._needs_resampling()
        if self._needs_resampling_cached:
            self._vad_blocksize = int(VAD_CHUNK_SIZE * self._recording_rate / self.WHISPER_SAMPLE_RATE)
        else:
            self._vad_blocksize = VAD_CHUNK_SIZE
        chunk_seconds = self._vad_blocksize / self._recording_rate
        self._preroll_max_chunks = max(1, int(self.PREROLL_SECONDS / chunk_seconds))
        if self.continuous_streaming:
            self.continuous_streaming.set_recording_rate(self._recording_rate)

    def _resample_audio(self, audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
        if orig_rate == target_rate or len(audio) == 0:
            return audio
        return soxr.resample(audio.flatten(), orig_rate, target_rate).astype(np.float32)

    def _handle_vad_event(self, event: VadEvent):
        self.on_vad_event(event)

    def _test_audio_source(self):
        try:
            if self.device is not None:
                device_info = sd.query_devices(self.device)
                self.logger.info(f"Using device: {device_info['name']}")
            else:
                default_input = sd.query_devices(kind='input')
                self.logger.info(f"Default source: {default_input['name']}")
        except sd.PortAudioError as e:
            # "Error querying device -1" = PortAudio has no default input at
            # all, i.e. no microphone is connected/enabled — tell the user what
            # to do instead of surfacing a cryptic device index.
            self.logger.error(f"Audio source test failed: {e}")
            raise RuntimeError(
                "No microphone found (the system has no default input device). "
                "Connect or enable a microphone — Windows: Settings > System > "
                "Sound > Input; macOS: System Settings > Sound > Input — then "
                "relaunch Whisper Local."
            ) from e
        except Exception as e:
            self.logger.error(f"Audio source test failed: {e}")
            raise

    # ---- Capture loop and stream recovery ----

    def _start_capture(self):
        self._capture_running = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True, name="audio-capture")
        self._capture_thread.start()

    # Runs for the life of the app: opens the stream, watches it, and reopens it
    # whenever it fails to open, stalls, or the set of microphones changes. It
    # never gives up; with no microphone available it keeps retrying quietly.
    def _capture_loop(self):
        while self._capture_running:
            try:
                stream = self._open_stream()
            except Exception as e:
                first_failure = self._outage_reason is None
                self._report_outage(f"could not open the microphone ({e})")
                # The first failure is retried at once: it is usually a stale
                # PortAudio device list, or one initialised on another thread
                # (WASAPI then refuses to start the stream), and a reload on this
                # thread fixes both. Repeat failures mean no microphone: back off.
                if not first_failure:
                    self._sleep_while_running(self.REOPEN_RETRY_SECONDS)
                if self._capture_running:
                    self._reload_devices()
                continue

            self._report_recovered()
            should_reopen = self._watch_stream()
            self._close_stream(stream)
            if not should_reopen:
                return
            self._reload_devices()

    def _open_stream(self):
        stream = sd.InputStream(samplerate=self._recording_rate,
                                channels=self.channels,
                                callback=self._audio_callback,
                                dtype=self.STREAM_DTYPE,
                                blocksize=self._vad_blocksize if self.continuous_vad else None,
                                device=self.device,
                                latency='low')
        try:
            stream.start()
        except Exception:
            stream.close()
            raise
        return stream

    # Blocks while the stream is healthy. Returns True when it should be
    # reopened, False when the app is shutting down.
    def _watch_stream(self) -> bool:
        heartbeat = self._callback_count
        silent_seconds = 0.0
        last_device_check = time.monotonic()
        longest_counted_tick = 2 * self.LOOP_SLEEP_MS / 1000
        while self._capture_running:
            tick_start = time.monotonic()
            sd.sleep(self.LOOP_SLEEP_MS)
            now = time.monotonic()
            if self.is_recording:
                self._check_max_duration_exceeded()

            # Stall: the callbacks have stopped. Only time this loop was itself
            # awake counts, so a laptop waking from sleep isn't read as a stall.
            if self._callback_count != heartbeat:
                heartbeat = self._callback_count
                silent_seconds = 0.0
            else:
                silent_seconds += min(now - tick_start, longest_counted_tick)
                if silent_seconds >= self.STALL_SECONDS:
                    self._report_outage(f"no audio from the microphone for {silent_seconds:.0f}s")
                    return True

            # Microphones plugged in or removed: reopen so the stream follows the
            # system default, or returns to the chosen device. Deferred while
            # recording, because the current stream is still delivering audio.
            if not self.is_recording and now - last_device_check >= self.DEVICE_CHECK_SECONDS:
                last_device_check = now
                if self._read_endpoint_fingerprint() != self._endpoint_fingerprint:
                    self.logger.info("Microphones connected or removed; reopening the audio stream")
                    return True
        return False

    # Abort, not stop: nothing in a stream being replaced is worth draining, and
    # each step is attempted even if the dead device makes the other one fail.
    def _close_stream(self, stream):
        for close_step in (stream.abort, stream.close):
            try:
                close_step()
            except Exception as e:
                self.logger.debug(f"Ignoring error while closing the audio stream: {e}")

    # Rebuilds PortAudio's device list (a snapshot taken at initialisation, so a
    # replugged microphone is invisible without this), then re-resolves the
    # device and every rate that depends on it. Only call with no stream open.
    def _reload_devices(self):
        previous_rate = self._recording_rate
        self._endpoint_fingerprint = self._read_endpoint_fingerprint()
        # Separate steps: if an earlier reload terminated PortAudio and then
        # failed to start it again, terminating now fails, and that must not stop
        # this attempt from starting it.
        try:
            sd._terminate()
        except Exception as e:
            self.logger.debug(f"PortAudio was not running before the reload: {e}")
        try:
            sd._initialize()
            self.device = self._find_preferred_device()
            self._resolve_hostapi(None if self.device is None else sd.query_devices(self.device))
        except Exception as e:
            self.logger.warning(f"Could not reload the audio device list: {e}")
            self.device = None
            self._resolve_hostapi(None)
        self._apply_device_rate()

        # Idle pre-roll is stale once the stream is replaced. A recording in
        # progress keeps its audio, unless the new device runs at another rate.
        with self._buffer_lock:
            if not self.is_recording or self._recording_rate != previous_rate:
                self._buffer.clear()

    # Finds the user's chosen device again by name, since a reload renumbers
    # devices. While it is unplugged, the same host API's default input stands
    # in (a WASAPI setup stays on WASAPI); None means the system default.
    def _find_preferred_device(self) -> Optional[int]:
        if self._preferred_device_name is None:
            return None
        for index, info in enumerate(sd.query_devices()):
            if (info['name'] == self._preferred_device_name
                    and info.get('max_input_channels', 0) > 0
                    and sd.query_hostapis(info['hostapi'])['name'] == self._preferred_hostapi):
                return index
        for hostapi in sd.query_hostapis():
            if hostapi['name'] == self._preferred_hostapi and hostapi.get('default_input_device', -1) >= 0:
                return hostapi['default_input_device']
        return None

    # Snapshot of the active microphones from the platform layer. None (macOS,
    # an unsupported OS, an unreadable registry) disables change detection.
    @staticmethod
    def _read_endpoint_fingerprint():
        try:
            from .platform import audio_endpoints
        except ImportError:
            return None
        return audio_endpoints.capture_fingerprint()

    def _sleep_while_running(self, seconds: float):
        deadline = time.monotonic() + seconds
        while self._capture_running and time.monotonic() < deadline:
            time.sleep(self.LOOP_SLEEP_MS / 1000)

    # An outage is announced once, not on every retry, and its end is announced
    # too, so the log shows how long dictation was unavailable.
    def _report_outage(self, reason: str):
        if self._outage_reason is None:
            self._outage_started = time.monotonic()
            self.logger.warning(f"Audio stream lost: {reason}; reconnecting")
            print(f"⚠ Microphone lost ({reason}); reconnecting...")
        self._outage_reason = reason

    def _report_recovered(self):
        if self._outage_reason is None:
            return
        try:
            info = sd.query_devices(self.device) if self.device is not None else sd.query_devices(kind='input')
            device_name = info['name']
        except Exception:
            device_name = "the default input"
        outage_seconds = time.monotonic() - self._outage_started
        self.logger.info(f"Audio stream recovered on {device_name} after {outage_seconds:.1f}s")
        print(f"✓ Microphone reconnected: {device_name}")
        self._outage_reason = None

    # ---- Audio callback and recording ----

    def _audio_callback(self, audio_data, frames, _time, status):
        # Heartbeat for the stall detector in _watch_stream.
        self._callback_count += 1
        chunk = audio_data.copy()
        recording = self.is_recording

        if recording:
            self._current_level = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
        else:
            self._current_level = 0.0

        with self._buffer_lock:
            self._buffer.append(chunk)
            # Trim to pre-roll size while idle. (VAD/streaming below operate on the
            # local `chunk` copy, not the buffer, so they stay outside the lock.)
            if not recording:
                while len(self._buffer) > self._preroll_max_chunks:
                    self._buffer.popleft()

        if recording:
            if self.continuous_vad and frames == self._vad_blocksize:
                if self._needs_resampling_cached:
                    chunk_16k = self._resample_audio(chunk, self._recording_rate, self.WHISPER_SAMPLE_RATE)
                    self.continuous_vad.process_chunk(chunk_16k.reshape(-1, 1))
                else:
                    self.continuous_vad.process_chunk(chunk)

            if self.continuous_streaming:
                self.continuous_streaming.process_chunk(chunk)

        if status:
            # Count, don't log. See _overflow_count in __init__ for why.
            if status.input_overflow:
                self._overflow_count += 1
            else:
                self._other_status_flags.add(str(status))

    def start_recording(self):
        if self.is_recording:
            return False

        self.logger.info("Starting audio recording...")
        self.recording_start_time = time.time()

        if self.continuous_vad:
            self.continuous_vad.reset()
        if self.continuous_streaming:
            self.continuous_streaming.reset()

        self._overflow_count = 0
        self._other_status_flags = set()
        preroll_chunks = len(self._buffer)
        self.is_recording = True
        self.logger.debug(f"Recording started with {preroll_chunks} preroll chunks (~{preroll_chunks * self._vad_blocksize / self._recording_rate:.2f}s)")
        return True

    def stop_recording(self) -> Optional[np.ndarray]:
        if not self.is_recording:
            return None
        with self._buffer_lock:
            snapshot = list(self._buffer)
            self.is_recording = False
            self._buffer.clear()
        return self._build_audio_array(snapshot)

    def _build_audio_array(self, chunks) -> Optional[np.ndarray]:
        if not chunks:
            print("   ✗ No audio data recorded!")
            return None

        audio_array = np.concatenate(chunks, axis=0)
        peak = float(np.max(np.abs(audio_array))) if len(audio_array) else 0.0
        if peak < 1e-5:
            self.logger.warning(f"Recorded audio is silent (peak={peak:.2e}) — mic may be muted or permission denied")
            print("   ⚠ Recording captured pure silence — mic muted, unplugged, or OS permission denied?")

        if self._needs_resampling_cached:
            self.logger.info(f"Resampling from {self._recording_rate} Hz to {self.WHISPER_SAMPLE_RATE} Hz")
            audio_array = self._resample_audio(audio_array, self._recording_rate, self.WHISPER_SAMPLE_RATE)

        if self._noise_suppression_config.get('enabled'):
            from .noise_suppression import apply_noise_reduction
            strength = float(self._noise_suppression_config.get('strength', 0.75))
            audio_array = apply_noise_reduction(audio_array, self.WHISPER_SAMPLE_RATE, strength)

        raw_duration = self.get_audio_duration(audio_array)
        self._dump_debug_wav('raw', audio_array)

        if self.trim_long_pauses:
            audio_array, splice_cuts = self._trim_long_pauses(audio_array)
        else:
            splice_cuts = 0
        after_splice = self.get_audio_duration(audio_array)

        audio_array = self._trim_trailing_silence(audio_array)
        duration = self.get_audio_duration(audio_array)
        self._dump_debug_wav('fed', audio_array)

        # Report what was actually removed, and by which stage. The old message
        # claimed both trims had run whether or not either cut anything, which made
        # it impossible to tell a harmless trailing trim from interior word loss.
        self.logger.info(
            f"Recorded {duration:.2f}s from {raw_duration:.2f}s captured (preroll incl.; "
            f"{raw_duration - after_splice:.2f}s spliced out of {splice_cuts} interior pause(s), "
            f"{after_splice - duration:.2f}s trailing silence trimmed)")
        if self._overflow_count:
            self.logger.warning(
                f"PortAudio reported {self._overflow_count} input overflow(s) during this recording; "
                f"samples were dropped and the audio has gaps")
        if self._other_status_flags:
            self.logger.info(
                f"PortAudio callback status during this recording: "
                f"{', '.join(sorted(self._other_status_flags))}")
        return audio_array

    # Writes the 16 kHz mono array to %APPDATA%/whisperkey/debug-audio/ so a bad
    # transcription can be traced back to what Whisper was actually fed. Dumped
    # twice per recording ('raw' before trimming, 'fed' after) so the trimmers can
    # be held to account. Off by default: there is no rotation and no size cap,
    # and these files are your speech.
    def _dump_debug_wav(self, tag: str, audio: np.ndarray) -> None:
        if not self.debug_save_wav or audio is None or not len(audio):
            return
        try:
            import datetime
            import os
            import wave

            from .utils import get_user_app_data_path

            out_dir = os.path.join(get_user_app_data_path(), "debug-audio")
            os.makedirs(out_dir, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            path = os.path.join(out_dir, f"{stamp}-{tag}.wav")
            pcm = (np.clip(audio.flatten(), -1.0, 1.0) * 32767).astype(np.int16)
            with wave.open(path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(self.WHISPER_SAMPLE_RATE)
                wav.writeframes(pcm.tobytes())
            self.logger.info(f"Debug audio written: {path}")
        except Exception as e:
            self.logger.warning(f"Could not write debug audio ({tag}): {e}")

    # Replaces interior silences longer than LONG_PAUSE_SECONDS with a short stub.
    # Returns the audio and the number of cuts made, because the cut COUNT is what
    # tells you whether this was harmless (one long pause at the end) or destructive
    # (several interior cuts through connected speech).
    def _trim_long_pauses(self, audio: np.ndarray):
        if audio.ndim > 1:
            mono = audio.mean(axis=1)
        else:
            mono = audio
        win = int(0.05 * self.WHISPER_SAMPLE_RATE)
        if win < 1:
            return audio, 0
        long_silence = int(self.LONG_PAUSE_SECONDS / 0.05)
        keep_windows = max(1, int(self.LONG_PAUSE_REPLACEMENT_SECONDS / 0.05))
        n = len(mono) // win
        if n < long_silence * 2:
            return audio, 0

        # Per-window RMS, vectorised. The silence gate sits a short way up from this
        # recording's own noise floor towards its speech level, because a fixed
        # absolute gate misjudges quiet input: a mic whose endpoint DSP holds the
        # signal tens of dB down has all of its speech below 0.005, and the whole
        # recording then reads as one long silence and gets spliced away.
        #
        # SILENCE_RMS_THRESHOLD is the CEILING, not the floor. The derived value can
        # only ever lower the gate, which means more audio counts as speech and
        # fewer cuts are made. For a trimmer that deletes audio, conservative is the
        # only safe direction to be wrong in.
        blocks = mono[:n * win].reshape(n, win)
        rms = np.sqrt(np.mean(blocks.astype(np.float32) ** 2, axis=1))
        floor = float(np.percentile(rms, 5))
        peak = float(np.percentile(rms, 95))
        derived = floor + 0.1 * max(peak - floor, 0.0)
        threshold = min(self.SILENCE_RMS_THRESHOLD, derived)
        voiced = rms > threshold

        pieces = []
        i = 0
        cuts = 0
        while i < n:
            if voiced[i]:
                j = i
                while j < n and voiced[j]:
                    j += 1
                pieces.append(audio[i * win:j * win])
                i = j
            else:
                j = i
                while j < n and not voiced[j]:
                    j += 1
                run_windows = j - i
                if run_windows > long_silence:
                    pieces.append(audio[i * win:(i + keep_windows) * win])
                    cuts += 1
                else:
                    pieces.append(audio[i * win:j * win])
                i = j

        if not cuts:
            return audio, 0
        if (len(mono) % win) > 0:
            pieces.append(audio[n * win:])
        return (np.concatenate(pieces, axis=0) if pieces else audio), cuts

    def _trim_trailing_silence(self, audio: np.ndarray) -> np.ndarray:
        if audio.ndim > 1:
            mono = audio.mean(axis=1)
        else:
            mono = audio
        window = int(0.02 * self.WHISPER_SAMPLE_RATE)
        if window < 1 or len(mono) < window * 4:
            return audio
        trim_samples = int(self.TRAILING_SILENCE_TRIM_SECONDS * self.WHISPER_SAMPLE_RATE)
        last_voice = len(mono)
        i = len(mono) - window
        while i > 0:
            block = mono[i:i + window]
            rms = float(np.sqrt(np.mean(block ** 2)))
            if rms > self.SILENCE_RMS_THRESHOLD:
                last_voice = i + window
                break
            i -= window
        keep_until = min(len(mono), last_voice + trim_samples)
        if keep_until >= len(mono) - window:
            return audio
        return audio[:keep_until]

    def get_current_level(self) -> float:
        return self._current_level

    def cancel_recording(self):
        if not self.is_recording:
            return
        with self._buffer_lock:
            self.is_recording = False
            self._buffer.clear()
        self.recording_start_time = None

    def shutdown(self):
        self._capture_running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=self.THREAD_JOIN_TIMEOUT)

    def _check_max_duration_exceeded(self) -> bool:
        if self.max_duration <= 0 or not self.recording_start_time:
            return False
        if time.time() - self.recording_start_time < self.max_duration:
            return False

        self.logger.info(f"Maximum recording duration of {self.max_duration}s reached")
        print(f"⏰ Maximum recording duration of {self.max_duration}s reached - stopping recording")

        with self._buffer_lock:
            snapshot = list(self._buffer)
            self.is_recording = False
            self._buffer.clear()
        audio_data = self._build_audio_array(snapshot)
        if self.on_max_duration_reached:
            self.on_max_duration_reached(audio_data)
        return True

    def get_recording_status(self) -> bool:
        return self.is_recording

    def get_audio_duration(self, audio_data: np.ndarray) -> float:
        if audio_data is None or len(audio_data) == 0:
            return 0.0
        return len(audio_data) / self.sample_rate

    def get_device_id(self) -> Optional[int]:
        if self.device is not None:
            return self.device
        return sd.query_devices(kind='input')['index']

    @staticmethod
    def get_available_audio_devices(host_filter: Optional[str] = None):
        try:
            all_devices = sd.query_devices()
            hostapis = sd.query_hostapis()
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to enumerate audio devices: {e}")
            return []

        devices = []
        host_filter_lower = host_filter.lower() if host_filter else None

        for idx, device in enumerate(all_devices):
            if device.get('max_input_channels', 0) <= 0:
                continue

            hostapi_index = device['hostapi']
            hostapi_info = hostapis[hostapi_index]
            hostapi_name = hostapi_info['name']

            if host_filter_lower and hostapi_name.lower() != host_filter_lower:
                continue

            devices.append({
                'id': idx,
                'name': device['name'],
                'input_channels': device['max_input_channels'],
                'sample_rate': device['default_samplerate'],
                'hostapi': hostapi_name
            })

        return devices
