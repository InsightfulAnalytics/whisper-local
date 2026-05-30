import logging
import sys
import time

logger = logging.getLogger(__name__)


def run_selftest() -> int:
    print("\n🔬 Whisper Local — self-test\n" + "─" * 50)
    failures = []

    print("\n[1/4] Audio capture")
    ok, msg = _test_audio_capture()
    _report(ok, msg, failures, "audio-capture")

    print("\n[2/4] Whisper model loadable")
    ok, msg = _test_model_loadable()
    _report(ok, msg, failures, "model-load")

    print("\n[3/4] End-to-end transcription (2-second silence)")
    ok, msg = _test_end_to_end()
    _report(ok, msg, failures, "transcribe")

    print("\n[4/4] Clipboard read/write")
    ok, msg = _test_clipboard()
    _report(ok, msg, failures, "clipboard")

    print("\n" + "─" * 50)
    if not failures:
        print("✅ All checks passed. You're ready to dictate.\n")
        return 0

    print(f"❌ {len(failures)} check(s) failed:\n")
    for name, reason, fix in failures:
        print(f"  • {name}: {reason}")
        if fix:
            print(f"    → fix: {fix}")
    print()
    return 1


def _report(ok, msg, failures, name):
    if ok:
        print(f"    ✓ {msg}")
    else:
        reason, fix = msg
        print(f"    ✗ {reason}")
        failures.append((name, reason, fix))


def _test_audio_capture():
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError as e:
        return False, (f"Missing audio library: {e}", "pip install --upgrade whisper-local")

    try:
        sd.query_devices(kind='input')
    except Exception as e:
        return False, (f"No default input device: {e}",
                       "Check your mic is plugged in and selected in OS settings")

    try:
        recording = sd.rec(int(0.5 * 16000), samplerate=16000, channels=1, dtype='float32')
        sd.wait()
        rms = float(np.sqrt(np.mean(recording.astype(np.float32) ** 2)))
        if rms < 1e-6:
            return False, ("Mic captured pure silence — could be muted or permission denied",
                           "Windows: Settings → Privacy → Microphone, allow desktop apps. "
                           "macOS: System Settings → Privacy → Microphone, allow Terminal/your shell.")
        return True, f"Captured {len(recording)} samples (RMS={rms:.4f})"
    except Exception as e:
        return False, (f"Recording failed: {e}", "Check mic permissions and that no other app is holding the device")


def _test_model_loadable():
    try:
        from .config_manager import ConfigManager
        from .model_registry import ModelRegistry
        cm = ConfigManager(quiet=True)
        whisper_cfg = cm.get_whisper_config()
        model_key = whisper_cfg.get('model', 'tiny')

        backend = whisper_cfg.get('backend', 'faster_whisper')
        if backend == 'whisper_cpp':
            try:
                import pywhispercpp  # noqa: F401
            except ImportError:
                return False, ("whisper_cpp backend selected but pywhispercpp not installed",
                               "pip install 'whisper-local[whispercpp]'")

        registry = ModelRegistry(
            whisper_models_config=whisper_cfg.get('models', {}),
            streaming_models_config={}
        )
        model_info = registry.get_model(model_key)
        if not model_info:
            return False, (f"Configured model '{model_key}' not in registry", "")
        return True, f"Backend={backend}  model={model_key}  → {model_info.source}"
    except Exception as e:
        return False, (f"Model registry load failed: {e}", "Check user_settings.yaml")


def _test_end_to_end():
    try:
        import numpy as np
        from .config_manager import ConfigManager
        from .model_registry import ModelRegistry
        from .voice_activity_detection import VadManager

        cm = ConfigManager(quiet=True)
        whisper_cfg = cm.get_whisper_config()
        vad_cfg = cm.get_vad_config()

        registry = ModelRegistry(
            whisper_models_config=whisper_cfg.get('models', {}),
            streaming_models_config={}
        )
        vad_manager = VadManager(
            vad_precheck_enabled=False,
            vad_realtime_enabled=False,
            vad_onset_threshold=vad_cfg.get('vad_onset_threshold', 0.5),
            vad_offset_threshold=vad_cfg.get('vad_offset_threshold', 0.5),
            vad_min_speech_duration=vad_cfg.get('vad_min_speech_duration', 0.1),
            vad_silence_timeout_seconds=999.0,
        )

        from .whisper_engine import WhisperEngine
        backend = whisper_cfg.get('backend', 'faster_whisper')
        if backend == 'whisper_cpp':
            from .whisper_engine_cpp import WhisperEngineCpp
            engine = WhisperEngineCpp(
                model_key=whisper_cfg['model'], device=whisper_cfg['device'],
                compute_type=whisper_cfg['compute_type'], language='en',
                beam_size=1, initial_prompt='', hotwords=[], task='transcribe',
                vad_manager=vad_manager, model_registry=registry,
            )
        else:
            engine = WhisperEngine(
                model_key=whisper_cfg['model'], device=whisper_cfg['device'],
                compute_type=whisper_cfg['compute_type'], language='en',
                beam_size=1, initial_prompt='', hotwords=[], task='transcribe',
                vad_manager=vad_manager, model_registry=registry,
            )

        t0 = time.time()
        silence = np.zeros(2 * 16000, dtype=np.float32)
        _ = engine.transcribe_audio(silence)
        elapsed = time.time() - t0
        return True, f"Transcribed 2s of silence in {elapsed:.2f}s (model warmup included)"
    except Exception as e:
        return False, (f"Transcription failed: {e}",
                       "Run --doctor for more detail. Try `whisper-local --setup` if model never loaded.")


def _test_clipboard():
    try:
        import pyperclip
    except ImportError:
        return False, ("pyperclip not installed", "pip install --upgrade whisper-local")
    try:
        prev = pyperclip.paste()
        marker = f"__whisper-local-selftest-{int(time.time())}"
        pyperclip.copy(marker)
        time.sleep(0.05)
        got = pyperclip.paste()
        try: pyperclip.copy(prev)
        except Exception: pass
        if got != marker:
            return False, ("Clipboard write didn't round-trip",
                           "Another clipboard manager may be interfering")
        return True, "Clipboard round-trip OK"
    except Exception as e:
        return False, (f"Clipboard error: {e}",
                       "Check no clipboard manager is blocking access")


if __name__ == "__main__":
    sys.exit(run_selftest())
