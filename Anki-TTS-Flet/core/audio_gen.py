import os
import re
import asyncio
import threading
import json
from datetime import datetime
import edge_tts
from config.constants import AUDIO_DIR
from utils.text import sanitize_text
from utils.i18n import i18n

from core.alignment import AlignmentEngine

async def generate_audio_with_timestamps_async(text, voice, rate, volume, pitch, output_path):
    """
    Async function to generate audio using edge_tts and capture word boundaries.
    Returns (output_path, timestamps_data) or (None, None) on error.
    """
    try:
        comm = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        
        word_boundaries = []
        audio_chunks = []
        
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset and duration are in 100-nanosecond units
                # We store them raw or simplified? AlignmentEngine handles raw logic?
                # Let's keep consistency with original dict but no manual char mapping
                word_boundaries.append({
                    "text": chunk["text"],
                    "offset": chunk["offset"],
                    "duration": chunk["duration"]
                })
        
        # Write audio file
        with open(output_path, "wb") as f:
            for chunk in audio_chunks:
                f.write(chunk)
        
        # Use AlignmentEngine to generate precise mappings
        engine = AlignmentEngine()
        alignment_data = engine.align(text, word_boundaries)
        
        # Create timestamps data
        timestamps_data = {
            "text": text,
            "sentences": alignment_data["sentences"],
            "words": alignment_data["words"]
        }
        
        # Save timestamps to JSON file
        timestamps_path = output_path.replace(".mp3", ".timestamps.json")
        with open(timestamps_path, "w", encoding="utf-8") as f:
            json.dump(timestamps_data, f, ensure_ascii=False, indent=2)
        
        print(i18n.get("debug_edge_tts_ok", output_path))
        print(f"DEBUG: Timestamps saved to {timestamps_path}")
        
        return output_path, timestamps_data
        
    except Exception as e:
        msg = str(e)
        if "No audio was received" in msg:
            msg += " (Hint: Does this voice support the text language?)"
        print(i18n.get("debug_edge_tts_fail", msg))
        return None, None


async def generate_audio_edge_tts_async(text, voice, rate, volume, pitch, output_path):
    """
    Async function to generate audio using edge_tts (legacy, without timestamps).
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
            result, _ = loop.run_until_complete(
                generate_audio_with_timestamps_async(text, voice, rate_str, volume_str, pitch_str, out_path)
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
    Returns (path, error, timestamps_data).
    """
    text = sanitize_text(text)
    if not text:
        return None, i18n.get("debug_empty_text"), None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    match = re.search(r", (.*Neural)\)$", voice)
    part = re.sub(r'\W+', '', match.group(1)) if match else "Unknown"
    fname = f"Anki-TTS-Edge_{part}_{ts}.mp3"
    out_path = os.path.join(AUDIO_DIR, fname)
    
    print(i18n.get("debug_generating_audio", voice, rate, volume, pitch))
    print(i18n.get("debug_output_path", out_path))

    try:
        result, timestamps = await generate_audio_with_timestamps_async(
            text, voice, rate, volume, pitch, out_path
        )
        if result:
            return result, None, timestamps
        else:
            return None, i18n.get("debug_edge_tts_internal_error"), None
    except Exception as e:
        return None, str(e), None


def load_timestamps(audio_path):
    """
    Load timestamps data from JSON file associated with an audio file.
    Returns timestamps_data dict or None if not found.
    """
    timestamps_path = audio_path.replace(".mp3", ".timestamps.json")
    if os.path.exists(timestamps_path):
        try:
            with open(timestamps_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"DEBUG: Failed to load timestamps: {e}")
    return None