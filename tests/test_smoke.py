import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


class HotkeyParsingTests(unittest.TestCase):
    def test_parse_hotkey_splits_on_plus(self):
        from whisper_key.utils import parse_hotkey
        self.assertEqual(parse_hotkey("ctrl+a"), ["ctrl", "a"])
        self.assertEqual(parse_hotkey("Ctrl+Shift+F1"), ["ctrl", "shift", "f1"])

    def test_parse_hotkey_handles_empty(self):
        from whisper_key.utils import parse_hotkey
        self.assertEqual(parse_hotkey(""), [])
        self.assertEqual(parse_hotkey(None), [])

    def test_beautify_hotkey_uppercases(self):
        from whisper_key.utils import beautify_hotkey
        self.assertEqual(beautify_hotkey("ctrl+a"), "CTRL+A")
        self.assertEqual(beautify_hotkey(""), "")


class VersionMetadataTests(unittest.TestCase):
    def test_pyproject_has_local_name(self):
        import tomllib
        with open(ROOT / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        self.assertEqual(data["project"]["name"], "whisper-local")
        self.assertIn("whisper-local", data["project"]["scripts"])
        self.assertIn("wl", data["project"]["scripts"])

    def test_no_orphan_update_checker(self):
        self.assertFalse((ROOT / "src" / "whisper_key" / "update_checker.py").exists())

    def test_main_does_not_import_update_checker(self):
        main_src = (ROOT / "src" / "whisper_key" / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("update_checker", main_src)
        self.assertNotIn("check_for_updates", main_src)


class VoiceCommandsDefaultsTests(unittest.TestCase):
    def test_no_registry_writes_in_defaults(self):
        defaults = (ROOT / "src" / "whisper_key" / "commands.defaults.yaml").read_text(encoding="utf-8")
        self.assertNotIn("reg add", defaults.lower())


class WhisperBackendTests(unittest.TestCase):
    def test_default_backend_is_faster_whisper(self):
        from ruamel.yaml import YAML
        path = ROOT / "src" / "whisper_key" / "config.defaults.yaml"
        with open(path, encoding="utf-8") as f:
            cfg = YAML().load(f)
        self.assertEqual(cfg["whisper"].get("backend"), "faster_whisper")

    def test_whisper_cpp_module_imports_lazily(self):
        # Import the module — the heavy pywhispercpp import is lazy inside __init__
        from whisper_key import whisper_engine_cpp
        self.assertTrue(hasattr(whisper_engine_cpp, 'WhisperEngineCpp'))

    def test_optional_dep_declared(self):
        import tomllib
        with open(ROOT / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        extras = data.get("project", {}).get("optional-dependencies", {})
        self.assertIn("whispercpp", extras)
        self.assertTrue(any("pywhispercpp" in d for d in extras["whispercpp"]))


class InstanceManagerTests(unittest.TestCase):
    def test_exposes_cleanup_pid_file(self):
        src = (ROOT / "src" / "whisper_key" / "instance_manager.py").read_text(encoding="utf-8")
        self.assertIn("def cleanup_pid_file", src)
        self.assertIn("os.kill", src)
        self.assertIn("_wait_for_lock", src)

    def test_main_calls_cleanup_pid_file(self):
        main_src = (ROOT / "src" / "whisper_key" / "main.py").read_text(encoding="utf-8")
        self.assertIn("cleanup_pid_file(instance_name)", main_src)


class TextPostprocessTests(unittest.TestCase):
    def test_strip_filler_words(self):
        from whisper_key.text_postprocess import postprocess
        cfg = {'strip_filler_words': True}
        self.assertEqual(postprocess("um, hello like world", cfg), "hello world")

    def test_capitalize_first(self):
        from whisper_key.text_postprocess import postprocess
        cfg = {'capitalize_first': True}
        self.assertEqual(postprocess("hello world", cfg), "Hello world")

    def test_ensure_punctuation(self):
        from whisper_key.text_postprocess import postprocess
        cfg = {'ensure_punctuation': True}
        self.assertEqual(postprocess("hello world", cfg), "hello world.")
        self.assertEqual(postprocess("hello world.", cfg), "hello world.")

    def test_postprocess_passthrough_when_empty(self):
        from whisper_key.text_postprocess import postprocess
        self.assertEqual(postprocess("hello", {}), "hello")
        self.assertEqual(postprocess("", {'capitalize_first': True}), "")

    def test_strip_trailing_period(self):
        from whisper_key.text_postprocess import postprocess
        cfg = {'strip_trailing_period': True}
        self.assertEqual(postprocess("hello world.", cfg), "hello world")
        self.assertEqual(postprocess("done.\n", cfg), "done\n")
        self.assertEqual(postprocess("e.g..", cfg), "e.g..")  # don't touch ellipsis-like
        self.assertEqual(postprocess("no period here", cfg), "no period here")

    def test_inline_formatting_basics(self):
        from whisper_key.text_postprocess import postprocess
        cfg = {'inline_formatting': True}
        self.assertEqual(postprocess("hello comma world period", cfg), "hello, world.")
        self.assertEqual(postprocess("what time is it question mark", cfg), "what time is it?")

    def test_ollama_polish_handles_curly_braces_in_text(self):
        from whisper_key.text_postprocess import _ollama_polish
        cfg = {'enabled': True, 'endpoint': 'http://127.0.0.1:0', 'timeout': 0.1,
               'prompt': 'Polish:\n\n{text}'}
        result = _ollama_polish("config = {a: 1, b: 2}", cfg)
        self.assertEqual(result, '')

    def test_ollama_polish_handles_curly_braces_in_prompt(self):
        from whisper_key.text_postprocess import _ollama_polish
        cfg = {'enabled': True, 'endpoint': 'http://127.0.0.1:0', 'timeout': 0.1,
               'prompt': 'Format: {format_var} not a placeholder. {text}'}
        result = _ollama_polish("hi", cfg)
        self.assertEqual(result, '')


class AppRulesShapeTests(unittest.TestCase):
    def test_defaults_yaml_is_valid(self):
        from ruamel.yaml import YAML
        path = ROOT / "src" / "whisper_key" / "app_rules.defaults.yaml"
        self.assertTrue(path.exists())
        with open(path, encoding="utf-8") as f:
            data = YAML().load(f)
        self.assertIn('rules', data)
        self.assertIsInstance(data['rules'], list)
        for rule in data['rules']:
            self.assertIn('match', rule)


class TransformsShapeTests(unittest.TestCase):
    def test_defaults_yaml_is_valid(self):
        from ruamel.yaml import YAML
        path = ROOT / "src" / "whisper_key" / "transforms.defaults.yaml"
        self.assertTrue(path.exists())
        with open(path, encoding="utf-8") as f:
            data = YAML().load(f)
        self.assertIn('transforms', data)
        for t in data['transforms']:
            self.assertIn('name', t)
            self.assertIn('prompt', t)

    def test_transforms_manager_loads(self):
        from whisper_key.transforms import TransformsManager
        tm = TransformsManager()
        names = [t.get('name') for t in tm.list_transforms()]
        self.assertIn('polish', names)
        self.assertIn('prompt-engineer', names)


class StreakComputationTests(unittest.TestCase):
    def test_streak_basic(self):
        import datetime
        from whisper_key.stats import _compute_streaks
        today = datetime.date(2026, 5, 18)
        active = {
            '2026-05-18', '2026-05-17', '2026-05-16',
            '2026-05-10', '2026-05-09',
        }
        current, longest = _compute_streaks(active, today)
        self.assertEqual(current, 3)
        self.assertEqual(longest, 3)

    def test_streak_breaks_yesterday(self):
        import datetime
        from whisper_key.stats import _compute_streaks
        today = datetime.date(2026, 5, 18)
        active = {'2026-05-10'}
        current, longest = _compute_streaks(active, today)
        self.assertEqual(current, 0)
        self.assertEqual(longest, 1)


class ProfilesShapeTests(unittest.TestCase):
    def test_defaults_yaml_is_valid(self):
        from ruamel.yaml import YAML
        path = ROOT / "src" / "whisper_key" / "profiles.defaults.yaml"
        self.assertTrue(path.exists())
        with open(path, encoding="utf-8") as f:
            data = YAML().load(f)
        self.assertIn('profiles', data)
        self.assertIn('dictation', data['profiles'])


class UtilsTests(unittest.TestCase):
    def test_resolve_asset_path_relative(self):
        from whisper_key.utils import resolve_asset_path
        result = resolve_asset_path("config.defaults.yaml")
        self.assertTrue(result.endswith("config.defaults.yaml"))

    def test_resolve_asset_path_absolute_passthrough(self):
        from whisper_key.utils import resolve_asset_path
        absolute = os.path.abspath(__file__)
        self.assertEqual(resolve_asset_path(absolute), absolute)


class NoiseSuppresionTests(unittest.TestCase):
    def test_passthrough_without_noisereduce(self):
        import sys
        import unittest.mock as mock
        import numpy as np
        sys.modules.pop('whisper_key.noise_suppression', None)
        import importlib
        with mock.patch.dict(sys.modules, {'noisereduce': None}):
            import whisper_key.noise_suppression as ns_mod
            importlib.reload(ns_mod)
            audio = np.zeros(16000, dtype=np.float32)
            result = ns_mod.apply_noise_reduction(audio, 16000, 0.75)
            np.testing.assert_array_equal(result, audio)

    def test_config_in_defaults(self):
        from ruamel.yaml import YAML
        path = ROOT / "src" / "whisper_key" / "config.defaults.yaml"
        with open(path, encoding="utf-8") as f:
            cfg = YAML().load(f)
        ns = cfg["audio"]["noise_suppression"]
        self.assertFalse(ns["enabled"])
        self.assertAlmostEqual(float(ns["strength"]), 0.75, places=2)


class UpdateCheckTests(unittest.TestCase):
    def test_is_newer_basic(self):
        from whisper_key.update_check import _is_newer
        self.assertTrue(_is_newer("1.0.0", "0.9.0"))
        self.assertFalse(_is_newer("0.9.0", "1.0.0"))
        self.assertFalse(_is_newer("0.9.0", "0.9.0"))

    def test_no_network_when_disabled(self):
        import unittest.mock as mock
        from whisper_key.update_check import maybe_check_for_update
        with mock.patch('whisper_key.update_check._check_in_background') as m:
            maybe_check_for_update(lambda _: None, {'enabled': False})
            m.assert_not_called()

    def test_update_check_in_config_defaults(self):
        from ruamel.yaml import YAML
        path = ROOT / "src" / "whisper_key" / "config.defaults.yaml"
        with open(path, encoding="utf-8") as f:
            cfg = YAML().load(f)
        self.assertIn("update_check", cfg)
        self.assertFalse(cfg["update_check"]["enabled"])


class TranscriptLogTests(unittest.TestCase):
    def test_record_and_load(self):
        import tempfile
        import unittest.mock as mock
        from whisper_key import transcript_log
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch('whisper_key.transcript_log.get_user_app_data_path', return_value=tmpdir):
                transcript_log.record_transcript("Hello world", app="test.exe", duration_s=1.5)
                entries = transcript_log.load_transcripts()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["text"], "Hello world")
        self.assertEqual(entries[0]["app"], "test.exe")

    def test_empty_text_not_logged(self):
        import tempfile
        import unittest.mock as mock
        from whisper_key import transcript_log
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch('whisper_key.transcript_log.get_user_app_data_path', return_value=tmpdir):
                transcript_log.record_transcript("", app="test.exe")
                entries = transcript_log.load_transcripts()
        self.assertEqual(len(entries), 0)


class SettingsUiModuleTests(unittest.TestCase):
    def test_module_importable(self):
        from whisper_key import settings_ui
        self.assertTrue(hasattr(settings_ui, 'run_settings_window'))


class HistoryWindowModuleTests(unittest.TestCase):
    def test_module_importable(self):
        from whisper_key import history_window
        self.assertTrue(hasattr(history_window, 'show_history'))


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_workflow_exists(self):
        self.assertTrue((ROOT / ".github" / "workflows" / "release.yml").exists())

    def test_release_workflow_triggers_on_tag(self):
        with open(ROOT / ".github" / "workflows" / "release.yml", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("tags:", content)
        self.assertIn("v*", content)
        self.assertIn("pypa/gh-action-pypi-publish", content)


class PyprojectOptionalDepsTests(unittest.TestCase):
    def test_noise_optional_dep(self):
        import tomllib
        with open(ROOT / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        extras = data.get("project", {}).get("optional-dependencies", {})
        self.assertIn("noise", extras)
        self.assertTrue(any("noisereduce" in d for d in extras["noise"]))


class SelftestModuleTests(unittest.TestCase):
    def test_module_importable(self):
        from whisper_key import selftest
        self.assertTrue(hasattr(selftest, 'run_selftest'))

    def test_report_helper(self):
        import io
        import sys
        from whisper_key.selftest import _report
        failures = []
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            _report(True, "looks good", failures, "fake")
            _report(False, ("uh oh", "fix-me"), failures, "fake-2")
        finally:
            sys.stdout = old_stdout
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0][0], "fake-2")


class FirstRunTests(unittest.TestCase):
    def test_flag_file_lifecycle(self):
        import tempfile
        import unittest.mock as mock
        from whisper_key import first_run

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch('whisper_key.first_run.get_user_app_data_path', return_value=tmpdir):
                self.assertTrue(first_run.is_first_run())
                first_run.mark_first_run_complete()
                self.assertFalse(first_run.is_first_run())

    def test_show_welcome_module_importable(self):
        from whisper_key import first_run
        self.assertTrue(hasattr(first_run, 'show_welcome_window'))


class CheatSheetTests(unittest.TestCase):
    def test_module_importable(self):
        from whisper_key import cheat_sheet
        self.assertTrue(hasattr(cheat_sheet, 'show_cheat_sheet'))


class BundleLogsTests(unittest.TestCase):
    def test_redaction_replaces_usernames(self):
        from whisper_key.bundle_logs import _redact
        sample = "Path: C:\\Users\\rohit\\AppData\\Roaming and email me at test@example.com"
        red = _redact(sample)
        self.assertNotIn("rohit", red.lower())
        self.assertNotIn("test@example.com", red)
        self.assertIn("<USER>", red)
        self.assertIn("<EMAIL>", red)

    def test_redaction_macos_linux_paths(self):
        from whisper_key.bundle_logs import _redact
        self.assertIn("<USER>", _redact("/Users/alice/.whisperkey/"))
        self.assertIn("<USER>", _redact("/home/bob/log.txt"))

    def test_bundle_creates_zip(self):
        import io
        import sys
        import tempfile
        import unittest.mock as mock
        import zipfile
        from whisper_key import bundle_logs

        with tempfile.TemporaryDirectory() as appdata:
            with tempfile.TemporaryDirectory() as out:
                output = f"{out}/bundle.zip"
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()
                try:
                    with mock.patch('whisper_key.bundle_logs.get_user_app_data_path', return_value=appdata), \
                         mock.patch('whisper_key.bundle_logs._capture_doctor', return_value='[doctor mocked]'):
                        rc = bundle_logs.bundle_logs(output)
                finally:
                    sys.stdout = old_stdout
                self.assertEqual(rc, 0)
                with zipfile.ZipFile(output) as zf:
                    names = zf.namelist()
                self.assertIn('about.txt', names)
                self.assertIn('doctor.txt', names)


class LocalServerTests(unittest.TestCase):
    def test_module_importable(self):
        from whisper_key import local_server
        self.assertTrue(hasattr(local_server, 'run_server'))
        self.assertEqual(local_server.DEFAULT_PORT, 7777)

    def test_decode_wav_fallback(self):
        import io
        import wave
        import numpy as np
        from whisper_key.local_server import _decode_wav_fallback

        with io.BytesIO() as buf:
            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                samples = (np.sin(2 * np.pi * 440 * np.arange(16000) / 16000) * 32767).astype(np.int16)
                wf.writeframes(samples.tobytes())
            wav_bytes = buf.getvalue()

        decoded = _decode_wav_fallback(wav_bytes)
        self.assertEqual(decoded.dtype, np.float32)
        self.assertEqual(len(decoded), 16000)
        self.assertGreater(float(np.max(np.abs(decoded))), 0.5)


class MainCliFlagsTests(unittest.TestCase):
    def test_main_registers_new_flags(self):
        main_src = (ROOT / "src" / "whisper_key" / "main.py").read_text(encoding="utf-8")
        for flag in ('--selftest', '--cheat-sheet', '--bundle-logs', '--serve'):
            self.assertIn(flag, main_src, f"main.py should register {flag}")


class TroubleshootingDocTests(unittest.TestCase):
    def test_docs_exist(self):
        self.assertTrue((ROOT / "docs" / "troubleshooting.md").exists())
        self.assertTrue((ROOT / "docs" / "faq.md").exists())


class VersionBumpTests(unittest.TestCase):
    def test_pyproject_version(self):
        import tomllib
        with open(ROOT / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        version = data["project"]["version"]
        major, minor = version.split('.')[:2]
        self.assertGreaterEqual((int(major), int(minor)), (0, 10))


if __name__ == "__main__":
    unittest.main()
