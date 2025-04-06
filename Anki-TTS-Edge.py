# ==============================================================================
# 导入所需库
# ==============================================================================
import sys
import os
import re
import shutil
import time
import threading
import asyncio
from datetime import datetime
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import messagebox, colorchooser
import json
import math
# <<<<<<< 添加: 托盘图标所需库 >>>>>>>>>
try:
    from PIL import Image
    import pystray
except ImportError as e:
    print(f"错误：缺少托盘图标所需的库: {e}。请运行 'pip install Pillow pystray'")
    # 可以选择退出或禁用托盘功能
    # sys.exit(1)
    pystray = None # 标记 pystray 不可用
    Image = None   # 标记 Pillow 不可用

# ==============================================================================
# <<<<<<< 添加: 自定义窗口标题 (从 JSON 加载) >>>>>>>>>
# ==============================================================================
# Default title if JSON fails
CUSTOM_WINDOW_TITLE = "Anki-TTS-Edge (v1.6)"

# ==============================================================================
# <<<<<<< 添加: 加载外部翻译文件 >>>>>>>>>
# ==============================================================================
TRANSLATIONS_FILE = "translations.json"
TRANSLATIONS = {} # Global dict to hold loaded translations

def load_translations(filename=TRANSLATIONS_FILE):
    """Loads translations from a JSON file."""
    global TRANSLATIONS, CUSTOM_WINDOW_TITLE
    # Default structure in case file is missing or invalid
    default_translations = {
        "zh": {"window_title": "Anki-TTS-Edge (错误)", "status_ready": "准备就绪 (错误: 未加载翻译)"},
        "en": {"window_title": "Anki-TTS-Edge (Error)", "status_ready": "Ready (Error: Translations not loaded)"}
    }
    filepath = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            TRANSLATIONS = json.load(f)
        print(f"成功加载翻译文件: {filename}")
        # Update default title from loaded JSON (assuming 'zh' exists)
        CUSTOM_WINDOW_TITLE = TRANSLATIONS.get("zh", {}).get("window_title", CUSTOM_WINDOW_TITLE)
    except FileNotFoundError:
        print(f"错误: 翻译文件未找到: {filepath}")
        print("将使用内置的默认文本 (可能不完整)。")
        TRANSLATIONS = default_translations
    except json.JSONDecodeError as e:
        print(f"错误: 解析翻译文件失败 ({filename}): {e}")
        print("将使用内置的默认文本 (可能不完整)。")
        TRANSLATIONS = default_translations
    except Exception as e:
        print(f"加载翻译时发生未知错误: {e}")
        TRANSLATIONS = default_translations

# Load translations at the start
load_translations()

# ==============================================================================
# 依赖检查与导入 (添加 pystray 和 Pillow)
# ==============================================================================
def check_dependencies():
    """检查所有依赖库是否安装"""
    # 添加 pystray 和 Pillow (PIL) 到依赖列表
    dependencies = {
        "customtkinter": "pip install customtkinter",
        "edge_tts": "pip install edge-tts",
        "pyperclip": "pip install pyperclip",
        "pygame": "pip install pygame",
        "pynput": "pip install pynput",
        "win32clipboard": "pip install pywin32",
        "win32con": "pip install pywin32",
        "pystray": "pip install pystray", # 新增
        "PIL": "pip install Pillow"      # 新增 (Pillow 提供 PIL 模块)
    }
    missing = []; checked_pywin32 = False
    for module, install_cmd in dependencies.items():
        try:
            if module == "edge_tts": import edge_tts.communicate
            elif module.startswith("win32"):
                if not checked_pywin32: __import__("win32clipboard"); checked_pywin32 = True
            elif module == "pynput": from pynput import mouse, keyboard
            elif module == "pygame": import pygame
            elif module == "pystray": import pystray # 检查 pystray
            elif module == "PIL": from PIL import Image # 检查 Pillow (模块名为 PIL)
            else: __import__(module)
        except ImportError:
            # 特殊处理 Pillow 的导入检查，因为模块名是 PIL
            # 只有当尝试导入 PIL 失败时才添加到 missing 列表
            if module == "PIL":
                 # 再次尝试导入，确认是否真的缺失
                 try:
                     from PIL import Image
                 except ImportError:
                     missing.append((module, install_cmd))
            elif module.startswith("win32"):
                if not checked_pywin32: missing.append((module, install_cmd)); checked_pywin32 = True
            else: missing.append((module, install_cmd))
    if missing:
        print("以下依赖库未安装："); install_cmds = set()
        for module, install_cmd in missing: print(f"- {module}"); install_cmds.add(install_cmd)
        print("\n请确保在激活的虚拟环境 (.venv) 中安装以上依赖库后重新运行脚本。")
        print(f"建议安装命令: {' '.join(install_cmds)}"); sys.exit(1)
    else: print("所有依赖库已安装！")
check_dependencies()
# Imports
import customtkinter as ctk; import pyperclip
try: import pygame
except ImportError: print("错误：无法导入 pygame。请确保已安装：pip install pygame"); sys.exit(1)
from pynput import mouse, keyboard
import win32clipboard, win32con
import edge_tts
from edge_tts import VoicesManager
# <<<<<<< 添加: 托盘图标所需库 >>>>>>>>>
try:
    from PIL import Image
    import pystray
except ImportError as e:
    print(f"错误：缺少托盘图标所需的库: {e}。请运行 'pip install Pillow pystray'")
    # 可以选择退出或禁用托盘功能
    # sys.exit(1)
    pystray = None # 标记 pystray 不可用
    Image = None   # 标记 Pillow 不可用
# <<<<<<< 添加: 托盘图标所需库 (Import 移到文件顶部) >>>>>>>>>
# (Import statements moved to the top of the file)

# ==============================================================================
# 全局配置变量 (无修改)
# ==============================================================================
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "音频")
DEFAULT_MAX_AUDIO_FILES = 20
DEFAULT_VOICE = "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)"
DEFAULT_APPEARANCE_MODE = "light"
DEFAULT_CUSTOM_COLOR = "#1F6AA5"
FLOAT_WINDOW_TIMEOUT = 2
MOUSE_TIP_TIMEOUT = 1
SETTINGS_FILE = "voice_settings.json"
MOUSE_DRAG_THRESHOLD = 10 # Pixels
os.makedirs(AUDIO_DIR, exist_ok=True)

# ==============================================================================
# 全局变量 (添加托盘相关)
# ==============================================================================
app = None; status_update_job = None; clipboard_monitor_active = False
clipboard_polling_thread = None; previous_clipboard_poll_content = None
mouse_listener_thread = None; mouse_listener = None
is_dragging = False; drag_start_pos = (0, 0); drag_start_time = 0
# <<<<<<< 添加: 托盘图标全局变量 >>>>>>>>>
icon_image = None # 加载的 PIL Image 对象 (全局缓存)
ICON_PATH = "icon.ico" # 图标文件路径 (确保此文件存在)
tray_icon = None # pystray Icon 实例 (全局引用，用于线程)
tray_thread = None # 运行 pystray 的线程

# ==============================================================================
# 模块 1：文本处理 (无修改)
# ==============================================================================
def sanitize_text(text):
    if not text: return ""
    text = re.sub(r'[^\w\s\.,!?;:\'"()\[\]{}<>%&$@#*+\-=/]', '', text, flags=re.UNICODE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text else ""

# ==============================================================================
# 模块 2：剪贴板操作 (使用翻译打印)
# ==============================================================================
def copy_file_to_clipboard(file_path):
    try:
        # ... (same CF_HDROP logic) ...
        class DROPFILES(ctypes.Structure): _fields_=[("pF",wintypes.DWORD),("pt",wintypes.POINT),("fNC",wintypes.BOOL),("fW",wintypes.BOOL)]
        abs_path = os.path.abspath(file_path); offset = ctypes.sizeof(DROPFILES)
        buf_size = offset + (len(abs_path) + 2) * ctypes.sizeof(wintypes.WCHAR); buf = (ctypes.c_char * buf_size)()
        df=ctypes.cast(buf,ctypes.POINTER(DROPFILES)).contents; df.pF=offset; df.fW=True
        path_bytes=abs_path.encode('utf-16-le'); ctypes.memmove(ctypes.byref(buf, offset), path_bytes, len(path_bytes))
        buf[offset + len(path_bytes)]=0; buf[offset + len(path_bytes) + 1]=0
        win32clipboard.OpenClipboard(); win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_HDROP, buf); win32clipboard.CloseClipboard()
        # Use translation helper, check if app exists
        if app: print(app._("debug_file_copied", file_path)); app.update_status("status_file_copied", duration=3)
        else: print(f"File copied to clipboard (CF_HDROP): {file_path}") # Fallback print
    except Exception as e:
        if app: print(app._("debug_copy_fail", e)); app.update_status("status_copy_failed", error=True)
        else: print(f"Failed to copy file to clipboard: {e}") # Fallback print

# ==============================================================================
# 模块 3：声音列表获取 (使用翻译打印)
# ==============================================================================
async def get_available_voices_async():
    try:
        # ... (same voice finding logic) ...
        voices = await VoicesManager.create(); raw_list = voices.find()
        pattern = re.compile(r"MSSTT.*\((.*),\s*(.*Neural)\)") # Simplified pattern example if needed
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
        total = sum(len(v) for lang_data in sorted_h.values() for v in lang_data.values())
        # Use translation helper
        if app: print(app._("debug_voices_loaded", total))
        else: print(f"Found {total} voices...") # Fallback
        return sorted_h
    except Exception as e:
        if app: print(app._("debug_voices_load_failed", e)); app.update_status("status_generate_error", error=True)
        else: print(f"Failed to get voice list: {e}") # Fallback
        return {}

