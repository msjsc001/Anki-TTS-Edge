import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "Anki-TTS-Flet"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import flet as ft

from config.ui_scale import SUPPORTED_UI_SCALE_PERCENTS, UiScale
from ui.history_view import HistoryView
from ui.home_view import HomeView
from ui.settings_view import SettingsView


def dummy_page():
    return SimpleNamespace(theme_mode=ft.ThemeMode.LIGHT)


class UiScaleTests(unittest.TestCase):
    def test_supported_presets_scale_dimensions_and_fonts(self):
        for percent in SUPPORTED_UI_SCALE_PERCENTS:
            with self.subTest(percent=percent):
                scale = UiScale(percent)
                self.assertEqual(scale.px(20), 20 * percent / 100)
                self.assertEqual(scale.font(14), 14 * percent / 100)

    def test_invalid_values_use_100_percent(self):
        for value in (None, True, 80.5, 95, "invalid"):
            with self.subTest(value=value):
                self.assertEqual(UiScale(value).percent, 100)

    def test_views_use_the_same_scale_for_static_dimensions(self):
        compact = UiScale(80)
        home = HomeView(dummy_page(), compact)
        history = HistoryView(dummy_page(), compact)
        settings = SettingsView(dummy_page(), compact)

        self.assertEqual(home.padding, compact.px(20))
        self.assertEqual(home.text_input_wrapper.height, compact.px(140))
        self.assertEqual(home.text_input.text_size, compact.font(14))
        self.assertEqual(home.highlighted_text_overlay.padding, compact.px(12))
        self.assertEqual(home.btn_gen_b.height, compact.px(50))
        self.assertEqual(history.padding, compact.px(20))
        self.assertEqual(history.header_text.size, compact.font(24))
        self.assertEqual(settings.padding, compact.px(20))
        self.assertEqual(settings.header.size, compact.font(24))
        self.assertEqual(settings.ui_scale_dropdown.width, compact.px(120))

    def test_dynamic_voice_history_and_highlight_controls_are_scaled(self):
        scale = UiScale(120)
        home = HomeView(dummy_page(), scale)
        home.populate_voices(
            [
                {"name": "zh-test", "display_name": "中文", "lang": "zh-CN", "region": "CN"},
                {"name": "en-test", "display_name": "English", "lang": "en-US", "region": "US"},
            ]
        )

        left_region_chip = home.region_nav_left.controls[0]
        left_voice_tile = home.list_left.controls[1]
        self.assertEqual(left_region_chip.content.size, scale.font(11))
        self.assertEqual(left_voice_tile.title.size, scale.font(14))

        home.show_highlighted_text(
            "你好 hello",
            [
                {"text": "你好", "start_char": 0, "end_char": 2},
                {"text": "hello", "start_char": 3, "end_char": 8},
            ],
        )
        highlight_row = home.highlighted_text_column.controls[0]
        highlighted_words = [
            control.content
            for control in highlight_row.controls
            if isinstance(control, ft.Container)
        ]
        self.assertTrue(highlighted_words)
        self.assertTrue(all(text.size == scale.font(14) for text in highlighted_words))
        self.assertEqual(
            home.highlighted_text_column.height,
            scale.px(140) - scale.px(24),
        )

        history = HistoryView(dummy_page(), scale)
        history.populate_history(
            [{"text": "example", "voice": "en-test", "timestamp": 1, "path": "unused.mp3"}]
        )
        history_card = history.history_list.controls[0]
        text_column = history_card.content.controls[1]
        self.assertEqual(history_card.padding, scale.px(10))
        self.assertEqual(text_column.controls[0].size, scale.font(14))
        self.assertEqual(text_column.controls[1].size, scale.font(12))

    def test_short_window_layout_keeps_voice_area_in_scrollable_content(self):
        scale = UiScale(80)
        home = HomeView(dummy_page(), scale)

        home.set_compact_height_layout(True)
        self.assertEqual(home.content.scroll, ft.ScrollMode.AUTO)
        self.assertFalse(home.voice_area.expand)
        self.assertEqual(home.voice_area.height, scale.px(190))

        home.set_compact_height_layout(False)
        self.assertIsNone(home.content.scroll)
        self.assertTrue(home.voice_area.expand)
        self.assertIn(home.voice_area.height, (None, ""))


if __name__ == "__main__":
    unittest.main()
