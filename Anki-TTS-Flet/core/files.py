import os
import ctypes
from ctypes import wintypes
import time
import struct
import win32clipboard
import win32con
import pygame
from config.constants import AUDIO_DIR, DEFAULT_MAX_AUDIO_FILES
from utils.i18n import i18n


def _build_dropfiles_payload(paths):
    file_block = ("\0".join(paths) + "\0\0").encode("utf-16le")
    header = struct.pack("<IiiII", 20, 0, 0, 0, 1)
    return header + file_block


def _set_clipboard_data(fmt, data):
    if fmt == win32con.CF_HDROP:
        if isinstance(data, (list, tuple)):
            payload = _build_dropfiles_payload([os.path.abspath(path) for path in data])
        else:
            payload = data
        win32clipboard.SetClipboardData(win32con.CF_HDROP, payload)
        return
    win32clipboard.SetClipboardData(fmt, data)

def capture_clipboard_snapshot():
    snapshot = {"formats": []}
    html_format = win32clipboard.RegisterClipboardFormat("HTML Format")
    _open_clipboard_with_retry()
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            try:
                snapshot["formats"].append((win32con.CF_UNICODETEXT, win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)))
            except Exception:
                pass
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
            try:
                snapshot["formats"].append((win32con.CF_TEXT, win32clipboard.GetClipboardData(win32con.CF_TEXT)))
            except Exception:
                pass
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
            try:
                snapshot["formats"].append((win32con.CF_HDROP, tuple(win32clipboard.GetClipboardData(win32con.CF_HDROP))))
            except Exception:
                pass
        if html_format and win32clipboard.IsClipboardFormatAvailable(html_format):
            try:
                snapshot["formats"].append((html_format, win32clipboard.GetClipboardData(html_format)))
            except Exception:
                pass
    finally:
        win32clipboard.CloseClipboard()
    return snapshot


def restore_clipboard_snapshot(snapshot):
    _open_clipboard_with_retry()
    try:
        win32clipboard.EmptyClipboard()
        for fmt, data in (snapshot or {}).get("formats", []):
            try:
                _set_clipboard_data(fmt, data)
            except Exception:
                continue
    finally:
        win32clipboard.CloseClipboard()


def copy_file_to_clipboard(file_path):
    """
    Copies a file to the clipboard using CF_HDROP.
    Returns True if successful, raises Exception otherwise.
    """
    try:
        abs_path = os.path.abspath(file_path)
        for _ in range(3):
            _open_clipboard_with_retry()
            try:
                win32clipboard.EmptyClipboard()
                _set_clipboard_data(win32con.CF_HDROP, (abs_path,))
                preferred_drop_effect = win32clipboard.RegisterClipboardFormat("Preferred DropEffect")
                win32clipboard.SetClipboardData(preferred_drop_effect, struct.pack("<I", 1))
            finally:
                win32clipboard.CloseClipboard()

            clipboard_files = get_clipboard_file_list()
            normalized_files = {os.path.abspath(path) for path in clipboard_files}
            if abs_path in normalized_files:
                print(i18n.get("debug_file_copied", file_path))
                return True
            time.sleep(0.05)

        raise RuntimeError(f"File clipboard verification failed: {abs_path}")
    except Exception as e:
        print(i18n.get("debug_copy_fail", e))
        raise e


def get_clipboard_file_list():
    opened = False
    _open_clipboard_with_retry()
    opened = True
    try:
        if not win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
            return []
        data = win32clipboard.GetClipboardData(win32con.CF_HDROP)
        return list(data) if data else []
    finally:
        if opened:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass


def _open_clipboard_with_retry(retries=12, delay=0.03):
    last_error = None
    for _ in range(retries):
        try:
            win32clipboard.OpenClipboard()
            return
        except Exception as ex:
            last_error = ex
            time.sleep(delay)
    raise last_error

def manage_audio_files(max_files=DEFAULT_MAX_AUDIO_FILES):
    """
    Manages audio files in the audio directory, keeping only the most recent ones.
    """
    try:
        max_f = int(max_files)
        max_f = max(1, min(50, max_f))
    except (ValueError, TypeError):
        max_f = DEFAULT_MAX_AUDIO_FILES

    try:
        if not os.path.exists(AUDIO_DIR):
            return

        files = sorted(
            [f for f in os.listdir(AUDIO_DIR) if f.endswith(".mp3")],
            key=lambda x: os.path.getctime(os.path.join(AUDIO_DIR, x))
        )
        
        while len(files) > max_f:
            file_rm = files.pop(0)
            path_rm = os.path.join(AUDIO_DIR, file_rm)
            try:
                mixer_busy = False
                if pygame.mixer.get_init():
                    mixer_busy = pygame.mixer.music.get_busy()
                
                if mixer_busy:
                    print(i18n.get("debug_delete_busy", file_rm))
                    
                os.remove(path_rm)
                print(i18n.get("debug_delete_file", file_rm))
            except PermissionError as e:
                print(i18n.get("debug_delete_fail_permission", file_rm, e))
            except OSError as e:
                print(i18n.get("debug_delete_fail_os", file_rm, e))
                
    except Exception as e:
        print(i18n.get("debug_manage_files_error", e))