def refresh_voices_list():
    def run_async():
        data = {}
        try: loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop); data=loop.run_until_complete(get_available_voices_async()); loop.close()
        except Exception as e:
             if app: print(app._("debug_run_async_voices_error", e))
             else: print(f"Error running async get voices task: {e}")
             data = {}
        finally:
            if app and app.root.winfo_exists(): app.root.after(0, app.update_voice_ui, data)
    threading.Thread(target=run_async, daemon=True).start()

# ==============================================================================
# 模块 4：音频生成 (使用翻译打印)
# ==============================================================================
async def generate_audio_edge_tts_async(text, voice, rate, volume, pitch, output_path):
    try:
        comm = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        await comm.save(output_path)
        if app: print(app._("debug_edge_tts_ok", output_path))
        else: print(f"Edge TTS audio generated successfully: {output_path}")
        return output_path
    except Exception as e:
        if app: print(app._("debug_edge_tts_fail", e))
        else: print(f"Edge TTS audio generation failed: {e}")
        return None

def generate_audio(text, voice, rate_str, volume_str, pitch_str, on_complete=None):
    text = sanitize_text(text)
    if not text:
        if app: print(app._("debug_empty_text")); app.update_status("status_empty_text_error", error=True)
        else: print("Text is empty...") # Fallback
        if on_complete:
            callback = lambda: on_complete(None, "Text empty")
            if app and app.root.winfo_exists(): app.root.after(0, callback)
            else: callback()
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S"); match = re.search(r", (.*Neural)\)$", voice)
    part = re.sub(r'\W+', '', match.group(1)) if match else "Unknown"; fname = f"Anki-TTS-Edge_{part}_{ts}.mp3"
    out_path = os.path.join(AUDIO_DIR, fname)
    if app: print(app._("debug_generating_audio", voice, rate_str, volume_str, pitch_str)); print(app._("debug_output_path", out_path))
    else: print(f"Generating audio... Output: {out_path}") # Fallback
    def run_async():
        result = None; error = None
        try:
            loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop); result=loop.run_until_complete(generate_audio_edge_tts_async(text, voice, rate_str, volume_str, pitch_str, out_path)); loop.close()
            if not result: error = app._("debug_edge_tts_internal_error") if app else "Edge TTS internal error"
        except Exception as e:
            if app: print(app._("debug_generate_thread_error", e)); error = str(e)
            else: print(f"Error in generation thread: {e}"); error = str(e)
        finally:
            if on_complete:
                callback = lambda p=result, e=error: on_complete(p, e)
                if app and app.root.winfo_exists(): app.root.after(0, callback)
                else: callback()
    threading.Thread(target=run_async, daemon=True).start()

# ==============================================================================
# 模块 5：文件管理 (使用翻译打印)
# ==============================================================================
def manage_audio_files():
    try: max_str = app.max_files_entry.get() if app and hasattr(app, 'max_files_entry') else str(DEFAULT_MAX_AUDIO_FILES); max_f = int(max_str) if max_str.isdigit() else DEFAULT_MAX_AUDIO_FILES; max_f = max(1, min(50, max_f))
    except: max_f = DEFAULT_MAX_AUDIO_FILES
    try:
        if not os.path.exists(AUDIO_DIR): return
        files = sorted( [f for f in os.listdir(AUDIO_DIR) if f.endswith(".mp3")], key=lambda x: os.path.getctime(os.path.join(AUDIO_DIR, x)) )
        while len(files) > max_f:
            file_rm = files.pop(0); path_rm = os.path.join(AUDIO_DIR, file_rm)
            try:
                mixer_busy = False
                if pygame.mixer.get_init(): mixer_busy = pygame.mixer.music.get_busy()
                if mixer_busy and app: print(app._("debug_delete_busy", file_rm))
                os.remove(path_rm)
                if app: print(app._("debug_delete_file", file_rm))
            except PermissionError as e: print(app._("debug_delete_fail_permission", file_rm, e) if app else f"Delete failed (Permission): {file_rm}")
            except OSError as e: print(app._("debug_delete_fail_os", file_rm, e) if app else f"Delete failed (OS): {file_rm}")
    except Exception as e: print(app._("debug_manage_files_error", e) if app else f"File management error: {e}")

