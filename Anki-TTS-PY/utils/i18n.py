import json
import os
from config.constants import TRANSLATIONS_FILE, CUSTOM_WINDOW_TITLE

class I18nManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(I18nManager, cls).__new__(cls)
            cls._instance.translations = {}
            cls._instance.current_language = 'zh' # Default
            cls._instance.window_title = CUSTOM_WINDOW_TITLE
            cls._instance.load_translations()
        return cls._instance

    def load_translations(self):
        """Loads translations from the JSON file."""
        default_translations = {
            "zh": {"window_title": "Anki-TTS-Edge (错误)", "status_ready": "准备就绪 (错误: 未加载翻译)"},
            "en": {"window_title": "Anki-TTS-Edge (Error)", "status_ready": "Ready (Error: Translations not loaded)"}
        }
        
        try:
            with open(TRANSLATIONS_FILE, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            print(f"成功加载翻译文件: {TRANSLATIONS_FILE}")
            # Update default title from loaded JSON
            self.window_title = self.translations.get("zh", {}).get("window_title", CUSTOM_WINDOW_TITLE)
        except FileNotFoundError:
            print(f"错误: 翻译文件未找到: {TRANSLATIONS_FILE}")
            print("将使用内置的默认文本 (可能不完整)。")
            self.translations = default_translations
        except json.JSONDecodeError as e:
            print(f"错误: 解析翻译文件失败 ({TRANSLATIONS_FILE}): {e}")
            self.translations = default_translations
        except Exception as e:
            print(f"加载翻译时发生未知错误: {e}")
            self.translations = default_translations

    def set_language(self, lang):
        if lang in ['zh', 'en']:
            self.current_language = lang
        else:
            print(f"Warning: Unsupported language '{lang}', falling back to 'zh'")
            self.current_language = 'zh'

    def get(self, key, *args, **kwargs):
        """Get translation for key with optional formatting arguments."""
        lang_map = self.translations.get(self.current_language, self.translations.get('zh', {}))
        text = lang_map.get(key, key) # Return key if not found
        try:
            return text.format(*args, **kwargs) if args or kwargs else text
        except (IndexError, KeyError, TypeError):
            return text

# Global instance for easy access
i18n = I18nManager()