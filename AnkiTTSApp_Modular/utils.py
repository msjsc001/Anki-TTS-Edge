# utils.py - REMOVE sanitize_text function

import os
import re
import ctypes
from ctypes import wintypes
import win32clipboard
import win32con
import pygame # Needed for manage_audio_files check

# Import necessary variables/objects from other modules
import config
# Removed: import main

# --- Text Processing ---
# REMOVED: def sanitize_text(text): ...

# --- Clipboard Operations ---
# <<<<<<< 修改: 添加 app_instance 参数 >>>>>>>>>
def copy_file_to_clipboard(file_path, app_instance=None):
    # ... (函数内容保持不变) ...
    try:
        class DROPFILES(ctypes.Structure): _fields_=[("pF",wintypes.DWORD),("pt",wintypes.POINT),("fNC",wintypes.BOOL),("fW",wintypes.BOOL)]
        abs_path = os.path.abspath(file_path); offset = ctypes.sizeof(DROPFILES)
        buf_size = offset + (len(abs_path) + 2) * ctypes.sizeof(wintypes.WCHAR); buf = (ctypes.c_char * buf_size)()
        df=ctypes.cast(buf,ctypes.POINTER(DROPFILES)).contents; df.pF=offset; df.fW=True
        path_bytes=abs_path.encode('utf-16-le'); ctypes.memmove(ctypes.byref(buf, offset), path_bytes, len(path_bytes))
        buf[offset + len(path_bytes)]=0; buf[offset + len(path_bytes) + 1]=0
        win32clipboard.OpenClipboard(); win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_HDROP, buf); win32clipboard.CloseClipboard()
        if app_instance: print(app_instance._("debug_file_copied", file_path)); app_instance.update_status("status_file_copied", duration=3)
        else: print(f"File copied to clipboard (CF_HDROP): {file_path}")
    except Exception as e:
        if app_instance: print(app_instance._("debug_copy_fail", e)); app_instance.update_status("status_copy_failed", error=True)
        else: print(f"Failed to copy file to clipboard: {e}")

# --- File Management ---
# <<<<<<< 修改: 添加 app_instance 参数 >>>>>>>>>
def manage_audio_files(app_instance=None):
    # ... (函数内容保持不变) ...
    try:
        max_str = app_instance.max_files_entry.get() if app_instance and hasattr(app_instance, 'max_files_entry') else str(config.DEFAULT_MAX_AUDIO_FILES)
        max_f = int(max_str) if max_str.isdigit() else config.DEFAULT_MAX_AUDIO_FILES
        max_f = max(1, min(50, max_f))
    except Exception: max_f = config.DEFAULT_MAX_AUDIO_FILES
    try:
        if not os.path.exists(config.AUDIO_DIR): return
        files = sorted( [f for f in os.listdir(config.AUDIO_DIR) if f.endswith(".mp3")], key=lambda x: os.path.getctime(os.path.join(config.AUDIO_DIR, x)) )
        while len(files) > max_f:
            file_rm = files.pop(0); path_rm = os.path.join(config.AUDIO_DIR, file_rm)
            try:
                mixer_busy = False
                if pygame.mixer.get_init(): mixer_busy = pygame.mixer.music.get_busy()
                if mixer_busy and app_instance: print(app_instance._("debug_delete_busy", file_rm))
                os.remove(path_rm)
                if app_instance: print(app_instance._("debug_delete_file", file_rm))
                else: print(f"Deleted old audio file: {file_rm}")
            except PermissionError as e:
                msg = f"Delete failed (Permission): {file_rm}"
                if app_instance: print(app_instance._("debug_delete_fail_permission", file_rm, e))
                else: print(msg)
            except OSError as e:
                msg = f"Delete failed (OS Error): {file_rm}"
                if app_instance: print(app_instance._("debug_delete_fail_os", file_rm, e))
                else: print(msg)
    except Exception as e:
        msg = f"File management error: {e}"
        if app_instance: print(app_instance._("debug_manage_files_error", e))
        else: print(msg)