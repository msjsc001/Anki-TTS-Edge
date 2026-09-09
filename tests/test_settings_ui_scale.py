import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "Anki-TTS-Flet"
SETTINGS_MODULE_PATH = APP_ROOT / "config" / "settings.py"


def load_settings_module(settings_file):
    fake_config = types.ModuleType("config")
    fake_config.__path__ = [str(APP_ROOT / "config")]
    fake_constants = types.ModuleType("config.constants")
    fake_constants.SETTINGS_FILE = str(settings_file)
    fake_constants.DEFAULT_MAX_AUDIO_FILES = 20
    fake_constants.DEFAULT_VOICE = "test-voice"
    fake_constants.DEFAULT_APPEARANCE_MODE = "light"
    fake_constants.DEFAULT_CUSTOM_COLOR = "#1F6AA5"

    spec = importlib.util.spec_from_file_location("settings_under_test", SETTINGS_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(
        sys.modules,
        {"config": fake_config, "config.constants": fake_constants},
    ):
        spec.loader.exec_module(module)
    return module


class SettingsUiScaleTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.settings_file = Path(self.temporary_directory.name) / "voice_settings.json"
        self.module = load_settings_module(self.settings_file)

    def write_settings(self, value_marker=...):
        payload = {}
        if value_marker is not ...:
            payload["ui_scale_percent"] = value_marker
        self.settings_file.write_text(json.dumps(payload), encoding="utf-8")

    def test_missing_scale_uses_default_integer(self):
        self.write_settings()

        manager = self.module.SettingsManager()

        self.assertEqual(manager.get("ui_scale_percent"), 100)
        self.assertIsInstance(manager.get("ui_scale_percent"), int)

    def test_supported_legacy_representations_are_normalized_to_integer(self):
        for stored_value, expected in (("80", 80), (90.0, 90), (110, 110)):
            with self.subTest(stored_value=stored_value):
                self.write_settings(stored_value)

                manager = self.module.SettingsManager()

                self.assertEqual(manager.get("ui_scale_percent"), expected)
                self.assertIsInstance(manager.get("ui_scale_percent"), int)

    def test_invalid_scale_values_fall_back_to_default(self):
        for stored_value in (None, True, "", "95", 95, 80.5, [], {}):
            with self.subTest(stored_value=stored_value):
                self.write_settings(stored_value)

                manager = self.module.SettingsManager()

                self.assertEqual(manager.get("ui_scale_percent"), 100)

    def test_set_and_save_keep_persisted_scale_in_supported_range(self):
        manager = self.module.SettingsManager()
        manager.set("ui_scale_percent", "120")
        manager.save_settings()

        saved = json.loads(self.settings_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["ui_scale_percent"], 120)
        self.assertIsInstance(saved["ui_scale_percent"], int)

        manager.settings["ui_scale_percent"] = 125
        manager.save_settings()
        saved = json.loads(self.settings_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["ui_scale_percent"], 100)


if __name__ == "__main__":
    unittest.main()
