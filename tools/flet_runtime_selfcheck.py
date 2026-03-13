import inspect
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(ROOT, "Anki-TTS-Flet")

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import flet as ft

from ui.history_view import HistoryView
from ui.home_view import HomeView
from ui.settings_view import SettingsView


class DummyPage:
    theme_mode = ft.ThemeMode.LIGHT
    overlay = []
    dialog = None

    def update(self):
        return None


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    page = DummyPage()
    home = HomeView(page)
    history = HistoryView(page)
    settings = SettingsView(page)

    voices = [
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

    home.set_dual_mode(True)
    home.populate_voices(voices)
    home.set_selections(voices[0]["name"], voices[1]["name"])
    home.refresh_texts()
    assert_true(home.selected_voice_left == voices[0]["name"], "home left slot mismatch")
    assert_true(home.selected_voice_right == voices[1]["name"], "home right slot mismatch")
    assert_true(home.btn_gen_a.visible is True, "dual mode should show A button")

    callback_state = {"play": 0, "delete": 0, "clear": 0}
    history.on_play_audio = lambda record: callback_state.__setitem__("play", callback_state["play"] + 1)
    history.on_delete_item = lambda record: callback_state.__setitem__("delete", callback_state["delete"] + 1)
    history.on_clear_all = lambda: callback_state.__setitem__("clear", callback_state["clear"] + 1)
    history.populate_history(
        [{"text": "demo", "voice": voices[1]["name"], "path": "demo.mp3", "timestamp": 0}]
    )
    history._play_audio({"path": "demo.mp3"})
    history._delete_item({"path": "demo.mp3"})
    history._confirm_clear(None)
    history.refresh_texts()
    assert_true(callback_state["play"] == 1, "history play callback missing")
    assert_true(callback_state["delete"] == 1, "history delete callback missing")
    assert_true(callback_state["clear"] == 1, "history clear callback missing")

    settings.set_values(
        {
            "max_audio_files": 20,
            "autoplay_enabled": True,
            "monitor_selection_enabled": True,
            "selection_dual_mode_enabled": True,
            "dual_voice_mode_enabled": True,
            "monitor_clipboard_enabled": True,
            "copy_path_enabled": True,
            "minimize_to_tray": False,
            "appearance_mode": "light",
            "window_width": 750,
            "window_height": 850,
        }
    )
    settings.update_window_size_display(750, 850)
    settings.refresh_texts()
    assert_true(settings.selection_switch.value is True, "selection switch mismatch")
    assert_true(settings.selection_dual_mode_switch.value is True, "selection dual switch mismatch")
    assert_true(settings.dual_voice_mode_switch.value is True, "dual voice switch mismatch")
    assert_true(settings.ctrl_c_switch.value is True, "clipboard switch mismatch")

    print("flet_runtime_selfcheck_ok")
    print(f"dropdown_signature={inspect.signature(ft.Dropdown)}")
    print(f"iconbutton_signature={inspect.signature(ft.IconButton)}")


if __name__ == "__main__":
    main()
