import inspect
import sys

sys.path.insert(0, "Anki-TTS-Flet")

import flet as ft

from ui.history_view import HistoryView
from ui.home_view import HomeView
from ui.settings_view import SettingsView


class DummyPage:
    theme_mode = ft.ThemeMode.LIGHT
    overlay = []

    def update(self):
        return None


def main():
    page = DummyPage()
    home = HomeView(page)
    history = HistoryView(page)
    settings = SettingsView(page)

    home.set_dual_mode(False)
    home.refresh_texts()
    home.populate_voices(
        [
            {
                "name": "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)",
                "lang": "zh",
                "region": "CN",
                "display_name": "XiaoxiaoNeural",
            },
            {
                "name": "Microsoft Server Speech Text to Speech Voice (en-US, AndrewNeural)",
                "lang": "en",
                "region": "US",
                "display_name": "AndrewNeural",
            },
        ]
    )
    history.populate_history([])
    history.refresh_texts()
    settings.set_values(
        {
            "max_audio_files": 20,
            "autoplay_enabled": True,
            "monitor_selection_enabled": False,
            "dual_blue_dot_enabled": False,
            "monitor_clipboard_enabled": False,
            "copy_path_enabled": True,
            "minimize_to_tray": False,
            "appearance_mode": "light",
            "window_width": 750,
            "window_height": 850,
        }
    )
    settings.update_window_size_display(750, 850)
    settings.refresh_texts()

    print("flet_selfcheck_ok")
    print(f"dropdown_signature={inspect.signature(ft.Dropdown)}")


if __name__ == "__main__":
    main()
