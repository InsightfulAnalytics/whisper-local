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
