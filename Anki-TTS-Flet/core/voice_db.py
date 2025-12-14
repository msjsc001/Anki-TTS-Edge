import json
import os
from config.constants import VOICE_CACHE_FILE

def load_voice_cache():
    """
    Loads voice data from the local cache file.
    Returns:
        dict: The cached voice data, or an empty dict if load fails.
    """
    if not os.path.exists(VOICE_CACHE_FILE):
        return {}
    
    try:
        with open(VOICE_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load voice cache: {e}")
        return {}

def save_voice_cache(data):
    """
    Saves voice data to the local cache file.
    Args:
        data (dict): The voice data to save.
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(VOICE_CACHE_FILE), exist_ok=True)
        
        with open(VOICE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Failed to save voice cache: {e}")