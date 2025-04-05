# config.py
# Handles configuration, constants, default settings, and translation loading.

import os
import json

# --- Constants and Defaults ---
AUDIO_DIR_NAME = "音频" # Folder name for audio files
AUDIO_DIR = os.path.join(os.path.dirname(__file__), AUDIO_DIR_NAME)
DEFAULT_MAX_AUDIO_FILES = 20
DEFAULT_VOICE = "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)"
DEFAULT_APPEARANCE_MODE = "light"
DEFAULT_CUSTOM_COLOR = "#1F6AA5"
FLOAT_WINDOW_TIMEOUT = 2  # Seconds for blue dot auto-close
MOUSE_TIP_TIMEOUT = 1     # Seconds for red OK dot auto-close
SETTINGS_FILE = "voice_settings.json"
MOUSE_DRAG_THRESHOLD = 10 # Pixels to differentiate click from drag
TRANSLATIONS_FILE = "translations.json"

# --- Global Translation Data ---
TRANSLATIONS = {}
DEFAULT_WINDOW_TITLE = "Anki-TTS-Edge (Config Error)"
CUSTOM_WINDOW_TITLE = DEFAULT_WINDOW_TITLE

# --- Shared State Variables (Moved from main/monitor) ---
app_instance = None # Will be set by main.py after app creation
status_update_job = None # Managed by ui.py but potentially useful globally? Keep in ui for now.
clipboard_monitor_active = False # Master flag for monitoring
clipboard_polling_thread = None
previous_clipboard_poll_content = None
mouse_listener_thread = None
mouse_listener = None
is_dragging = False
drag_start_pos = (0, 0)
drag_start_time = 0
# --- End Shared State Variables ---


def load_translations(filename=TRANSLATIONS_FILE):
    """Loads translations from JSON into the global TRANSLATIONS dict."""
    global TRANSLATIONS, CUSTOM_WINDOW_TITLE
    default_translations = {
        "zh": {"window_title": "Anki-TTS-Edge (错误)", "status_ready": "准备就绪 (错误: 未加载翻译)"},
        "en": {"window_title": "Anki-TTS-Edge (Error)", "status_ready": "Ready (Error: Translations not loaded)"}
    }
    filepath = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f: TRANSLATIONS = json.load(f)
        print(f"Successfully loaded translations from: {filename}")
        CUSTOM_WINDOW_TITLE = TRANSLATIONS.get("zh", {}).get("window_title", TRANSLATIONS.get("en", {}).get("window_title", DEFAULT_WINDOW_TITLE))
    except FileNotFoundError:
        print(f"ERROR: Translations file not found: {filepath}"); TRANSLATIONS = default_translations; CUSTOM_WINDOW_TITLE = default_translations['en']['window_title']
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse {filename}: {e}"); TRANSLATIONS = default_translations; CUSTOM_WINDOW_TITLE = default_translations['en']['window_title']
    except Exception as e:
        print(f"ERROR: Unknown error loading translations: {e}"); TRANSLATIONS = default_translations; CUSTOM_WINDOW_TITLE = default_translations['en']['window_title']

# --- Initial Setup ---
load_translations()
os.makedirs(AUDIO_DIR, exist_ok=True)

print(f"Audio directory: {AUDIO_DIR}")
print(f"Settings file: {SETTINGS_FILE}")
print(f"Default window title set to: {CUSTOM_WINDOW_TITLE}")