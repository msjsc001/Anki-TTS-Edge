import re
import asyncio
from edge_tts import VoicesManager
from utils.i18n import i18n
from core.voice_db import save_voice_cache

async def get_available_voices_async():
    """
    Fetches and organizes available voices from edge-tts.
    Returns a hierarchical dictionary of voices sorted by language and region.
    """
    try:
        voices = await VoicesManager.create()
        raw_list = voices.find()
        
        pattern = re.compile(r"^Microsoft Server Speech Text to Speech Voice \(([a-z]{2,3})-([A-Z]{2,}(?:-[A-Za-z]+)?), (.*Neural)\)$")
        h_voices = {}
        
        for v in raw_list:
            match = pattern.match(v['Name'])
            if match:
                lang, region, name_part = match.groups()
                h_voices.setdefault(lang, {}).setdefault(region, []).append(v['Name'])
        
        # Sort internal lists and dicts
        for lang in h_voices:
            for region in h_voices[lang]:
                h_voices[lang][region].sort()
            h_voices[lang] = dict(sorted(h_voices[lang].items()))
            
        # Sort languages with zh and en first
        sorted_h = {}
        if "zh" in h_voices: sorted_h["zh"] = h_voices.pop("zh")
        if "en" in h_voices: sorted_h["en"] = h_voices.pop("en")
        for lang in sorted(h_voices.keys()):
            sorted_h[lang] = h_voices[lang]
            
        total = sum(len(v) for lang_data in sorted_h.values() for v in lang_data.values())
        print(i18n.get("debug_voices_loaded", total))
        
        # Cache the successful result
        save_voice_cache(sorted_h)
        
        return sorted_h
        
    except Exception as e:
        print(i18n.get("debug_voices_load_failed", e))
        return {}

def get_display_voice_name(name, voice_map=None):
    """
    Helper to get a display friendly name for a voice.
    If voice_map is provided, it tries to find the reverse mapping.
    """
    if not name:
        return "Unknown"
        
    if voice_map:
        for dn, fn in voice_map.items():
            if fn == name:
                return dn
                
    match = re.search(r", (.*Neural)\)$", name)
    return match.group(1) if match else name