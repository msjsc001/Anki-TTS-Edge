import os
import re
import asyncio
import threading
from datetime import datetime
import edge_tts
from config.constants import AUDIO_DIR
from utils.text import sanitize_text
from utils.i18n import i18n

async def generate_audio_edge_tts_async(text, voice, rate, volume, pitch, output_path):
    """
    Async function to generate audio using edge_tts.
    """
    try:
        comm = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        await comm.save(output_path)
        print(i18n.get("debug_edge_tts_ok", output_path))
        return output_path
    except Exception as e:
        msg = str(e)
        if "No audio was received" in msg:
             msg += " (Hint: Does this voice support the text language?)"
        print(i18n.get("debug_edge_tts_fail", msg))
        return None

def generate_audio(text, voice, rate_str, volume_str, pitch_str, on_complete=None):
    """
    Wrapper to run async audio generation in a separate thread.
    Calls on_complete(path, error) when done.
    """
    text = sanitize_text(text)
    if not text:
        print(i18n.get("debug_empty_text"))
        if on_complete:
            on_complete(None, "Text empty")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    match = re.search(r", (.*Neural)\)$", voice)
    part = re.sub(r'\W+', '', match.group(1)) if match else "Unknown"
    fname = f"Anki-TTS-Edge_{part}_{ts}.mp3"
    out_path = os.path.join(AUDIO_DIR, fname)
    
    print(i18n.get("debug_generating_audio", voice, rate_str, volume_str, pitch_str))
    print(i18n.get("debug_output_path", out_path))

    def run_async():
        result = None
        error = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                generate_audio_edge_tts_async(text, voice, rate_str, volume_str, pitch_str, out_path)
            )
            loop.close()
            
            if not result:
                error = i18n.get("debug_edge_tts_internal_error")
                
        except Exception as e:
            print(i18n.get("debug_generate_thread_error", e))
            error = str(e)
        finally:
            if on_complete:
                on_complete(result, error)

    threading.Thread(target=run_async, daemon=True).start()

async def generate_audio_task(text, voice, rate, volume, pitch):
    """
    Pure async wrapper for Flet usage.
    Returns (path, error).
    """
    text = sanitize_text(text)
    if not text:
        return None, i18n.get("debug_empty_text")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    match = re.search(r", (.*Neural)\)$", voice)
    part = re.sub(r'\W+', '', match.group(1)) if match else "Unknown"
    fname = f"Anki-TTS-Edge_{part}_{ts}.mp3"
    out_path = os.path.join(AUDIO_DIR, fname)
    
    print(i18n.get("debug_generating_audio", voice, rate, volume, pitch))
    print(i18n.get("debug_output_path", out_path))

    try:
        # direct await
        result = await generate_audio_edge_tts_async(text, voice, rate, volume, pitch, out_path)
        if result:
            return result, None
        else:
            return None, i18n.get("debug_edge_tts_internal_error")
    except Exception as e:
        return None, str(e)