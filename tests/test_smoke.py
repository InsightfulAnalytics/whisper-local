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


if __name__ == "__main__":
    unittest.main()
