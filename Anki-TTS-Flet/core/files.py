import os
import ctypes
from ctypes import wintypes
import win32clipboard
import win32con
import pygame
from config.constants import AUDIO_DIR, DEFAULT_MAX_AUDIO_FILES
from utils.i18n import i18n

def copy_file_to_clipboard(file_path):
    """
    Copies a file to the clipboard using CF_HDROP.
    Returns True if successful, raises Exception otherwise.
    """
    try:
        class DROPFILES(ctypes.Structure):
            _fields_=[("pF",wintypes.DWORD),("pt",wintypes.POINT),("fNC",wintypes.BOOL),("fW",wintypes.BOOL)]
        
        abs_path = os.path.abspath(file_path)
        offset = ctypes.sizeof(DROPFILES)
        # +2 for double null terminator
        buf_size = offset + (len(abs_path) + 2) * ctypes.sizeof(wintypes.WCHAR)
        buf = (ctypes.c_char * buf_size)()
        
        df = ctypes.cast(buf, ctypes.POINTER(DROPFILES)).contents
        df.pF = offset
        df.fW = True
        
        path_bytes = abs_path.encode('utf-16-le')
        ctypes.memmove(ctypes.byref(buf, offset), path_bytes, len(path_bytes))
        
        # Null terminators are already 0 by default initialization, but for clarity:
        buf[offset + len(path_bytes)] = 0
        buf[offset + len(path_bytes) + 1] = 0
        
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_HDROP, buf)
        win32clipboard.CloseClipboard()
        
        print(i18n.get("debug_file_copied", file_path))
        return True
    except Exception as e:
        print(i18n.get("debug_copy_fail", e))
        raise e

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