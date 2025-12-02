import os
import sys

def get_base_paths():
    """
    Determine the correct base paths for resources (read-only) and data (read-write).
    Handles both development environment and PyInstaller frozen environment.
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller: Temporary folder for resources, Executable folder for data
        resource_dir = sys._MEIPASS
        data_dir = os.path.dirname(sys.executable)
    else:
        # Development: Project root for both
        resource_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = resource_dir
        
    return resource_dir, data_dir

RESOURCE_DIR, DATA_DIR = get_base_paths()

# Base directory of the project (parent of config/)
# Keeping BASE_DIR for backward compatibility, pointing to DATA_DIR where appropriate
BASE_DIR = DATA_DIR

# Audio Directory (Read/Write -> Data Dir)
AUDIO_DIR = os.path.join(DATA_DIR, "音频")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Assets (Read-Only -> Resource Dir)
# 注意：在 PyInstaller 中，assets 文件夹需要被打包进去
ASSETS_DIR = os.path.join(RESOURCE_DIR, "assets")
ICON_PATH = os.path.join(ASSETS_DIR, "icon.ico")

# Translations (Read-Only -> Resource Dir)
TRANSLATIONS_FILE = os.path.join(ASSETS_DIR, "translations.json")

# Voice Cache (Read/Write -> Data Dir, or Resource if serving as default)
# We treat cache as something that might be updated or created, so let's check Data first, then Resource
# But for simplicity in this app, let's keep it in Data dir if we want to update it,
# OR in Resource dir if it's static.
# 假设 cache 是只读的或者我们不介意它丢失（如果是临时目录），或者我们希望它持久化。
# 为了稳妥，我们让 cache 文件也位于 Data Dir，如果不存在，可以从 Resource Dir 复制（可选逻辑），
# 或者简单地只使用 Data Dir。如果 Data Dir 没有，就会重新下载。
# 之前的逻辑似乎是直接读写 assets 下的文件，这在 EXE 中是不行的（assets在临时目录）。
# 我们将 cache 移到 Data Dir。
VOICE_CACHE_FILE = os.path.join(DATA_DIR, "voices_cache.json")

# Settings File (Read/Write -> Data Dir)
SETTINGS_FILE = os.path.join(DATA_DIR, "voice_settings.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

# Default Configuration Values
DEFAULT_MAX_AUDIO_FILES = 20
DEFAULT_VOICE = "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)"
DEFAULT_APPEARANCE_MODE = "light"
DEFAULT_CUSTOM_COLOR = "#1F6AA5"
CUSTOM_WINDOW_TITLE = "Anki-TTS-Edge (v1.8.0)"

# Timeouts & Thresholds
FLOAT_WINDOW_TIMEOUT = 2
MOUSE_TIP_TIMEOUT = 1
MOUSE_DRAG_THRESHOLD = 10 # Pixels