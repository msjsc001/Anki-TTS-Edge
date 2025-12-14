import json
import os
import re
from config.constants import (
    SETTINGS_FILE, DEFAULT_MAX_AUDIO_FILES, DEFAULT_VOICE,
    DEFAULT_APPEARANCE_MODE, DEFAULT_CUSTOM_COLOR
)

class SettingsManager:
    def __init__(self):
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        defaults = {
            "language": "zh",
            "copy_path_enabled": True,
            "autoplay_enabled": True,
            "monitor_clipboard_enabled": False,
            "monitor_selection_enabled": False,
            "minimize_to_tray": False,
            "dual_blue_dot_enabled": False,
            "max_audio_files": DEFAULT_MAX_AUDIO_FILES,
            "selected_voice_latest": DEFAULT_VOICE,
            "selected_voice_previous": DEFAULT_VOICE,
            "rate": 0,
            "volume": 0,
            "appearance_mode": DEFAULT_APPEARANCE_MODE,
            "language_filter_left": "zh",
            "language_filter_right": "en",
            "custom_theme_color": DEFAULT_CUSTOM_COLOR
        }

        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                
                # Backward compatibility
                if "monitor_enabled" in loaded:
                    loaded["monitor_clipboard_enabled"] = loaded.pop("monitor_enabled")
                if "select_trigger_enabled" in loaded:
                    loaded["monitor_selection_enabled"] = loaded.pop("select_trigger_enabled")
                if "selected_voice" in loaded:
                    old_voice = loaded.pop("selected_voice")
                    if "selected_voice_latest" not in loaded:
                        loaded["selected_voice_latest"] = old_voice
                    if "selected_voice_previous" not in loaded:
                        loaded["selected_voice_previous"] = loaded.get("selected_voice_latest", old_voice)

                self.settings = defaults.copy()
                self.settings.update(loaded)

                # Validation
                loaded_color = self.settings.get("custom_theme_color", DEFAULT_CUSTOM_COLOR)
                if not re.match(r"^#[0-9a-fA-F]{6}$", loaded_color):
                    self.settings["custom_theme_color"] = DEFAULT_CUSTOM_COLOR
                
                if self.settings.get("language") not in ["zh", "en"]:
                    self.settings["language"] = "zh"

                if not self.settings.get("selected_voice_previous"):
                     self.settings["selected_voice_previous"] = self.settings.get("selected_voice_latest", DEFAULT_VOICE)

            except Exception as e:
                print(f"Load settings failed: {e}")
                self.settings = defaults
        else:
            self.settings = defaults
        
        return self.settings

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Settings save failed: {e}")

# Global instance
settings_manager = SettingsManager()