# ==============================================================================
# 模块 6：UI 主类 (EdgeTTSApp) - Language Integration
# ==============================================================================
class EdgeTTSApp:
    def __init__(self, root):
        self.root = root; self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        global app; app = self
        # Language Setup (BEFORE UI that uses translations)
        settings = self.load_settings()
        self.current_language = settings.get("language", "zh")
        self.root.title(self._("window_title"))

        # <<<<<<< 添加: 设置窗口图标 >>>>>>>>>
        icon_path = os.path.join(os.path.dirname(__file__), ICON_PATH)
        try:
            # Ensure the icon file exists before trying to set it
            if os.path.exists(icon_path):
                 self.root.iconbitmap(icon_path)
                 print(f"窗口图标已设置为: {icon_path}")
            else:
                 print(f"警告: 窗口图标文件未找到: {icon_path}")
        except tk.TclError as e:
            print(f"设置窗口图标失败 (可能是不支持的格式或路径问题): {e}")
        except Exception as e:
             print(f"设置窗口图标时发生未知错误: {e}")


        # Pygame Init
        try: pygame.init(); pygame.mixer.init(); print(self._("debug_init_pygame_ok"))
        except Exception as e:
            print(self._("debug_init_pygame_fail").format(e))
            messagebox.showerror(self._("error_mixer_init_title"), self._("error_mixer_init_message").format(e))

        # UI Vars
        self.voice_display_to_full_map = {}; self.hierarchical_voice_data = {}
        self.current_full_voice_name = None; self.current_custom_color = None
        # Appearance
        appearance = settings.get("appearance_mode", DEFAULT_APPEARANCE_MODE)
        self.current_custom_color = settings.get("custom_theme_color", DEFAULT_CUSTOM_COLOR)
        ctk.set_appearance_mode(appearance)
        # Store references to widgets needing language updates
        self._language_widgets = {}

        # --- Main Frame ---
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent"); self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1); self.main_frame.grid_rowconfigure(1, weight=1)

        # --- Text Input Area ---
        text_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent"); text_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15)); text_frame.grid_columnconfigure(0, weight=1)
        self.text_input_label = ctk.CTkLabel(text_frame, text=self._("input_text_label"), font=ctk.CTkFont(size=14, weight="bold")); self.text_input_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        self._language_widgets['input_text_label'] = self.text_input_label
        self.text_input = ctk.CTkTextbox(text_frame, height=100, wrap="word", corner_radius=8, border_width=1); self.text_input.grid(row=1, column=0, sticky="nsew")

        # --- Tab View ---
        self.tab_view = ctk.CTkTabview(self.main_frame, corner_radius=8); self.tab_view.grid(row=1, column=0, sticky="nsew", pady=0)
        # Store keys for tab renaming later
        self._language_widgets['tab_voices'] = "tab_voices"
        self._language_widgets['tab_settings'] = "tab_settings"
        self._language_widgets['tab_appearance'] = "tab_appearance"
        self.tab_view.add(self._("tab_voices"))
        self.tab_view.add(self._("tab_settings"))
        self.tab_view.add(self._("tab_appearance"))

        # --- Voice Tab ---
        voice_tab = self.tab_view.tab(self._("tab_voices")); voice_tab.grid_columnconfigure((0, 1), weight=1); voice_tab.grid_rowconfigure(1, weight=1)
        left_outer = ctk.CTkFrame(voice_tab, fg_color="transparent"); left_outer.grid(row=0, column=0, rowspan=2, padx=(0, 5), pady=5, sticky="nsew"); left_outer.grid_rowconfigure(1, weight=1)
        self.language_filter_entry_left = ctk.CTkEntry(left_outer, placeholder_text=self._("filter_language_placeholder")); self.language_filter_entry_left.grid(row=0, column=0, padx=0, pady=(0, 5), sticky="ew"); self.language_filter_entry_left.bind("<KeyRelease>", lambda e: self._filter_voices_inline('left'))
        self._language_widgets['filter_language_placeholder_left'] = self.language_filter_entry_left
        self.inline_voice_list_frame_left = ctk.CTkScrollableFrame(left_outer, label_text=self._("voice_list_label_1"), height=150); self.inline_voice_list_frame_left.grid(row=1, column=0, padx=0, pady=0, sticky="nsew"); self.inline_voice_list_frame_left.grid_columnconfigure(0, weight=1)
        self._language_widgets['voice_list_label_1'] = self.inline_voice_list_frame_left
        right_outer = ctk.CTkFrame(voice_tab, fg_color="transparent"); right_outer.grid(row=0, column=1, rowspan=2, padx=(5, 0), pady=5, sticky="nsew"); right_outer.grid_rowconfigure(1, weight=1)
        self.language_filter_entry_right = ctk.CTkEntry(right_outer, placeholder_text=self._("filter_language_placeholder")); self.language_filter_entry_right.grid(row=0, column=0, padx=0, pady=(0, 5), sticky="ew"); self.language_filter_entry_right.bind("<KeyRelease>", lambda e: self._filter_voices_inline('right'))
        self._language_widgets['filter_language_placeholder_right'] = self.language_filter_entry_right
        self.inline_voice_list_frame_right = ctk.CTkScrollableFrame(right_outer, label_text=self._("voice_list_label_2"), height=150); self.inline_voice_list_frame_right.grid(row=1, column=0, padx=0, pady=0, sticky="nsew"); self.inline_voice_list_frame_right.grid_columnconfigure(0, weight=1)
        self._language_widgets['voice_list_label_2'] = self.inline_voice_list_frame_right
        saved_f_l = settings.get("language_filter_left", "zh"); saved_f_r = settings.get("language_filter_right", "en")
        self.language_filter_entry_left.insert(0, saved_f_l); self.language_filter_entry_right.insert(0, saved_f_r)
        controls_frame = ctk.CTkFrame(voice_tab, fg_color="transparent"); controls_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="ew"); controls_frame.grid_columnconfigure(1, weight=1)
        self.refresh_button = ctk.CTkButton(controls_frame, text=self._("refresh_voices_button"), command=self.refresh_voices_ui, font=ctk.CTkFont(size=12)); self.refresh_button.grid(row=0, column=0, columnspan=3, padx=0, pady=(0, 10), sticky="ew")
        self._language_widgets['refresh_voices_button'] = self.refresh_button
        self.rate_label = ctk.CTkLabel(controls_frame, text=self._("rate_label")); self.rate_label.grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        self._language_widgets['rate_label'] = self.rate_label
        self.rate_slider_var = ctk.IntVar(value=settings.get("rate", 0)); self.rate_slider = ctk.CTkSlider(controls_frame, from_=-100, to=100, number_of_steps=40, variable=self.rate_slider_var, command=self.update_rate_label); self.rate_slider.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.rate_value_label = ctk.CTkLabel(controls_frame, text=f"{self.rate_slider_var.get():+}%", width=45); self.rate_value_label.grid(row=1, column=2, padx=(5, 0), pady=5, sticky="w")
        self.volume_label = ctk.CTkLabel(controls_frame, text=self._("volume_label")); self.volume_label.grid(row=2, column=0, padx=(0, 5), pady=5, sticky="w")
        self._language_widgets['volume_label'] = self.volume_label
        self.volume_slider_var = ctk.IntVar(value=settings.get("volume", 0)); self.volume_slider = ctk.CTkSlider(controls_frame, from_=-100, to=100, number_of_steps=40, variable=self.volume_slider_var, command=self.update_volume_label); self.volume_slider.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.volume_value_label = ctk.CTkLabel(controls_frame, text=f"{self.volume_slider_var.get():+}%", width=45); self.volume_value_label.grid(row=2, column=2, padx=(5, 0), pady=5, sticky="w")

        # --- Settings Tab ---
        settings_tab = self.tab_view.tab(self._("tab_settings")); settings_tab.grid_columnconfigure(0, weight=1)
        output_cache_frame = ctk.CTkFrame(settings_tab); output_cache_frame.pack(fill="x", padx=10, pady=10); output_cache_frame.grid_columnconfigure(1, weight=1)
        self.settings_output_cache_label_widget = ctk.CTkLabel(output_cache_frame, text=self._("settings_output_cache_label"), font=ctk.CTkFont(weight="bold")); self.settings_output_cache_label_widget.grid(row=0, column=0, columnspan=3, pady=(5, 10), padx=10, sticky="w")
        self._language_widgets['settings_output_cache_label'] = self.settings_output_cache_label_widget
        self.copy_to_clipboard_var = ctk.BooleanVar(value=settings.get("copy_path_enabled", True)); self.copy_to_clipboard_switch = ctk.CTkSwitch(output_cache_frame, text=self._("settings_copy_label"), variable=self.copy_to_clipboard_var, onvalue=True, offvalue=False); self.copy_to_clipboard_switch.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self._language_widgets['settings_copy_label'] = self.copy_to_clipboard_switch
        self.play_audio_var = ctk.BooleanVar(value=settings.get("autoplay_enabled", False)); self.play_audio_switch = ctk.CTkSwitch(output_cache_frame, text=self._("settings_autoplay_label"), variable=self.play_audio_var, onvalue=True, offvalue=False); self.play_audio_switch.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self._language_widgets['settings_autoplay_label'] = self.play_audio_switch
        self.settings_max_files_label_widget = ctk.CTkLabel(output_cache_frame, text=self._("settings_max_files_label")); self.settings_max_files_label_widget.grid(row=2, column=0, padx=(10, 5), pady=(5, 10), sticky="w")
        self._language_widgets['settings_max_files_label'] = self.settings_max_files_label_widget
        self.max_files_entry = ctk.CTkEntry(output_cache_frame, width=60); self.max_files_entry.insert(0, str(settings.get("max_audio_files", DEFAULT_MAX_AUDIO_FILES))); self.max_files_entry.grid(row=2, column=1, padx=5, pady=(5, 10), sticky="w")
        clipboard_frame = ctk.CTkFrame(settings_tab); clipboard_frame.pack(fill="x", padx=10, pady=(0, 10)); clipboard_frame.grid_columnconfigure(0, weight=1)
        self.settings_clipboard_label_widget = ctk.CTkLabel(clipboard_frame, text=self._("settings_clipboard_label"), font=ctk.CTkFont(weight="bold")); self.settings_clipboard_label_widget.grid(row=0, column=0, columnspan=2, pady=(5, 10), padx=10, sticky="w")
        self._language_widgets['settings_clipboard_label'] = self.settings_clipboard_label_widget
        self.select_to_audio_var = ctk.BooleanVar(value=settings.get("monitor_enabled", False)); self.select_to_audio_switch = ctk.CTkSwitch(clipboard_frame, text=self._("settings_enable_ctrl_c_label"), variable=self.select_to_audio_var, command=self.toggle_select_to_audio, onvalue=True, offvalue=False); self.select_to_audio_switch.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self._language_widgets['settings_enable_ctrl_c_label'] = self.select_to_audio_switch
        self.select_trigger_var = ctk.BooleanVar(value=settings.get("select_trigger_enabled", False)); self.select_trigger_switch = ctk.CTkSwitch(clipboard_frame, text=self._("settings_enable_selection_label"), variable=self.select_trigger_var, command=self.save_settings, onvalue=True, offvalue=False); self.select_trigger_switch.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w") # Adjusted pady
        self._language_widgets['settings_enable_selection_label'] = self.select_trigger_switch
        # <<<<<<< 添加: 最小化到托盘开关 >>>>>>>>>
        self.minimize_to_tray_var = ctk.BooleanVar(value=settings.get("minimize_to_tray", False)); self.minimize_to_tray_switch = ctk.CTkSwitch(clipboard_frame, text=self._("settings_minimize_to_tray_label"), variable=self.minimize_to_tray_var, command=self.save_settings, onvalue=True, offvalue=False); self.minimize_to_tray_switch.grid(row=3, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="w") # Added pady
        self._language_widgets['settings_minimize_to_tray_label'] = self.minimize_to_tray_switch

        # --- Appearance Tab ---
        appearance_tab = self.tab_view.tab(self._("tab_appearance")); appearance_tab.grid_columnconfigure(1, weight=1)
        self.appearance_theme_label_widget = ctk.CTkLabel(appearance_tab, text=self._("appearance_theme_label")); self.appearance_theme_label_widget.grid(row=0, column=0, padx=(15, 5), pady=15, sticky="w")
        self._language_widgets['appearance_theme_label'] = self.appearance_theme_label_widget
        self.appearance_mode_segmented_button = ctk.CTkSegmentedButton( appearance_tab, values=[self._("appearance_mode_light"), self._("appearance_mode_dark")], command=self._change_appearance_mode ); self.appearance_mode_segmented_button.grid(row=0, column=1, columnspan=3, padx=5, pady=15, sticky="ew")
        initial_mode_text = self._("appearance_mode_light") if appearance == "light" else self._("appearance_mode_dark"); self.appearance_mode_segmented_button.set(initial_mode_text)
        self._language_widgets['appearance_mode_light'] = self.appearance_mode_segmented_button # Store button itself for value update
        self._language_widgets['appearance_mode_dark'] = self.appearance_mode_segmented_button # Store button itself for value update
        self.appearance_color_label_widget = ctk.CTkLabel(appearance_tab, text=self._("appearance_color_label")); self.appearance_color_label_widget.grid(row=1, column=0, padx=(15, 5), pady=(5, 15), sticky="w")
        self._language_widgets['appearance_color_label'] = self.appearance_color_label_widget
        self.custom_color_entry = ctk.CTkEntry(appearance_tab, placeholder_text="#1F6AA5"); self.custom_color_entry.grid(row=1, column=1, padx=5, pady=(5, 15), sticky="ew"); self.custom_color_entry.insert(0, self.current_custom_color or "")
        self.pick_color_button = ctk.CTkButton(appearance_tab, text=self._("appearance_pick_color_button"), width=30, command=self._pick_custom_color); self.pick_color_button.grid(row=1, column=2, padx=(0, 5), pady=(5, 15), sticky="w")
        self.apply_color_button = ctk.CTkButton(appearance_tab, text=self._("appearance_apply_color_button"), command=self._apply_custom_color); self.apply_color_button.grid(row=1, column=3, padx=(0, 15), pady=(5, 15), sticky="e")
        self._language_widgets['appearance_apply_color_button'] = self.apply_color_button

        # --- Bottom Frame (Button & Status) ---
        bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent"); bottom_frame.grid(row=2, column=0, sticky="ew", pady=(15, 5)); bottom_frame.grid_columnconfigure(0, weight=1)
        self.generate_button = ctk.CTkButton( bottom_frame, text=self._("generate_button"), command=self.generate_audio_manual, height=40, font=ctk.CTkFont(size=16, weight="bold"), corner_radius=10 ); self.generate_button.grid(row=0, column=0, pady=(0, 15), sticky="")
        self._language_widgets['generate_button'] = self.generate_button
        self.status_bar_frame = ctk.CTkFrame(self.main_frame, height=25, corner_radius=0); self.status_bar_frame.grid(row=3, column=0, sticky="ew"); self.status_bar_frame.grid_columnconfigure(0, weight=1); self.status_bar_frame.grid_columnconfigure(1, weight=0); self.status_bar_frame.grid_columnconfigure(2, weight=0) # Column for lang btn
        self.status_label = ctk.CTkLabel(self.status_bar_frame, text=self._("status_ready"), anchor="w", font=ctk.CTkFont(size=12)); self.status_label.grid(row=0, column=0, sticky="ew", padx=(10, 5))
        self.progress_bar = ctk.CTkProgressBar(self.status_bar_frame, height=10, width=100, corner_radius=5); self.progress_bar.set(0); self.progress_bar.grid_remove()
        self.language_button = ctk.CTkButton(self.status_bar_frame, text=self._("lang_button_text"), width=50, height=20, font=ctk.CTkFont(size=10), command=self.toggle_language); self.language_button.grid(row=0, column=2, padx=(5, 10), sticky="e")

        # --- Float Window Vars ---
        self.float_window = None; self.ok_window = None; self.generating_window = None
        self.generating_animation_job = None; self.generating_window_label = None
        self.last_mouse_pos = (0, 0); self._text_for_float_trigger = None
        self._float_window_close_job = None; self._ok_window_close_job = None

        # --- Tray Icon Setup ---
        self.tray_icon_instance = None # Store pystray icon instance
        self._tray_setup_complete = False # Flag to prevent multiple setups

        # --- Initial Actions ---
        self._apply_custom_color(save=False); self.refresh_voices_ui()
        if self.select_to_audio_var.get(): self.start_clipboard_monitor()
        # Delay tray setup slightly to ensure translations are ready
        self.root.after(100, self.setup_tray_icon) # <<<<<<< 修改: 延迟初始化托盘图标 >>>>>>>>>
        self.root.bind("<Unmap>", self.handle_minimize) # <<<<<<< 添加: 绑定最小化事件 >>>>>>>>>

    # --------------------------------------------------------------------------
    # Tray Icon Methods <<<<<<< 添加: 新增/修改托盘相关方法 >>>>>>>>>
    # --------------------------------------------------------------------------
    def setup_tray_icon(self):
        """Sets up the system tray icon and its menu. Ensures it runs only once."""
        global tray_icon, tray_thread, icon_image # Use global icon_image
        if self._tray_setup_complete or pystray is None or Image is None: # Check dependencies and flag
            if pystray is None or Image is None:
                print("警告: pystray 或 Pillow 未加载，无法创建托盘图标。")
            return

        icon_path = os.path.join(os.path.dirname(__file__), ICON_PATH)
        try:
            # Load image only once
            if icon_image is None:
                icon_image = Image.open(icon_path)
        except FileNotFoundError:
            print(f"错误: 托盘图标文件未找到: {icon_path}")
            messagebox.showerror("错误", f"托盘图标文件未找到: {icon_path}")
            return
        except Exception as e:
            print(f"加载托盘图标时出错: {e}")
            messagebox.showerror("错误", f"加载托盘图标时出错: {e}")
            return

        # Define menu items using lambda to capture current state
        menu = (
            # Pass translated strings directly for menu item text
            pystray.MenuItem(self._("tray_show_hide"), self.toggle_window_visibility),
            pystray.MenuItem(self._("tray_exit"), self.quit_application)
        )

        # Use the loaded global icon_image
        # pystray uses the first menu item as the default left-click action.
        self.tray_icon_instance = pystray.Icon(
            "AnkiTTS",
            icon_image,
            self._("window_title"),
            menu=menu
        )
        # Explicitly setting default_action might be redundant but ensures clarity.
        # self.tray_icon_instance.default_action = self.toggle_window_visibility # Already handled by menu order

        tray_icon = self.tray_icon_instance # Assign to global for thread access

        # Run the icon in a separate thread only if not already running
        def run_icon():
            if tray_icon:
                try:
                    print("启动托盘图标...")
                    tray_icon.run()
                    print("托盘图标已停止。")
                except Exception as e:
                    print(f"运行托盘图标时出错: {e}")
            else:
                print("错误：尝试运行未初始化的托盘图标。")

        if tray_thread is None or not tray_thread.is_alive():
            tray_thread = threading.Thread(target=run_icon, daemon=True)
            tray_thread.start()
            self._tray_setup_complete = True # Mark setup as done
        else:
            print("托盘图标线程已在运行。")


    def toggle_window_visibility(self, icon=None, item=None): # Add icon/item args for pystray
        """Shows or hides the main window."""
        if self.root.winfo_viewable():
            self.hide_window()
        else:
            self.show_window()

    def show_window(self):
        """Shows the main window."""
        if not self.root.winfo_exists(): return
        try:
            # Use schedule tasks to ensure they run on the main thread
            self.root.after(0, self.root.deiconify)
            self.root.after(10, self.root.lift)
            self.root.after(20, self.root.focus_force)
            print("窗口已显示")
        except tk.TclError as e:
            print(f"显示窗口时出错: {e}")

    def hide_window(self):
        """Hides the main window."""
        if not self.root.winfo_exists(): return
        try:
            self.root.withdraw()
            print("窗口已隐藏到托盘")
        except tk.TclError as e:
            print(f"隐藏窗口时出错: {e}")

    def handle_minimize(self, event=None):
        """Handles the window minimize event."""
        # This event might be triggered when withdrawing, so check the actual state
        # Need a slight delay to let the state update after clicking minimize
        def check_state_and_hide():
            if not self.root.winfo_exists(): return
            try:
                # Check the setting AND if the window state is 'iconic' (minimized)
                if self.minimize_to_tray_var.get() and self.root.state() == 'iconic':
                    print("检测到最小化事件 (iconic state)，隐藏到托盘...")
                    self.hide_window()
                # elif not self.root.winfo_viewable(): # Optional: Handle if already hidden?
                #    print("窗口已隐藏。")
            except tk.TclError as e:
                 print(f"检查窗口状态时出错: {e}")

        # Schedule the check slightly after the event
        self.root.after(50, check_state_and_hide)


    def quit_application(self, icon=None, item=None): # Add icon/item args for pystray
        """Properly exits the application."""
        print("正在退出应用程序 (来自托盘菜单)...")
        global tray_icon, tray_thread # Ensure globals are accessible
        if self.tray_icon_instance:
            try:
                self.tray_icon_instance.stop()
                print("托盘图标已请求停止。")
            except Exception as e:
                print(f"停止托盘图标时出错: {e}")
        tray_icon = None # Clear global reference
        # Wait briefly for the tray thread to potentially exit
        if tray_thread and tray_thread.is_alive():
             print("等待托盘线程退出...")
             tray_thread.join(timeout=1.0) # Wait max 1 second
             if tray_thread.is_alive():
                 print("警告：托盘线程未在超时内退出。")
        tray_thread = None

        # Call the original closing logic AFTER stopping the tray icon
        # Ensure it runs on the main thread if called from tray thread
        if threading.current_thread() is not threading.main_thread():
            if self.root.winfo_exists():
                self.root.after(0, self.on_closing, True) # Pass force_quit=True
            else:
                 # If root doesn't exist, try direct cleanup (less ideal)
                 self._perform_cleanup()
        else:
             self.on_closing(force_quit=True)

    # --------------------------------------------------------------------------
    # Language Handling
    # --------------------------------------------------------------------------
    def _(self, key, *args):
        """Helper function to get translation."""
        # Use loaded TRANSLATIONS global, fallback within the dict or to key
        lang_map = TRANSLATIONS.get(self.current_language, TRANSLATIONS.get('zh', {}))
        text = lang_map.get(key, key) # Return key if not found in current or fallback lang
        try:
            return text.format(*args) if args else text
        except (IndexError, KeyError, TypeError):
            # print(f"Warning: Formatting error for key '{key}' with args {args}")
            return text # Return raw string on format error

    def toggle_language(self):
        """Switches the UI language between Chinese and English."""
        self.current_language = 'en' if self.current_language == 'zh' else 'zh'
        print(f"Switching language to: {self.current_language}")
        self._update_ui_language()
        self.save_settings() # Save the new language preference
        lang_name_key = f"lang_name_{self.current_language}"
        self.update_status("status_lang_changed", duration=3, args_tuple=(self._(lang_name_key),)) # Pass lang name as arg


    def _update_ui_language(self):
        """Updates the text of all registered UI widgets."""
        self.root.title(self._("window_title")) # Update window title

        # Update standard widgets stored by key
        for key, widget in self._language_widgets.items():
            if key.startswith("tab_"): continue # Handle tabs separately
            if widget and widget.winfo_exists():
                try:
                    if isinstance(widget, (ctk.CTkLabel, ctk.CTkButton, ctk.CTkSwitch)):
                        # Check if it's the segmented button key before configuring text
                        if key not in ['appearance_mode_light', 'appearance_mode_dark']:
                             widget.configure(text=self._(key))
                    elif isinstance(widget, ctk.CTkEntry): # Update placeholder
                        widget.configure(placeholder_text=self._(key))
                    elif isinstance(widget, ctk.CTkScrollableFrame): # Update label_text
                         widget.configure(label_text=self._(key))
                except Exception as e: print(f"Warning: Failed to update widget '{key}': {e}")

        # Update Tab names - Requires knowing original vs new name
        tab_map = {"tab_voices": self._("tab_voices"), "tab_settings": self._("tab_settings"), "tab_appearance": self._("tab_appearance")}
        # Store current tab before renaming
        current_tab_text = self.tab_view.get()
        new_selected_tab_name = None

        for tab_key, new_name in tab_map.items():
            # Find the corresponding old name (from the other language)
            old_lang = 'en' if self.current_language == 'zh' else 'zh'
            old_name = TRANSLATIONS.get(old_lang, {}).get(tab_key, new_name) # Fallback to new name if old fails
            try:
                # Check if a tab with the 'old_name' exists before renaming
                if old_name in self.tab_view._name_list:
                     self.tab_view.rename(old_name, new_name)
                     # If this was the selected tab, store its new name
                     if current_tab_text == old_name:
                         new_selected_tab_name = new_name
                elif new_name in self.tab_view._name_list:
                     # If old name doesn't exist but new name does (already updated?), ensure selection
                     if current_tab_text == new_name:
                         new_selected_tab_name = new_name

            except Exception as e: print(f"Warning: Failed to rename tab '{old_name}' to '{new_name}': {e}")

        # Reselect the tab using its (potentially) new name
        if new_selected_tab_name:
            try: self.tab_view.set(new_selected_tab_name)
            except Exception as e: print(f"Warning: Failed to set tab to '{new_selected_tab_name}': {e}")


        # Update Segmented Button values
        try:
            seg_button = self._language_widgets.get('appearance_mode_light') # Get the button itself
            if seg_button and seg_button.winfo_exists():
                new_values = [self._("appearance_mode_light"), self._("appearance_mode_dark")]
                current_mode = ctk.get_appearance_mode()
                current_selection_text = self._("appearance_mode_light") if current_mode == 'light' else self._("appearance_mode_dark")
                seg_button.configure(values=new_values)
                seg_button.set(current_selection_text) # Re-set selection with new text
        except Exception as e: print(f"Warning: Failed to update segmented button: {e}")

        # Update status bar text (if it's showing the default message)
        if hasattr(self, 'status_label') and self.status_label.winfo_exists():
             current_status = self.status_label.cget("text")
             # Check against both language defaults
             if current_status == TRANSLATIONS.get('zh',{}).get('status_ready','?') or \
                current_status == TRANSLATIONS.get('en',{}).get('status_ready','?'):
                 self.status_label.configure(text=self._("status_ready"))

        # Update voice list status messages if applicable (e.g., "No matching voices")
        self._populate_inline_voice_list('left')
        self._populate_inline_voice_list('right')


    # --------------------------------------------------------------------------
    # UI 更新与状态管理方法 (使用翻译 key)
    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    # UI 更新与状态管理方法 (使用翻译 key, 修复 SyntaxError)
    # --------------------------------------------------------------------------
    def update_status(self, message_key_or_literal, duration=0, error=False, permanent=False, show_progress=False, args_tuple=None):
        """Updates status bar. Accepts a translation key or literal string."""
        global status_update_job
        def _update():
            global status_update_job
            # <<<<<<< CORRECTED SyntaxError >>>>>>>>>
            if status_update_job:
                try:
                    self.status_label.after_cancel(status_update_job)
                except Exception as e:
                    # print(f"DEBUG: Error cancelling status job: {e}") # Optional debug
                    pass
                status_update_job = None # Reset job ID

            args = args_tuple or ()
            is_key = isinstance(message_key_or_literal, str) and message_key_or_literal in TRANSLATIONS.get(self.current_language, {})
            message = self._(message_key_or_literal, *args) if is_key else message_key_or_literal.format(*args) # Use translation if key, else format literal

            status_text = message
            try: label_fg = ctk.ThemeManager.theme["CTkLabel"]["text_color"]; text_color = label_fg[ctk.get_appearance_mode()=='dark'] if isinstance(label_fg, (list, tuple)) else label_fg
            except: text_color = ("#000000", "#FFFFFF")

            check_mark = "✅"
            cross_mark = "❌"
            hourglass = "⏳"

            if error: status_text = f"{cross_mark} {message}"; text_color = ("#D81B60", "#FF8A80")
            elif (is_key and ("success" in message_key_or_literal or "copied" in message_key_or_literal or "updated" in message_key_or_literal or "saved" in message_key_or_literal or "ready" in message_key_or_literal or "enabled" in message_key_or_literal or "changed" in message_key_or_literal)) \
                 or check_mark in status_text:
                if not status_text.startswith(check_mark): status_text = f"{check_mark} {message}"
                text_color = ("#00796B", "#80CBC4")
            elif (is_key and ("generating" in message_key_or_literal or "getting" in message_key_or_literal)) \
                  or hourglass in status_text:
                 if not status_text.startswith(hourglass): status_text = f"{hourglass} {message}"

            # Ensure status label exists before configuring
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.configure(text=status_text, text_color=text_color)

            # Ensure progress bar exists before configuring/gridding
            if hasattr(self, 'progress_bar'):
                if show_progress:
                    self.progress_bar.grid(row=0, column=1, padx=(0, 10), sticky="e")
                    try: theme_color = ctk.ThemeManager.theme["CTkProgressBar"]["progress_color"]; default_color = theme_color[ctk.get_appearance_mode()=='dark'] if isinstance(theme_color, (list, tuple)) else theme_color; p_color = self.current_custom_color or default_color
                    except: p_color = self.current_custom_color or "#1F6AA5"
                    self.progress_bar.configure(mode="indeterminate", progress_color=p_color)
                    if hasattr(self.progress_bar, 'start'): self.progress_bar.start()
                else:
                    if hasattr(self.progress_bar, 'stop'): self.progress_bar.stop()
                    self.progress_bar.grid_remove()

            if not permanent and duration > 0:
                 # Ensure status label exists for scheduling the reset
                 if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                     status_update_job = self.status_label.after(duration * 1000, lambda: self.update_status("status_ready")) # Reset to ready key

        if threading.current_thread() is not threading.main_thread():
            if hasattr(self, 'root') and self.root.winfo_exists(): self.root.after(0, _update)
        else: _update()


    def update_rate_label(self, value): val = int(value); self.rate_value_label.configure(text=f"{val:+}%")
    def update_volume_label(self, value): val = int(value); self.volume_value_label.configure(text=f"{val:+}%")
    def refresh_voices_ui(self):
        self.update_status("status_getting_voices", permanent=True)
        self.refresh_button.configure(state="disabled")
        for frame in [self.inline_voice_list_frame_left, self.inline_voice_list_frame_right]:
            for widget in frame.winfo_children(): widget.destroy()
            ctk.CTkLabel(frame, text=self._("status_getting_voices"), text_color="gray").pack(pady=20)
        refresh_voices_list()

    def update_voice_ui(self, hierarchical_voice_data):
        # print(self._("debug_voice_ui_updated").format(self.current_full_voice_name)) # Updated print
        self.hierarchical_voice_data = hierarchical_voice_data; self.refresh_button.configure(state="normal")
        self.voice_display_to_full_map.clear()
        if not hierarchical_voice_data:
            print(self._("debug_voice_ui_no_data"))
            for frame in [self.inline_voice_list_frame_left, self.inline_voice_list_frame_right]:
                for widget in frame.winfo_children(): widget.destroy()
                ctk.CTkLabel(frame, text=self._("debug_voice_load_failed_ui"), text_color="red").pack(pady=20)
            self.update_status("status_generate_error", error=True); return
        pattern = re.compile(r", (.*Neural)\)$")
        for lang_data in hierarchical_voice_data.values():
            for voices in lang_data.values():
                for name in voices:
                    match = pattern.search(name); display = match.group(1) if match else name
                    orig_dn = display; count = 1
                    while display in self.voice_display_to_full_map: display = f"{orig_dn}_{count}"; count += 1
                    self.voice_display_to_full_map[display] = name
        settings = self.load_settings(); selected = settings.get("selected_voice", DEFAULT_VOICE)
        if selected in self.voice_display_to_full_map.values(): self.current_full_voice_name = selected
        elif DEFAULT_VOICE in self.voice_display_to_full_map.values(): self.current_full_voice_name = DEFAULT_VOICE
        else: available = list(self.voice_display_to_full_map.values()); self.current_full_voice_name = available[0] if available else None
        self._populate_inline_voice_list('left'); self._populate_inline_voice_list('right')
        print(self._("debug_voice_ui_updated").format(self.current_full_voice_name)) # Print after update
        self.update_status("status_voices_updated", duration=3)

    # --------------------------------------------------------------------------
    # 内联声音选择器方法 (使用翻译)
    # --------------------------------------------------------------------------
    def _populate_inline_voice_list(self, side):
        frame = self.inline_voice_list_frame_left if side == 'left' else self.inline_voice_list_frame_right
        filter_entry = self.language_filter_entry_left if side == 'left' else self.language_filter_entry_right
        if not frame: return
        filter_term = filter_entry.get() if hasattr(self, f'language_filter_entry_{side}') else ""
        for widget in frame.winfo_children(): widget.destroy()
        row_count = 0
        filter_codes = [c.strip().lower() for c in re.split(r'[,\s]+', filter_term) if c.strip()]
        if not self.voice_display_to_full_map:
             # print(self._("debug_voice_map_empty"))
             ctk.CTkLabel(frame, text=self._("debug_no_matching_voices"), text_color="gray").grid(row=0, column=0, pady=20); return
        sorted_voices = sorted(self.voice_display_to_full_map.items()); found_match = False
        for display_name, full_name in sorted_voices:
            apply_filter = len(filter_codes) > 0; match_filter = False
            if apply_filter:
                match = re.search(r'\(([a-z]{2,3})-', full_name); code = match.group(1).lower() if match else ""
                if code in filter_codes: match_filter = True
            if apply_filter and not match_filter: continue
            found_match = True; is_selected = (full_name == self.current_full_voice_name)
            try: default_fg = ctk.ThemeManager.theme["CTkButton"]["fg_color"]; default_fg_mode = default_fg[ctk.get_appearance_mode()=='dark'] if isinstance(default_fg,(list,tuple)) else default_fg
            except: default_fg_mode = "#1F6AA5"
            btn_fg = self.current_custom_color or default_fg_mode; btn_hover = self._calculate_hover_color(btn_fg)
            # Determine normal text color based on theme
            try:
                default_txt_colors = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
                if isinstance(default_txt_colors, (list, tuple)):
                    # Use light text for dark mode, dark text for light mode
                    txt_normal = default_txt_colors[1] if ctk.get_appearance_mode().lower() == 'dark' else default_txt_colors[0]
                else:
                    txt_normal = default_txt_colors # Single color specified
            except:
                # Fallback if theme fetching fails
                txt_normal = "#FFFFFF" if ctk.get_appearance_mode().lower() == 'dark' else "#000000"

            txt_selected = self._get_contrasting_text_color(btn_fg)
            btn = ctk.CTkButton( frame, text=display_name, anchor="w", fg_color=btn_fg if is_selected else "transparent", hover_color=btn_hover, text_color=txt_selected if is_selected else txt_normal, command=lambda fn=full_name: self._select_voice_inline(fn) )
            btn.grid(row=row_count, column=0, padx=5, pady=2, sticky="ew"); row_count += 1
        if not found_match: ctk.CTkLabel(frame, text=self._("debug_no_matching_voices"), text_color="gray").grid(row=0, column=0, pady=20)

    def _filter_voices_inline(self, side): self._populate_inline_voice_list(side); self.save_settings()
    def _select_voice_inline(self, full_name):
        if self.current_full_voice_name != full_name:
            self.current_full_voice_name = full_name; print(self._("debug_voice_selected", full_name))
            self._populate_inline_voice_list('left'); self._populate_inline_voice_list('right'); self.save_settings()

    # --------------------------------------------------------------------------
    # 主题与颜色切换方法 (使用翻译)
    # --------------------------------------------------------------------------
    def _change_appearance_mode(self, selected_value):
        mode = 'light' if selected_value == self._("appearance_mode_light") else 'dark'
        print(f"Switching appearance mode to: {mode}"); ctk.set_appearance_mode(mode); self._apply_custom_color(save=True)
    def _pick_custom_color(self):
        initial = self.custom_color_entry.get() or self.current_custom_color or DEFAULT_CUSTOM_COLOR
        chosen = colorchooser.askcolor(title=self._("appearance_color_label"), initialcolor=initial) # Translated title
        if chosen and chosen[1]: hex_color = chosen[1]; self.custom_color_entry.delete(0, tk.END); self.custom_color_entry.insert(0, hex_color); self._apply_custom_color()
    def _apply_custom_color(self, save=True):
        new_color = self.custom_color_entry.get().strip()
        if not re.match(r"^#[0-9a-fA-F]{6}$", new_color):
            if new_color: messagebox.showerror(self._("error_invalid_color_title"), self._("error_invalid_color_message", new_color))
            self.current_custom_color = DEFAULT_CUSTOM_COLOR; self.custom_color_entry.delete(0, tk.END); self.custom_color_entry.insert(0, self.current_custom_color)
            new_color = self.current_custom_color; save = False
        else: self.current_custom_color = new_color
        print(self._("debug_apply_color", self.current_custom_color)); hover = self._calculate_hover_color(self.current_custom_color)
        # ... (rest of apply color logic remains same, widget references are stable) ...
        buttons=[getattr(self,n,None) for n in ['generate_button','refresh_button','apply_color_button','pick_color_button']]
        for b in buttons:
             if b and hasattr(b, 'configure'): b.configure(fg_color=self.current_custom_color, hover_color=hover)
        # Add minimize_to_tray_switch to the list of switches to theme
        switches=[getattr(self,n,None) for n in ['copy_to_clipboard_switch','play_audio_switch','select_to_audio_switch','select_trigger_switch', 'minimize_to_tray_switch']]
        for s in switches:
             if s and hasattr(s, 'configure'): s.configure(progress_color=self.current_custom_color)
        sliders=[getattr(self,n,None) for n in ['rate_slider','volume_slider']]
        for s in sliders:
             if s: s.configure(button_color=self.current_custom_color, progress_color=self.current_custom_color, button_hover_color=hover)
        if hasattr(self, 'progress_bar'):
             try: theme_color = ctk.ThemeManager.theme["CTkProgressBar"]["progress_color"]; default_color = theme_color[ctk.get_appearance_mode()=='dark'] if isinstance(theme_color, (list, tuple)) else theme_color; color = self.current_custom_color or default_color
             except: color = self.current_custom_color or "#1F6AA5"
             self.progress_bar.configure(progress_color=color)
        if hasattr(self, 'tab_view'): self.tab_view.configure(segmented_button_selected_color=self.current_custom_color, segmented_button_selected_hover_color=hover)
        if hasattr(self, 'appearance_mode_segmented_button'): self.appearance_mode_segmented_button.configure(selected_color=self.current_custom_color, selected_hover_color=hover)
        self._populate_inline_voice_list('left'); self._populate_inline_voice_list('right')
        if save: self.save_settings()

    def _calculate_hover_color(self, hex_color): # No change
        try: h=hex_color.lstrip('#'); r,g,b=tuple(int(h[i:i+2],16) for i in (0,2,4)); hr,hg,hb=max(0,r-20),max(0,g-20),max(0,b-20); return f"#{hr:02x}{hg:02x}{hb:02x}"
        except:
            try: d=ctk.ThemeManager.theme["CTkButton"]["hover_color"]; return d[ctk.get_appearance_mode()=='dark'] if isinstance(d,(list,tuple)) else d
            except: return "#A0A0A0"
    def _get_contrasting_text_color(self, bg_hex_color): # No change
        try: h=bg_hex_color.lstrip('#'); r,g,b=tuple(int(h[i:i+2],16) for i in (0,2,4)); br=(r*299+g*587+b*114)/1000; return "#000000" if br>128 else "#FFFFFF"
        except:
            try: d=ctk.ThemeManager.theme["CTkLabel"]["text_color"]; return d[ctk.get_appearance_mode()=='dark'] if isinstance(d,(list,tuple)) else d
            except: return "#000000"

    # --------------------------------------------------------------------------
    # 设置加载与保存 (添加 minimize_to_tray)
    # --------------------------------------------------------------------------
    def load_settings(self):
        # Added minimize_to_tray default
        defaults = {"language":"zh", "copy_path_enabled": True, "autoplay_enabled": False, "monitor_enabled": False, "select_trigger_enabled": False, "minimize_to_tray": False, "max_audio_files": DEFAULT_MAX_AUDIO_FILES, "selected_voice": DEFAULT_VOICE, "rate": 0, "volume": 0, "appearance_mode": DEFAULT_APPEARANCE_MODE, "language_filter_left": "zh", "language_filter_right": "en", "custom_theme_color": DEFAULT_CUSTOM_COLOR}
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f: settings = json.load(f)
                merged = defaults.copy(); merged.update(settings)
                loaded_color = merged.get("custom_theme_color", DEFAULT_CUSTOM_COLOR)
                # Use default language "zh" for initial validation print if app._ not ready
                if not re.match(r"^#[0-9a-fA-F]{6}$", loaded_color): print(TRANSLATIONS.get('zh',{}).get('debug_invalid_color_loaded',"Warn: Invalid color").format(loaded_color)); merged["custom_theme_color"] = DEFAULT_CUSTOM_COLOR
                if merged.get("language") not in ["zh", "en"]: print(f"Warn: Invalid lang '{merged.get('language')}', using zh."); merged["language"] = "zh"
                return merged
        except Exception as e: print(f"Load settings failed: {e}") # Use basic print here
        return defaults

    def save_settings(self):
        try: max_f = int(self.max_files_entry.get()); max_f = max_f if 1 <= max_f <= 50 else DEFAULT_MAX_AUDIO_FILES
        except ValueError: max_f = DEFAULT_MAX_AUDIO_FILES
        filter_l = getattr(self, 'language_filter_entry_left', None); filter_r = getattr(self, 'language_filter_entry_right', None)
        settings = {
            "language": self.current_language,
            "selected_voice": self.current_full_voice_name or DEFAULT_VOICE,
            "copy_path_enabled": self.copy_to_clipboard_var.get(),
            "autoplay_enabled": self.play_audio_var.get(),
            "monitor_enabled": self.select_to_audio_var.get(),
            "select_trigger_enabled": self.select_trigger_var.get(),
            "minimize_to_tray": self.minimize_to_tray_var.get(), # Save tray setting
            "max_audio_files": max_f,
            "rate": self.rate_slider_var.get(),
            "volume": self.volume_slider_var.get(),
            "appearance_mode": ctk.get_appearance_mode().lower(),
            "language_filter_left": filter_l.get() if filter_l else "zh",
            "language_filter_right": filter_r.get() if filter_r else "en",
            "custom_theme_color": self.current_custom_color or DEFAULT_CUSTOM_COLOR
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f: json.dump(settings, f, ensure_ascii=False, indent=4)
            # print(self._("debug_settings_saved")) # Optional: only show on explicit save action?
        except Exception as e: print(self._("debug_settings_save_failed", e)); self.update_status("status_settings_save_failed", error=True)

    # --------------------------------------------------------------------------
    # 音频生成与处理方法 (使用翻译)
    # --------------------------------------------------------------------------
    def generate_audio_manual(self):
        text = self.text_input.get("1.0", "end").strip()
        if not text: self.update_status("status_empty_text_error", error=True, duration=5); return
        voice = self.current_full_voice_name
        if not voice: self.update_status("status_no_voice_error", error=True, duration=5); return
        rate=f"{self.rate_slider_var.get():+}%"; volume=f"{self.volume_slider_var.get():+}%"; pitch="+0Hz"
        def on_complete(path, error=None):
            if self.root.winfo_exists(): self.generate_button.configure(state="normal")
            if path:
                base = os.path.basename(path); self.update_status(f"{self._('status_success')}: {base}", duration=10); print(self._("debug_audio_complete", path))
                play = self.play_audio_var.get(); print(self._("debug_autoplay_manual", play))
                if play: self.play_audio_pygame(path)
                if self.copy_to_clipboard_var.get(): copy_file_to_clipboard(path)
            else: err=f"{self._('status_generate_error')}: {error or '??'}"; print(err); self.update_status(err, error=True)
            manage_audio_files()
        self.generate_button.configure(state="disabled"); name = self._get_display_voice_name(voice)
        self.update_status(f"{self._('status_generating')} ({name})...", permanent=True, show_progress=True)
        generate_audio(text, voice, rate, volume, pitch, on_complete)

    def play_audio_pygame(self, path):
        print(self._("debug_pygame_play_call", path))
        if not pygame.mixer.get_init(): print("ERROR: Pygame mixer not initialized."); self.update_status("status_mixer_init_error", error=True); return
        if not os.path.exists(path): print(f"ERROR: Audio file not found: {path}"); self.update_status("status_file_not_found", error=True); return
        try:
            if pygame.mixer.music.get_busy(): print(self._("debug_pygame_stop_current")); pygame.mixer.music.stop(); pygame.mixer.music.unload(); time.sleep(0.05)
            print(self._("debug_pygame_load_play", path)); pygame.mixer.music.load(path); pygame.mixer.music.play(); print(self._("debug_pygame_play_start"))
        except pygame.error as e: print(self._("debug_pygame_play_error", e)); self.update_status(f"{self._('status_play_error')}: {e}", error=True)
        except Exception as e: print(self._("debug_play_unknown_error", e)); self.update_status(f"{self._('status_play_error')}: {e}", error=True)

    def _get_display_voice_name(self, name): # No change
        if not name: return "Unknown"
        for dn, fn in self.voice_display_to_full_map.items():
            if fn == name: return dn
        match = re.search(r", (.*Neural)\)$", name); return match.group(1) if match else name

    # --------------------------------------------------------------------------
    # 浮窗相关方法 (SyntaxError 修复 + 打印)
    # --------------------------------------------------------------------------
    def show_float_window(self, text):
        """在鼠标位置显示蓝色“音”字浮窗"""
        # 先销毁可能存在的旧窗口
        if self.float_window:
            try:
                self.float_window.destroy()
            except Exception: # Catch any error during destroy
                pass
            self.float_window = None # Ensure it's reset

        self.destroy_generating_window()
        self.destroy_ok_window()

        self._text_for_float_trigger = text # Store text for later use

        # 创建新窗口
        self.float_window = tk.Toplevel(self.root)
        self.float_window.overrideredirect(True)
        x, y = self.last_mouse_pos
        self.float_window.geometry(f"50x50+{x + 10}+{y + 10}")
        self.float_window.attributes("-topmost", True)

        # 创建按钮
        btn = ctk.CTkButton(
            self.float_window, text="音", width=50, height=50, corner_radius=25,
            font=ctk.CTkFont(size=20, weight="bold"), fg_color="#1E90FF",
            hover_color="#1C86EE", text_color="white",
            command=self.trigger_generate_from_float
        )
        btn.pack(fill="both", expand=True)

        # 取消之前的自动关闭任务
        if hasattr(self, '_float_window_close_job') and self._float_window_close_job:
            try:
                self.root.after_cancel(self._float_window_close_job)
            except Exception:
                pass
            self._float_window_close_job = None

        # 定义自动关闭函数 (内嵌)
        def auto_close():
            # <<<<<<< CORRECTED SyntaxError >>>>>>>>>
            if self.float_window:
                try:
                    self.float_window.destroy()
                except tk.TclError: # Specific tkinter error
                    pass
                except Exception as e: # Catch other potential errors during destroy
                    # print(f"DEBUG: Error destroying float window in auto_close: {e}")
                    pass
            # Ensure these are reset even if destroy failed
            self.float_window = None
            self._float_window_close_job = None

        # 启动新的自动关闭任务
        self._float_window_close_job = self.float_window.after(FLOAT_WINDOW_TIMEOUT * 1000, auto_close)

    def show_generating_window(self, position):
        self.destroy_float_window(); self.destroy_ok_window(); self.destroy_generating_window()
        self.generating_window = tk.Toplevel(self.root); self.generating_window.overrideredirect(True)
        x, y = position; self.generating_window.geometry(f"50x50+{x+10}+{y+10}"); self.generating_window.attributes("-topmost", True)
        self.generating_window_label = ctk.CTkButton( self.generating_window, text="/", width=50, height=50, corner_radius=25, font=ctk.CTkFont(size=20, weight="bold"), fg_color="#4CAF50", hover_color="#45a049", text_color="white", state="disabled" )
        self.generating_window_label.pack(fill="both", expand=True); self._animate_green_dot()
    def _animate_green_dot(self, char_index=0):
        if self.generating_window and self.generating_window.winfo_exists():
            chars=["/","-","\\","|"]; char=chars[char_index % len(chars)]
            if self.generating_window_label: self.generating_window_label.configure(text=char)
            self.generating_animation_job = self.root.after(150, lambda: self._animate_green_dot(char_index + 1))
        else: self.generating_animation_job = None

    # Corrected Syntax
    def destroy_generating_window(self):
        if self.generating_animation_job:
            try: self.root.after_cancel(self.generating_animation_job)
            except: pass
            self.generating_animation_job = None
        if self.generating_window:
            try: self.generating_window.destroy()
            except: pass
            self.generating_window = None; self.generating_window_label = None
    # Corrected Syntax
    def destroy_float_window(self):
        if hasattr(self, '_float_window_close_job') and self._float_window_close_job:
            try: self.root.after_cancel(self._float_window_close_job)
            except: pass
            self._float_window_close_job = None
        if self.float_window:
            try: self.float_window.destroy()
            except: pass
            self.float_window = None
    # Corrected Syntax
    def destroy_ok_window(self):
        if hasattr(self, '_ok_window_close_job') and self._ok_window_close_job:
            try: self.root.after_cancel(self._ok_window_close_job)
            except: pass
            self._ok_window_close_job = None
        if self.ok_window:
            try: self.ok_window.destroy()
            except: pass
            self.ok_window = None
    # Corrected Syntax
    def show_ok_window(self, position=None):
        self.destroy_ok_window(); self.destroy_generating_window()
        self.ok_window = tk.Toplevel(self.root); self.ok_window.overrideredirect(True)
        pos = position or self.last_mouse_pos; x, y = pos
        self.ok_window.geometry(f"50x50+{x+10}+{y+10}"); self.ok_window.attributes("-topmost", True)
        btn = ctk.CTkButton( self.ok_window, text="OK", width=50, height=50, corner_radius=25, font=ctk.CTkFont(size=20, weight="bold"), fg_color="#DC143C", hover_color="#B22222", text_color="white", command=self.destroy_ok_window )
        btn.pack(fill="both", expand=True)
        if hasattr(self, '_ok_window_close_job') and self._ok_window_close_job:
            try: self.root.after_cancel(self._ok_window_close_job)
            except: pass
            self._ok_window_close_job = None
        def auto_close():
            if self.ok_window: self.destroy_ok_window()
            self._ok_window_close_job = None
        self._ok_window_close_job = self.ok_window.after(MOUSE_TIP_TIMEOUT * 1000, auto_close)

    def trigger_generate_from_float(self):
        text = getattr(self, '_text_for_float_trigger', None)
        if not text: print(self._("debug_no_float_text")); self.destroy_float_window(); return
        print(self._("debug_float_trigger_text").format(text[:50]))
        voice = self.current_full_voice_name
        if not voice: self.update_status("status_no_voice_error", error=True, duration=5); self.destroy_float_window(); return
        rate=f"{self.rate_slider_var.get():+}%"; volume=f"{self.volume_slider_var.get():+}%"; pitch="+0Hz"
        pos = self.last_mouse_pos; self.destroy_float_window(); self.show_generating_window(pos)
        def on_complete(path, error=None):
            self.destroy_generating_window()
            copy=self.copy_to_clipboard_var.get(); play=self.play_audio_var.get()
            if path:
                print(self._("debug_audio_complete", path)); print(self._("debug_autoplay_float", play)); print(self._("debug_autocopy_float", copy))
                if play: self.play_audio_pygame(path)
                if copy: copy_file_to_clipboard(path); self.show_ok_window(pos)
            else: err = f"{self._('status_generate_error')}: {error or '??'}"; print(err); self.update_status(err, error=True)
            manage_audio_files()
        generate_audio(text, voice, rate, volume, pitch, on_complete)

    # --------------------------------------------------------------------------
    # 剪贴板与鼠标监控方法 (使用翻译)
    # --------------------------------------------------------------------------
    def toggle_select_to_audio(self):
        global clipboard_monitor_active
        if self.select_to_audio_var.get():
            if not clipboard_monitor_active: self.start_clipboard_monitor()
        else: self.stop_clipboard_monitor()
        self.save_settings()

    def start_clipboard_monitor(self):
        global clipboard_monitor_active, clipboard_polling_thread, previous_clipboard_poll_content
        global mouse_listener_thread, mouse_listener, is_dragging, drag_start_pos, drag_start_time
        if clipboard_monitor_active: print("Monitor already running"); return
        clipboard_monitor_active = True
        print(self._("debug_monitor_start"))
        self.update_status("status_monitor_enabled", duration=5)
        # Clipboard Polling Thread
        try: previous_clipboard_poll_content = pyperclip.paste()
        except Exception as e: print(self._("debug_initial_paste_error", e)); previous_clipboard_poll_content = ""
        # print(self._("debug_initial_paste_set", previous_clipboard_poll_content[:50]))
        def poll_clipboard():
            global clipboard_monitor_active, previous_clipboard_poll_content
            # print(self._("debug_poll_thread_start")) # Can be verbose
            while clipboard_monitor_active:
                current_text = None
                try:
                    current_text = pyperclip.paste()
                    if current_text is not None and current_text.strip() and current_text != previous_clipboard_poll_content:
                        sanitized = sanitize_text(current_text)
                        if sanitized:
                            print(self._("debug_new_clipboard_content", sanitized[:50]))
                            previous_clipboard_poll_content = current_text
                            if self.root.winfo_exists(): self.root.after(0, self._trigger_float_from_poll, sanitized)
                        else: previous_clipboard_poll_content = current_text
                    elif current_text is not None: previous_clipboard_poll_content = current_text
                    elif current_text is None: previous_clipboard_poll_content = None
                    time.sleep(0.5)
                except pyperclip.PyperclipException as e: print(self._("debug_poll_clipboard_error", e)); previous_clipboard_poll_content=current_text; time.sleep(1)
                except Exception as e: print(self._("debug_poll_generic_error", e)); previous_clipboard_poll_content=current_text; time.sleep(1)
            print(self._("debug_poll_thread_stop"))
        clipboard_polling_thread = threading.Thread(target=poll_clipboard, daemon=True); clipboard_polling_thread.start()
        # Mouse Listener Thread
        is_dragging = False
        def on_mouse_click(x, y, button, pressed):
            global is_dragging, drag_start_pos, drag_start_time
            if button == mouse.Button.left:
                if pressed: is_dragging = True; drag_start_pos = (x, y); drag_start_time = time.time()
                else:
                    if is_dragging:
                        is_dragging = False; release_pos=(x,y); release_time=time.time()
                        if self.select_trigger_var.get():
                            try:
                                dist = math.sqrt((release_pos[0]-drag_start_pos[0])**2 + (release_pos[1]-drag_start_pos[1])**2)
                                # print(self._("debug_mouse_released", dist, release_time - drag_start_time)) # Verbose
                                if dist > MOUSE_DRAG_THRESHOLD:
                                    print(self._("debug_selection_detected"))
                                    threading.Thread(target=self._simulate_copy_after_selection, daemon=True).start()
                            except Exception as e: print(self._("debug_mouse_release_error", e))
        def listen_mouse():
            global mouse_listener
            mouse_listener = mouse.Listener(on_click=on_mouse_click); mouse_listener.start(); mouse_listener.join()
            print(self._("debug_mouse_listener_thread_stop"))
        mouse_listener_thread = threading.Thread(target=listen_mouse, daemon=True); mouse_listener_thread.start()

    def _simulate_copy_after_selection(self):
        try:
            time.sleep(0.05); print(self._("debug_simulate_copy"))
            controller = keyboard.Controller()
            with controller.pressed(keyboard.Key.ctrl): controller.press('c'); controller.release('c')
            print(self._("debug_simulate_copy_complete"))
        except Exception as e: print(self._("debug_simulate_copy_error", e))

    def _trigger_float_from_poll(self, text_to_show):
        if not clipboard_monitor_active or not self.root.winfo_exists(): return
        try:
            self.last_mouse_pos = (self.root.winfo_pointerx(), self.root.winfo_pointery())
            print(self._("debug_poll_mouse_pos", self.last_mouse_pos))
            self.show_float_window(text_to_show)
        except Exception as e: print(self._("debug_poll_trigger_error", e))

    def stop_clipboard_monitor(self):
        global clipboard_monitor_active, clipboard_polling_thread, mouse_listener_thread, mouse_listener
        if not clipboard_monitor_active: print("监控未运行"); return
        print(self._("debug_monitor_stop"))
        clipboard_monitor_active = False
        if mouse_listener:
            try: mouse_listener.stop()
            except Exception as e: print(self._("debug_mouse_listener_stop_error", e))
        mouse_listener = None; mouse_listener_thread = None
        clipboard_polling_thread = None
        if self.root.winfo_exists():
            self.root.after(0, self.destroy_float_window)
            self.root.after(0, self.destroy_generating_window)
            self.root.after(0, self.destroy_ok_window)
        self.update_status("status_monitor_disabled", duration=3)

    # --------------------------------------------------------------------------
    # 窗口关闭处理 (修改以处理托盘和强制退出)
    # --------------------------------------------------------------------------
    def on_closing(self, force_quit=False):
        """Handles window closing action. Hides to tray or quits."""
        # If minimize to tray is enabled AND we are not force quitting, hide instead.
        if hasattr(self, 'minimize_to_tray_var') and self.minimize_to_tray_var.get() and not force_quit:
            print("关闭按钮点击，检查是否隐藏到托盘...")
            self.hide_window()
            return # Don't proceed with full shutdown if hiding

        # Proceed with full shutdown if force_quit is True or minimize_to_tray is False
        print(self._("debug_closing"))
        self._perform_cleanup(save=not force_quit) # Perform cleanup, save settings only if not force_quit

        # self.root.quit() is removed as self.root.destroy() in _perform_cleanup should handle it.
        # If self.root doesn't exist anymore, quit() would error anyway.
        pass # No explicit quit needed here now

    def _perform_cleanup(self, save=True):
        """Handles the actual cleanup tasks. Checks winfo_exists() before operations."""
        print("执行清理操作...")
        self.stop_clipboard_monitor() # Stop monitors first

        # Stop tray icon thread (if quitting completely)
        global tray_icon, tray_thread
        if tray_icon:
            print("请求停止托盘图标...")
            try:
                tray_icon.stop()
            except Exception as e:
                print(f"停止托盘图标时出错: {e}")
        # Wait briefly for the tray thread to potentially exit
        if tray_thread and tray_thread.is_alive():
             print("等待托盘线程退出...")
             tray_thread.join(timeout=0.5) # Shorter timeout
             if tray_thread.is_alive():
                 print("警告：托盘线程未在超时内退出。")
        tray_icon = None
        tray_thread = None

        # Save settings if requested
        if save:
            print("正在保存设置...")
            self.save_settings()

        # Stop Pygame
        print("正在停止 Pygame...")
        try:
            if pygame.mixer.get_init(): print(self._("debug_pygame_stop_mixer")); pygame.mixer.music.stop(); pygame.mixer.quit()
            if pygame.get_init(): print(self._("debug_pygame_quit")); pygame.quit()
        except Exception as e: print(self._("debug_pygame_close_error", e))
        try:
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    try: widget.destroy()
                    except: pass
            self.root.destroy()
        except tk.TclError as e: print(self._("debug_destroy_error", e))
        # Destroy any remaining Toplevel windows (like floaters)
        # Check if root exists before accessing children
        if hasattr(self, 'root') and self.root.winfo_exists():
            print("销毁顶层窗口...")
            try:
                for widget in self.root.winfo_children():
                    if isinstance(widget, tk.Toplevel):
                        try: widget.destroy()
                        except: pass
            except Exception as e:
                 print(f"销毁顶层窗口时出错: {e}")

        # Destroy root window last if it exists
        # Check again before destroying the root itself
        if hasattr(self, 'root') and self.root.winfo_exists():
            print("销毁主窗口...")
            try:
                self.root.destroy()
            except tk.TclError as e:
                print(self._("debug_destroy_error", e))
        print("清理完成。")


# ==============================================================================
# 程序入口点 (修改退出逻辑)
# ==============================================================================
if __name__ == "__main__":
    # Ensure only one instance is running (Optional but good practice)
    # This part might need adjustments depending on the OS and exact requirements
    # For Windows, using a mutex is common. This is a simplified placeholder.
    # lock_file = os.path.join(os.path.expanduser("~"), "anki_tts_edge.lock")
    # if os.path.exists(lock_file):
    #     print("应用程序已在运行。")
    #     # Optionally, try to signal the existing instance to show itself
    #     sys.exit(1)
    # else:
    #     with open(lock_file, "w") as f: f.write(str(os.getpid()))

    try: # Set DPI awareness
        if sys.platform == "win32": ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e: print(f"Failed to set DPI awareness: {e}") # Use basic print before app init

    root = ctk.CTk()
    app = EdgeTTSApp(root) # Pygame/Language/Tray initialized inside EdgeTTSApp
    try:
        print("启动 Tkinter 主循环...")
        root.mainloop()
        print("Tkinter 主循环已结束。")
    except KeyboardInterrupt:
        print("用户中断 (KeyboardInterrupt)。")
        if app:
            # Ensure cleanup happens on the main thread if possible
            if threading.current_thread() is threading.main_thread():
                 app.quit_application()
            else:
                 # Schedule quit_application on the main thread
                 if root.winfo_exists():
                     root.after(0, app.quit_application)
                 else: # Fallback if root is already gone
                     app._perform_cleanup() # Direct cleanup
    except Exception as e:
         print(f"主循环中发生意外错误: {e}")
         # Attempt cleanup even on unexpected errors
         if app: app._perform_cleanup(save=False) # Don't save on crash
    finally:
        print("程序最终退出。")
        # Clean up lock file if used (ensure it's robust)
        # if os.path.exists(lock_file):
        #     try: os.remove(lock_file)
        #     except Exception as e: print(f"无法删除锁定文件: {e}")
