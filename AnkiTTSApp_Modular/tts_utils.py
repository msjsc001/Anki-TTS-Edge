# tts_utils.py
# Functions for interacting with the Edge TTS service.

import asyncio
import threading
import re
from datetime import datetime # Needed for generate_audio filename
import os # Needed for generate_audio path join

from edge_tts import VoicesManager, Communicate

# Import necessary variables/objects from other modules
import config # Need AUDIO_DIR etc.
# Removed import main

# --- Voice List Retrieval ---
async def get_available_voices_async(app_instance=None): # Accept app_instance
    """Asynchronously fetches and categorizes available Edge TTS voices."""
    try:
        voices_mgr = await VoicesManager.create()
        raw_list = voices_mgr.find()
        pattern = re.compile(r"^Microsoft Server Speech Text to Speech Voice \(([a-z]{2,3})-([A-Z]{2,}(?:-[A-Za-z]+)?), (.*Neural)\)$")
        h_voices = {}
        for v in raw_list:
            match = pattern.match(v['Name'])
            if match: lang, region, name_part = match.groups(); h_voices.setdefault(lang, {}).setdefault(region, []).append(v['Name'])
        for lang in h_voices:
            for region in h_voices[lang]: h_voices[lang][region].sort()
            h_voices[lang] = dict(sorted(h_voices[lang].items()))
        sorted_h = {}
        if "zh" in h_voices: sorted_h["zh"] = h_voices.pop("zh")
        if "en" in h_voices: sorted_h["en"] = h_voices.pop("en")
        for lang in sorted(h_voices.keys()): sorted_h[lang] = h_voices[lang]
        total = sum(len(v_list) for lang_data in sorted_h.values() for v_list in lang_data.values())

        if app_instance: print(app_instance._("debug_voices_loaded", total))
        else: print(f"Found {total} voices...")
        return sorted_h
    except Exception as e:
        if app_instance: print(app_instance._("debug_voices_load_failed", e))
        else: print(f"Failed to get voice list: {e}")
        return {}

def refresh_voices_list(app_instance=None):
    """Starts a background thread to asynchronously refresh the voice list."""
    if not app_instance: print("Error: refresh_voices_list requires an app_instance."); return

    def run_async():
        data = {}
        try:
            loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            data=loop.run_until_complete(get_available_voices_async(app_instance=app_instance)); loop.close()
        except Exception as e:
             print(app_instance._("debug_run_async_voices_error", e)); data = {}
        finally:
            if app_instance and app_instance.root.winfo_exists():
                app_instance.root.after(0, app_instance.update_voice_ui, data)
            else: print("Error: Could not schedule voice UI update (app context lost).")
    threading.Thread(target=run_async, daemon=True).start()


# --- Audio Generation ---
async def generate_audio_edge_tts_async(text, voice, rate, volume, pitch, output_path, app_instance=None):
    """Core function to generate audio using edge-tts library."""
    try:
        comm = Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        await comm.save(output_path)
        if app_instance: print(app_instance._("debug_edge_tts_ok", output_path))
        else: print(f"Edge TTS audio generated successfully: {output_path}")
        return output_path
    except Exception as e:
        if app_instance: print(app_instance._("debug_edge_tts_fail", e))
        else: print(f"Edge TTS audio generation failed: {e}")
        return None

def generate_audio(text, voice, rate_str, volume_str, pitch_str, on_complete=None, app_instance=None):
    """
    Handles audio generation setup, filename creation, and starts the async generation
    in a background thread. Calls on_complete in the main thread afterwards.
    Requires app_instance for translations and status updates.
    """
    # <<<<<<< 修改: 从 monitor 导入 sanitize_text >>>>>>>>>
    from monitor import sanitize_text # Import locally from monitor module

    text = sanitize_text(text)
    if not text:
        if app_instance: print(app_instance._("debug_empty_text")); app_instance.update_status("status_empty_text_error", error=True)
        else: print("Text is empty...")
        if on_complete:
            callback = lambda: on_complete(None, "Text empty")
            if app_instance and app_instance.root.winfo_exists(): app_instance.root.after(0, callback)
            else: callback()
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    match = re.search(r", (.*Neural)\)$", voice)
    safe_part = re.sub(r'\W+', '', match.group(1)) if match else "UnknownVoice"
    filename = f"Anki-TTS-Edge_{safe_part}_{timestamp}.mp3"
    output_path = os.path.join(config.AUDIO_DIR, filename)

    if app_instance:
        print(app_instance._("debug_generating_audio", voice, rate_str, volume_str, pitch_str))
        print(app_instance._("debug_output_path", output_path))
    else: print(f"Generating audio... Output: {output_path}")

    def run_async_in_thread():
        result = None; error = None
        try:
            loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            result=loop.run_until_complete(generate_audio_edge_tts_async(text, voice, rate_str, volume_str, pitch_str, output_path, app_instance=app_instance)); loop.close() # Pass app_instance down
            if not result:
                 error_key = "debug_edge_tts_internal_error"
                 error = app_instance._(error_key) if app_instance else config.TRANSLATIONS['en'].get(error_key, "Edge TTS internal error")
        except Exception as e:
            error_key = "debug_generate_thread_error"
            if app_instance: print(app_instance._(error_key, e))
            else: print(f"Error in generation thread: {e}")
            error = str(e)
        finally:
            if on_complete:
                callback = lambda p=result, e=error: on_complete(p, e)
                if app_instance and app_instance.root.winfo_exists(): app_instance.root.after(0, callback)
                else:
                    print("Warning: App context lost, running on_complete directly.");
                    try: callback()
                    except Exception as cb_e: print(f"Error running on_complete directly: {cb_e}")

    threading.Thread(target=run_async_in_thread, daemon=True).start()