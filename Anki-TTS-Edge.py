# ==============================================================================
# 导入所需库
# ==============================================================================
import sys
import os
import re
import shutil
import time
import threading
import asyncio  # 用于异步操作 (如获取声音列表、生成音频)
from datetime import datetime
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import messagebox, colorchooser # 导入 colorchooser
import json
# Pillow 导入尝试移到 __init__ 中使用处

# ==============================================================================
# <<<<<<< 添加: 自定义窗口标题 >>>>>>>>>
# ==============================================================================
# 在这里修改你想要的窗口标题
CUSTOM_WINDOW_TITLE = "Anki-TTS-Edge (v1.3)" # Increment version
# ==============================================================================

# ==============================================================================
# 依赖检查与导入
# ==============================================================================
# 检查必要的第三方库是否已安装
def check_dependencies():
    """检查所有依赖库是否安装"""
    dependencies = {
        "customtkinter": "pip install customtkinter",
        "edge_tts": "pip install edge-tts",  # 用于调用 Edge TTS 服务
        "pyperclip": "pip install pyperclip",  # 用于剪贴板操作
        "pygame": "pip install pygame",        # 用于播放音频
        "pynput": "pip install pynput",        # 用于监听鼠标事件 (浮窗定位)
        "win32clipboard": "pip install pywin32",  # 用于复制文件到剪贴板
        "win32con": "pip install pywin32"         # 用于复制文件到剪贴板
    }
    missing = []
    checked_pywin32 = False
    for module, install_cmd in dependencies.items():
        try:
            if module == "edge_tts": import edge_tts.communicate
            elif module.startswith("win32"):
                if not checked_pywin32: __import__("win32clipboard"); checked_pywin32 = True
            elif module == "pynput": from pynput import mouse
            elif module == "pygame": import pygame
            else: __import__(module)
        except ImportError:
            if module.startswith("win32"):
                if not checked_pywin32: missing.append((module, install_cmd)); checked_pywin32 = True
            else: missing.append((module, install_cmd))

    if missing:
        print("以下依赖库未安装：")
        install_cmds = set()
        for module, install_cmd in missing: print(f"- {module}"); install_cmds.add(install_cmd)
        print("\n请确保在激活的虚拟环境 (.venv) 中安装以上依赖库后重新运行脚本。")
        print(f"建议安装命令: {' '.join(install_cmds)}")
        sys.exit(1)
    else: print("所有依赖库已安装！")

check_dependencies()

# 导入检查通过的库
import customtkinter as ctk
import pyperclip
try: import pygame
except ImportError: print("错误：无法导入 pygame。请确保已安装：pip install pygame"); sys.exit(1)
from pynput import mouse
import win32clipboard
import win32con
import edge_tts
from edge_tts import VoicesManager

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
os.makedirs(AUDIO_DIR, exist_ok=True)

# ==============================================================================
# 全局变量
# ==============================================================================
app = None
status_update_job = None
clipboard_monitor_active = False
clipboard_polling_thread = None
previous_clipboard_poll_content = None # Track content from previous poll cycle

# ==============================================================================
# 模块 1：文本处理 (无修改)
# ==============================================================================
def sanitize_text(text):
    if not text: return ""
    text = re.sub(r'[^\w\s\.,!?;:\'"()\[\]{}<>%&$@#*+\-=/]', '', text, flags=re.UNICODE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text else ""

# ==============================================================================
# 模块 2：剪贴板操作 (无修改)
# ==============================================================================
def copy_file_to_clipboard(file_path):
    try:
        class DROPFILES(ctypes.Structure):
            _fields_ = [("pFiles", wintypes.DWORD), ("pt", wintypes.POINT),
                        ("fNC", wintypes.BOOL), ("fWide", wintypes.BOOL)]
        file_path = os.path.abspath(file_path)
        offset = ctypes.sizeof(DROPFILES)
        buffer_size = offset + (len(file_path) + 2) * ctypes.sizeof(wintypes.WCHAR)
        buf = (ctypes.c_char * buffer_size)()
        df = ctypes.cast(buf, ctypes.POINTER(DROPFILES)).contents
        df.pFiles = offset; df.fWide = True
        path_bytes = file_path.encode('utf-16-le')
        ctypes.memmove(ctypes.byref(buf, offset), path_bytes, len(path_bytes))
        buf[offset + len(path_bytes)] = 0; buf[offset + len(path_bytes) + 1] = 0
        win32clipboard.OpenClipboard(); win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_HDROP, buf)
        win32clipboard.CloseClipboard()
        print(f"文件已复制到剪贴板 (CF_HDROP): {file_path}")
        if app: app.update_status("文件已复制到剪贴板", duration=3)
    except Exception as e:
        print(f"复制文件到剪贴板失败: {e}")
        if app: app.update_status(f"复制文件失败: {e}", error=True)

# ==============================================================================
# 模块 3：声音列表获取 (无修改)
# ==============================================================================
async def get_available_voices_async():
    try:
        voices = await VoicesManager.create()
        raw_voices_list = voices.find()
        voice_pattern = re.compile(r"^Microsoft Server Speech Text to Speech Voice \(([a-z]{2,3})-([A-Z]{2,}(?:-[A-Za-z]+)?), (.*Neural)\)$")
        hierarchical_voices = {}
        for v in raw_voices_list:
            full_name = v['Name']; match = voice_pattern.match(full_name)
            if match:
                lang, region, name_part = match.groups()
                if lang not in hierarchical_voices: hierarchical_voices[lang] = {}
                if region not in hierarchical_voices[lang]: hierarchical_voices[lang][region] = []
                hierarchical_voices[lang][region].append(full_name)
            # else: print(f"Skipping voice format: {full_name}") # Optional debug
        for lang in hierarchical_voices:
            for region in hierarchical_voices[lang]: hierarchical_voices[lang][region].sort()
            hierarchical_voices[lang] = dict(sorted(hierarchical_voices[lang].items()))
        sorted_hierarchical_voices = {}
        if "zh" in hierarchical_voices: sorted_hierarchical_voices["zh"] = hierarchical_voices.pop("zh")
        if "en" in hierarchical_voices: sorted_hierarchical_voices["en"] = hierarchical_voices.pop("en")
        for lang in sorted(hierarchical_voices.keys()): sorted_hierarchical_voices[lang] = hierarchical_voices[lang]
        total_voices = sum(len(v) for lang_data in sorted_hierarchical_voices.values() for v in lang_data.values())
        print(f"获取到 {total_voices} 个声音，已按 语言->地区->名称 层级分类。")
        return sorted_hierarchical_voices
    except Exception as e:
        print(f"获取声音列表失败: {e}")
        if app: app.update_status(f"获取声音列表失败: {e}", error=True)
        return {}

def refresh_voices_list():
    def run_async_get_voices():
        data = {}
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            data = loop.run_until_complete(get_available_voices_async()); loop.close()
        except Exception as e: print(f"运行异步获取声音任务时出错: {e}"); data = {}
        finally:
            if app and app.root.winfo_exists(): app.root.after(0, app.update_voice_ui, data)
    threading.Thread(target=run_async_get_voices, daemon=True).start()

# ==============================================================================
# 模块 4：音频生成 (无修改)
# ==============================================================================
async def generate_audio_edge_tts_async(text, voice, rate, volume, pitch, output_path):
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        await communicate.save(output_path)
        print(f"Edge TTS 音频生成成功: {output_path}")
        return output_path
    except Exception as e: print(f"Edge TTS 音频生成失败: {e}"); return None

def generate_audio(text, voice, rate_str, volume_str, pitch_str, on_complete=None):
    text = sanitize_text(text)
    if not text:
        print("文本为空，无法生成音频")
        if app: app.update_status("错误：文本不能为空", error=True)
        if on_complete:
            if app and app.root.winfo_exists(): app.root.after(0, lambda: on_complete(None, "文本为空"))
            else: on_complete(None, "文本为空")
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    match = re.search(r", (.*Neural)\)$", voice)
    safe_part = re.sub(r'\W+', '', match.group(1)) if match else "UnknownVoice"
    filename = f"Anki-TTS-Edge_{safe_part}_{timestamp}.mp3"
    output_path = os.path.join(AUDIO_DIR, filename)
    print(f"准备生成音频: voice='{voice}', rate='{rate_str}', volume='{volume_str}', pitch='{pitch_str}'")
    print(f"输出路径: {output_path}")
    def run_async_in_thread():
        result = None; error = None
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            result = loop.run_until_complete(generate_audio_edge_tts_async(text, voice, rate_str, volume_str, pitch_str, output_path))
            loop.close()
            if not result: error = "Edge TTS 内部错误"
        except Exception as e: print(f"运行异步生成任务时出错: {e}"); error = str(e)
        finally:
            if on_complete:
                if app and app.root.winfo_exists():
                    app.root.after(0, lambda p=result, e=error: on_complete(p, e))
                else: on_complete(result, error)
    threading.Thread(target=run_async_in_thread, daemon=True).start()

# ==============================================================================
# 模块 5：文件管理 (包含 pygame 播放检查的尝试)
# ==============================================================================
def manage_audio_files():
    try:
        max_str = app.max_files_entry.get() if app and hasattr(app, 'max_files_entry') else str(DEFAULT_MAX_AUDIO_FILES)
        max_f = int(max_str) if max_str.isdigit() else DEFAULT_MAX_AUDIO_FILES
        max_f = max(1, min(50, max_f)) # Clamp between 1 and 50
    except: max_f = DEFAULT_MAX_AUDIO_FILES
    try:
        if not os.path.exists(AUDIO_DIR): return
        files = sorted( [f for f in os.listdir(AUDIO_DIR) if f.endswith(".mp3")], key=lambda x: os.path.getctime(os.path.join(AUDIO_DIR, x)) )
        while len(files) > max_f:
            file_rm = files.pop(0); path_rm = os.path.join(AUDIO_DIR, file_rm)
            try:
                mixer_busy = False
                if pygame.mixer.get_init(): mixer_busy = pygame.mixer.music.get_busy()
                if mixer_busy: print(f"播放器可能正忙，延迟删除: {file_rm}") # Just a notification
                os.remove(path_rm); print(f"删除旧音频文件: {file_rm}")
            except PermissionError as e: print(f"删除文件 {file_rm} 失败 (可能正在使用): {e}")
            except OSError as e: print(f"删除文件 {file_rm} 失败: {e}")
    except Exception as e: print(f"文件管理出错: {e}")

# ==============================================================================
# 模块 6：UI 主类 (EdgeTTSApp)
# ==============================================================================
class EdgeTTSApp:
    def __init__(self, root):
        self.root = root; self.root.title(CUSTOM_WINDOW_TITLE)
        self.root.geometry("550x750"); self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        global app; app = self
        # Initialize Pygame Mixer
        try: pygame.init(); pygame.mixer.init(); print("pygame mixer 初始化成功。")
        except Exception as e:
            print(f"pygame mixer 初始化失败: {e}")
            messagebox.showerror("初始化错误", f"无法初始化音频播放器 (pygame): {e}\n自动播放功能将不可用。")
        # UI Variables
        self.voice_display_to_full_map = {}; self.hierarchical_voice_data = {}
        self.current_full_voice_name = None; self.current_custom_color = None
        # Settings & Appearance
        settings = self.load_settings()
        appearance = settings.get("appearance_mode", DEFAULT_APPEARANCE_MODE)
        self.current_custom_color = settings.get("custom_theme_color", DEFAULT_CUSTOM_COLOR)
        ctk.set_appearance_mode(appearance)
        # Main Frame
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent"); self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1); self.main_frame.grid_rowconfigure(1, weight=1)
        # Text Input Area
        text_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent"); text_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15)); text_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(text_frame, text="📝 输入文本:", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.text_input = ctk.CTkTextbox(text_frame, height=100, wrap="word", corner_radius=8, border_width=1); self.text_input.grid(row=1, column=0, sticky="nsew")
        # Tab View
        self.tab_view = ctk.CTkTabview(self.main_frame, corner_radius=8); self.tab_view.grid(row=1, column=0, sticky="nsew", pady=0)
        self.tab_view.add("🔊 声音"); self.tab_view.add("⚙️ 设置"); self.tab_view.add("🎨 外观")
        # Voice Tab
        voice_tab = self.tab_view.tab("🔊 声音"); voice_tab.grid_columnconfigure((0, 1), weight=1); voice_tab.grid_rowconfigure(1, weight=1)
        left_outer = ctk.CTkFrame(voice_tab, fg_color="transparent"); left_outer.grid(row=0, column=0, rowspan=2, padx=(0, 5), pady=5, sticky="nsew"); left_outer.grid_rowconfigure(1, weight=1)
        self.language_filter_entry_left = ctk.CTkEntry(left_outer, placeholder_text="筛选语言 (如: zh)..."); self.language_filter_entry_left.grid(row=0, column=0, padx=0, pady=(0, 5), sticky="ew"); self.language_filter_entry_left.bind("<KeyRelease>", lambda e: self._filter_voices_inline('left'))
        self.inline_voice_list_frame_left = ctk.CTkScrollableFrame(left_outer, label_text="声音列表 1", height=150); self.inline_voice_list_frame_left.grid(row=1, column=0, padx=0, pady=0, sticky="nsew"); self.inline_voice_list_frame_left.grid_columnconfigure(0, weight=1)
        right_outer = ctk.CTkFrame(voice_tab, fg_color="transparent"); right_outer.grid(row=0, column=1, rowspan=2, padx=(5, 0), pady=5, sticky="nsew"); right_outer.grid_rowconfigure(1, weight=1)
        self.language_filter_entry_right = ctk.CTkEntry(right_outer, placeholder_text="筛选语言 (如: en)..."); self.language_filter_entry_right.grid(row=0, column=0, padx=0, pady=(0, 5), sticky="ew"); self.language_filter_entry_right.bind("<KeyRelease>", lambda e: self._filter_voices_inline('right'))
        self.inline_voice_list_frame_right = ctk.CTkScrollableFrame(right_outer, label_text="声音列表 2", height=150); self.inline_voice_list_frame_right.grid(row=1, column=0, padx=0, pady=0, sticky="nsew"); self.inline_voice_list_frame_right.grid_columnconfigure(0, weight=1)
        saved_f_l = settings.get("language_filter_left", "zh"); saved_f_r = settings.get("language_filter_right", "en")
        self.language_filter_entry_left.insert(0, saved_f_l); self.language_filter_entry_right.insert(0, saved_f_r)
        controls_frame = ctk.CTkFrame(voice_tab, fg_color="transparent"); controls_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="ew"); controls_frame.grid_columnconfigure(1, weight=1)
        self.refresh_button = ctk.CTkButton(controls_frame, text="🔄 刷新声音列表", command=self.refresh_voices_ui, font=ctk.CTkFont(size=12)); self.refresh_button.grid(row=0, column=0, columnspan=3, padx=0, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(controls_frame, text="语速:").grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        self.rate_slider_var = ctk.IntVar(value=settings.get("rate", 0)); self.rate_slider = ctk.CTkSlider(controls_frame, from_=-100, to=100, number_of_steps=40, variable=self.rate_slider_var, command=self.update_rate_label); self.rate_slider.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.rate_value_label = ctk.CTkLabel(controls_frame, text=f"{self.rate_slider_var.get():+}%", width=45); self.rate_value_label.grid(row=1, column=2, padx=(5, 0), pady=5, sticky="w")
        ctk.CTkLabel(controls_frame, text="音量:").grid(row=2, column=0, padx=(0, 5), pady=5, sticky="w")
        self.volume_slider_var = ctk.IntVar(value=settings.get("volume", 0)); self.volume_slider = ctk.CTkSlider(controls_frame, from_=-100, to=100, number_of_steps=40, variable=self.volume_slider_var, command=self.update_volume_label); self.volume_slider.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.volume_value_label = ctk.CTkLabel(controls_frame, text=f"{self.volume_slider_var.get():+}%", width=45); self.volume_value_label.grid(row=2, column=2, padx=(5, 0), pady=5, sticky="w")
        # Settings Tab
        settings_tab = self.tab_view.tab("⚙️ 设置"); settings_tab.grid_columnconfigure(0, weight=1)
        output_cache_frame = ctk.CTkFrame(settings_tab); output_cache_frame.pack(fill="x", padx=10, pady=10); output_cache_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(output_cache_frame, text="输出与缓存", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=3, pady=(5, 10), padx=10, sticky="w")
        self.copy_to_clipboard_var = ctk.BooleanVar(value=settings.get("copy_path_enabled", True)); self.copy_to_clipboard_switch = ctk.CTkSwitch(output_cache_frame, text="🔗 自动复制文件", variable=self.copy_to_clipboard_var, onvalue=True, offvalue=False); self.copy_to_clipboard_switch.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.play_audio_var = ctk.BooleanVar(value=settings.get("autoplay_enabled", False)); self.play_audio_switch = ctk.CTkSwitch(output_cache_frame, text="▶️ 自动播放", variable=self.play_audio_var, onvalue=True, offvalue=False); self.play_audio_switch.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(output_cache_frame, text="🔢 最大缓存数:").grid(row=2, column=0, padx=(10, 5), pady=(5, 10), sticky="w")
        self.max_files_entry = ctk.CTkEntry(output_cache_frame, width=60); self.max_files_entry.insert(0, str(settings.get("max_audio_files", DEFAULT_MAX_AUDIO_FILES))); self.max_files_entry.grid(row=2, column=1, padx=5, pady=(5, 10), sticky="w")
        clipboard_frame = ctk.CTkFrame(settings_tab); clipboard_frame.pack(fill="x", padx=10, pady=(0, 10)); clipboard_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(clipboard_frame, text="剪贴板功能", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=(5, 10), padx=10, sticky="w")
        self.select_to_audio_var = ctk.BooleanVar(value=settings.get("monitor_enabled", False)); self.select_to_audio_switch = ctk.CTkSwitch(clipboard_frame, text="🖱️ 启用复制生音频浮窗", variable=self.select_to_audio_var, command=self.toggle_select_to_audio, onvalue=True, offvalue=False); self.select_to_audio_switch.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="w")
        # Appearance Tab
        appearance_tab = self.tab_view.tab("🎨 外观"); appearance_tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(appearance_tab, text="界面主题:").grid(row=0, column=0, padx=(15, 5), pady=15, sticky="w")
        self.appearance_mode_segmented_button = ctk.CTkSegmentedButton( appearance_tab, values=["浅色模式", "深色模式"], command=self._change_appearance_mode ); self.appearance_mode_segmented_button.grid(row=0, column=1, columnspan=3, padx=5, pady=15, sticky="ew")
        initial_mode_text = "浅色模式" if appearance == "light" else "深色模式"; self.appearance_mode_segmented_button.set(initial_mode_text)
        ctk.CTkLabel(appearance_tab, text="自定义主色 (Hex):").grid(row=1, column=0, padx=(15, 5), pady=(5, 15), sticky="w")
        self.custom_color_entry = ctk.CTkEntry(appearance_tab, placeholder_text="#1F6AA5"); self.custom_color_entry.grid(row=1, column=1, padx=5, pady=(5, 15), sticky="ew"); self.custom_color_entry.insert(0, self.current_custom_color or "")
        self.pick_color_button = ctk.CTkButton(appearance_tab, text="🎨", width=30, command=self._pick_custom_color); self.pick_color_button.grid(row=1, column=2, padx=(0, 5), pady=(5, 15), sticky="w")
        self.apply_color_button = ctk.CTkButton(appearance_tab, text="应用颜色", command=self._apply_custom_color); self.apply_color_button.grid(row=1, column=3, padx=(0, 15), pady=(5, 15), sticky="e")
        # Bottom Frame (Button & Status)
        bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent"); bottom_frame.grid(row=2, column=0, sticky="ew", pady=(15, 5)); bottom_frame.grid_columnconfigure(0, weight=1)
        self.generate_button = ctk.CTkButton( bottom_frame, text="生成音频", command=self.generate_audio_manual, height=40, font=ctk.CTkFont(size=16, weight="bold"), corner_radius=10 ); self.generate_button.grid(row=0, column=0, pady=(0, 15), sticky="")
        self.status_bar_frame = ctk.CTkFrame(self.main_frame, height=25, corner_radius=0); self.status_bar_frame.grid(row=3, column=0, sticky="ew"); self.status_bar_frame.grid_columnconfigure(0, weight=1); self.status_bar_frame.grid_columnconfigure(1, weight=0)
        self.status_label = ctk.CTkLabel(self.status_bar_frame, text="✅ 准备就绪", anchor="w", font=ctk.CTkFont(size=12)); self.status_label.grid(row=0, column=0, sticky="ew", padx=(10, 5))
        self.progress_bar = ctk.CTkProgressBar(self.status_bar_frame, height=10, width=100, corner_radius=5); self.progress_bar.set(0); self.progress_bar.grid_remove()
        # Float Window Vars
        self.float_window = None; self.ok_window = None; self.generating_window = None
        self.generating_animation_job = None; self.generating_window_label = None
        self.last_mouse_pos = (0, 0); self._text_for_float_trigger = None
        self._float_window_close_job = None; self._ok_window_close_job = None
        # Initial Actions
        self._apply_custom_color(save=False); self.refresh_voices_ui()
        if self.select_to_audio_var.get(): self.start_clipboard_monitor()

    # --------------------------------------------------------------------------
    # UI 更新与状态管理方法 (无修改 - 除了修复 TypeError)
    # --------------------------------------------------------------------------
    def update_status(self, message, duration=0, error=False, permanent=False, show_progress=False):
        global status_update_job
        def _update():
            global status_update_job
            if status_update_job:
                try: self.status_label.after_cancel(status_update_job)
                except: pass
                status_update_job = None
            status_text = message
            try:
                label_fg_color = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
                text_color = label_fg_color[ctk.get_appearance_mode() == 'dark'] if isinstance(label_fg_color, (list, tuple)) else label_fg_color
            except: text_color = ("#000000", "#FFFFFF") # Fallback
            if error:
                status_text = f"❌ {message}"
                text_color = ("#D81B60", "#FF8A80")
            elif "成功" in message or "完成" in message or "已复制" in message:
                 status_text = f"✅ {message}"
                 text_color = ("#00796B", "#80CBC4")
            elif "正在" in message or "..." in message:
                 status_text = f"⏳ {message}"
            self.status_label.configure(text=status_text, text_color=text_color)
            if show_progress:
                self.progress_bar.grid(row=0, column=1, padx=(0, 10), sticky="e")
                try:
                    progress_bar_theme_color = ctk.ThemeManager.theme["CTkProgressBar"]["progress_color"]
                    default_progress_color = progress_bar_theme_color[ctk.get_appearance_mode() == 'dark'] if isinstance(progress_bar_theme_color, (list, tuple)) else progress_bar_theme_color
                    progress_bar_color = self.current_custom_color or default_progress_color
                except: progress_bar_color = self.current_custom_color or "#1F6AA5" # Fallback
                self.progress_bar.configure(mode="indeterminate", progress_color=progress_bar_color)
                if hasattr(self.progress_bar, 'start'): self.progress_bar.start()
            else:
                if hasattr(self.progress_bar, 'stop'): self.progress_bar.stop()
                self.progress_bar.grid_remove()
            if not permanent and duration > 0:
                 # Use lambda to ensure keyword arguments work correctly with after's callback
                 status_update_job = self.status_label.after(duration * 1000, lambda msg="✅ 准备就绪": self.update_status(msg))
        # Run update in main thread if called from another thread
        if threading.current_thread() is not threading.main_thread():
            if self.root.winfo_exists(): self.root.after(0, _update)
        else: _update() # Run directly if already in main thread

    def update_rate_label(self, value): val = int(value); self.rate_value_label.configure(text=f"{val:+}%")
    def update_volume_label(self, value): val = int(value); self.volume_value_label.configure(text=f"{val:+}%")
    def refresh_voices_ui(self):
        self.update_status("正在获取声音列表...", permanent=True)
        self.refresh_button.configure(state="disabled")
        for frame in [self.inline_voice_list_frame_left, self.inline_voice_list_frame_right]:
            for widget in frame.winfo_children(): widget.destroy()
            ctk.CTkLabel(frame, text="正在加载...", text_color="gray").pack(pady=20)
        refresh_voices_list()

    def update_voice_ui(self, hierarchical_voice_data):
        print("DEBUG: update_voice_ui called")
        self.hierarchical_voice_data = hierarchical_voice_data
        self.refresh_button.configure(state="normal")
        self.voice_display_to_full_map.clear()
        if not hierarchical_voice_data:
            print("DEBUG: No voice data received.")
            for frame in [self.inline_voice_list_frame_left, self.inline_voice_list_frame_right]:
                for widget in frame.winfo_children(): widget.destroy()
                ctk.CTkLabel(frame, text="获取失败", text_color="red").pack(pady=20)
            self.update_status("获取声音列表失败", error=True)
            return
        name_extract_pattern = re.compile(r", (.*Neural)\)$")
        for lang_data in hierarchical_voice_data.values():
            for region_voices in lang_data.values():
                for full_name in region_voices:
                    match = name_extract_pattern.search(full_name)
                    display_name = match.group(1) if match else full_name
                    original_display_name = display_name; count = 1
                    while display_name in self.voice_display_to_full_map:
                        display_name = f"{original_display_name}_{count}"; count += 1
                    self.voice_display_to_full_map[display_name] = full_name
        settings = self.load_settings()
        selected_voice = settings.get("selected_voice", DEFAULT_VOICE)
        if selected_voice in self.voice_display_to_full_map.values(): self.current_full_voice_name = selected_voice
        elif DEFAULT_VOICE in self.voice_display_to_full_map.values(): self.current_full_voice_name = DEFAULT_VOICE
        else:
            available = list(self.voice_display_to_full_map.values())
            self.current_full_voice_name = available[0] if available else None
        self._populate_inline_voice_list('left'); self._populate_inline_voice_list('right')
        print(f"DEBUG: Voice UI updated. Current Voice: {self.current_full_voice_name}")
        self.update_status("声音列表已更新", duration=3)

    # --------------------------------------------------------------------------
    # 内联声音选择器方法 (双列版本) (无修改)
    # --------------------------------------------------------------------------
    def _populate_inline_voice_list(self, side):
        frame = self.inline_voice_list_frame_left if side == 'left' else self.inline_voice_list_frame_right
        filter_entry = self.language_filter_entry_left if side == 'left' else self.language_filter_entry_right
        if not frame: return
        filter_term = filter_entry.get() if hasattr(self, f'language_filter_entry_{side}') else ""
        for widget in frame.winfo_children(): widget.destroy()
        row_count = 0
        filter_codes = [code.strip().lower() for code in re.split(r'[,\s]+', filter_term) if code.strip()]
        if not self.voice_display_to_full_map:
             ctk.CTkLabel(frame, text="声音列表为空", text_color="gray").grid(row=0, column=0, pady=20)
             return
        sorted_voices = sorted(self.voice_display_to_full_map.items())
        found_match = False
        for display_name, full_name in sorted_voices:
            apply_filter = len(filter_codes) > 0; match_filter = False
            if apply_filter:
                lang_match = re.search(r'\(([a-z]{2,3})-', full_name)
                lang_code = lang_match.group(1).lower() if lang_match else ""
                if lang_code in filter_codes: match_filter = True
            if apply_filter and not match_filter: continue
            found_match = True
            is_selected = (full_name == self.current_full_voice_name)
            try:
                default_btn_fg = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
                default_btn_fg_mode = default_btn_fg[ctk.get_appearance_mode() == 'dark'] if isinstance(default_btn_fg, (list, tuple)) else default_btn_fg
            except: default_btn_fg_mode = "#1F6AA5"
            btn_fg_color = self.current_custom_color or default_btn_fg_mode
            btn_hover_color = self._calculate_hover_color(btn_fg_color)
            try:
                default_text_color = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
                text_color_normal = default_text_color[ctk.get_appearance_mode() == 'dark'] if isinstance(default_text_color, (list, tuple)) else default_text_color
            except: text_color_normal = "#000000"
            text_color_selected = self._get_contrasting_text_color(btn_fg_color)
            btn = ctk.CTkButton( frame, text=display_name, anchor="w", fg_color=btn_fg_color if is_selected else "transparent", hover_color=btn_hover_color, text_color=text_color_selected if is_selected else text_color_normal, command=lambda fn=full_name: self._select_voice_inline(fn) )
            btn.grid(row=row_count, column=0, padx=5, pady=2, sticky="ew")
            row_count += 1
        if not found_match: ctk.CTkLabel(frame, text="无匹配声音", text_color="gray").grid(row=0, column=0, pady=20)

    def _filter_voices_inline(self, side): self._populate_inline_voice_list(side); self.save_settings()
    def _select_voice_inline(self, full_name):
        if self.current_full_voice_name != full_name:
            self.current_full_voice_name = full_name; print(f"DEBUG _select_voice_inline: Selected {full_name}")
            self._populate_inline_voice_list('left'); self._populate_inline_voice_list('right'); self.save_settings()

    # --------------------------------------------------------------------------
    # 主题与颜色切换方法 (无修改)
    # --------------------------------------------------------------------------
    def _change_appearance_mode(self, selected_value):
        mode_map = {"浅色模式": "light", "深色模式": "dark"}; new_mode = mode_map.get(selected_value, DEFAULT_APPEARANCE_MODE)
        print(f"切换外观模式到: {new_mode}"); ctk.set_appearance_mode(new_mode); self._apply_custom_color(save=True)
    def _pick_custom_color(self):
        initial = self.custom_color_entry.get() or self.current_custom_color or DEFAULT_CUSTOM_COLOR
        chosen = colorchooser.askcolor(title="选择主颜色", initialcolor=initial)
        if chosen and chosen[1]:
            hex_color = chosen[1]; self.custom_color_entry.delete(0, tk.END); self.custom_color_entry.insert(0, hex_color); self._apply_custom_color()
    def _apply_custom_color(self, save=True):
        new_color = self.custom_color_entry.get().strip()
        if not re.match(r"^#[0-9a-fA-F]{6}$", new_color):
            if new_color: messagebox.showerror("无效颜色", f"请输入有效的 6 位十六进制颜色代码, 而不是 '{new_color}'")
            self.current_custom_color = DEFAULT_CUSTOM_COLOR; self.custom_color_entry.delete(0, tk.END); self.custom_color_entry.insert(0, self.current_custom_color)
            new_color = self.current_custom_color; save = False
        else: self.current_custom_color = new_color
        print(f"应用自定义颜色: {self.current_custom_color}"); hover = self._calculate_hover_color(self.current_custom_color)
        buttons = [getattr(self, n, None) for n in ['generate_button', 'refresh_button', 'apply_color_button', 'pick_color_button']]
        for b in buttons:
             if b: b.configure(fg_color=self.current_custom_color, hover_color=hover)
        switches = [getattr(self, n, None) for n in ['copy_to_clipboard_switch', 'play_audio_switch', 'select_to_audio_switch']]
        for s in switches:
             if s: s.configure(progress_color=self.current_custom_color)
        sliders = [getattr(self, n, None) for n in ['rate_slider', 'volume_slider']]
        for s in sliders:
             if s: s.configure(button_color=self.current_custom_color, progress_color=self.current_custom_color, button_hover_color=hover)
        if hasattr(self, 'progress_bar'):
             try:
                 theme_color = ctk.ThemeManager.theme["CTkProgressBar"]["progress_color"]
                 default_color = theme_color[ctk.get_appearance_mode() == 'dark'] if isinstance(theme_color, (list, tuple)) else theme_color
                 color = self.current_custom_color or default_color
             except: color = self.current_custom_color or "#1F6AA5"
             self.progress_bar.configure(progress_color=color)
        if hasattr(self, 'tab_view'): self.tab_view.configure(segmented_button_selected_color=self.current_custom_color, segmented_button_selected_hover_color=hover)
        if hasattr(self, 'appearance_mode_segmented_button'): self.appearance_mode_segmented_button.configure(selected_color=self.current_custom_color, selected_hover_color=hover)
        self._populate_inline_voice_list('left'); self._populate_inline_voice_list('right')
        if save: self.save_settings()
    def _calculate_hover_color(self, hex_color):
        try:
            h = hex_color.lstrip('#'); r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            hr, hg, hb = max(0, r-20), max(0, g-20), max(0, b-20); return f"#{hr:02x}{hg:02x}{hb:02x}"
        except:
            try:
                default = ctk.ThemeManager.theme["CTkButton"]["hover_color"]
                return default[ctk.get_appearance_mode() == 'dark'] if isinstance(default, (list, tuple)) else default
            except: return "#A0A0A0"
    def _get_contrasting_text_color(self, bg_hex_color):
        try:
            h = bg_hex_color.lstrip('#'); r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            brightness = (r*299 + g*587 + b*114) / 1000; return "#000000" if brightness > 128 else "#FFFFFF"
        except:
            try:
                default = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
                return default[ctk.get_appearance_mode() == 'dark'] if isinstance(default, (list, tuple)) else default
            except: return "#000000"

    # --------------------------------------------------------------------------
    # 设置加载与保存 (无修改)
    # --------------------------------------------------------------------------
    def load_settings(self):
        defaults = {"copy_path_enabled": True, "autoplay_enabled": False, "monitor_enabled": False, "max_audio_files": DEFAULT_MAX_AUDIO_FILES, "selected_voice": DEFAULT_VOICE, "rate": 0, "volume": 0, "appearance_mode": DEFAULT_APPEARANCE_MODE, "language_filter_left": "zh", "language_filter_right": "en", "custom_theme_color": DEFAULT_CUSTOM_COLOR}
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f: settings = json.load(f)
                merged = defaults.copy(); merged.update(settings)
                loaded_color = merged.get("custom_theme_color", DEFAULT_CUSTOM_COLOR)
                if not re.match(r"^#[0-9a-fA-F]{6}$", loaded_color):
                    print(f"警告：加载的颜色 '{loaded_color}' 无效，使用默认。"); merged["custom_theme_color"] = DEFAULT_CUSTOM_COLOR
                return merged
        except Exception as e: print(f"加载设置失败: {e}")
        return defaults
    def save_settings(self):
        try: max_f = int(self.max_files_entry.get()); max_f = max_f if 1 <= max_f <= 50 else DEFAULT_MAX_AUDIO_FILES
        except ValueError: max_f = DEFAULT_MAX_AUDIO_FILES
        filter_left = self.language_filter_entry_left.get() if hasattr(self, 'language_filter_entry_left') else "zh"
        filter_right = self.language_filter_entry_right.get() if hasattr(self, 'language_filter_entry_right') else "en"
        settings = { "selected_voice": self.current_full_voice_name or DEFAULT_VOICE, "copy_path_enabled": self.copy_to_clipboard_var.get(), "autoplay_enabled": self.play_audio_var.get(), "monitor_enabled": self.select_to_audio_var.get(), "max_audio_files": max_f, "rate": self.rate_slider_var.get(), "volume": self.volume_slider_var.get(), "appearance_mode": ctk.get_appearance_mode().lower(), "language_filter_left": filter_left, "language_filter_right": filter_right, "custom_theme_color": self.current_custom_color or DEFAULT_CUSTOM_COLOR }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f: json.dump(settings, f, ensure_ascii=False, indent=4)
            print("设置已保存。")
        except Exception as e: print(f"保存设置失败: {e}")

    # --------------------------------------------------------------------------
    # 音频生成与处理方法 (使用 pygame 播放)
    # --------------------------------------------------------------------------
    def generate_audio_manual(self):
        text = self.text_input.get("1.0", "end").strip()
        if not text: self.update_status("错误：请输入文本", error=True, duration=5); return
        voice = self.current_full_voice_name
        if not voice: self.update_status("错误：请选择一个声音", error=True, duration=5); return
        rate_str = f"{self.rate_slider_var.get():+}%"
        volume_str = f"{self.volume_slider_var.get():+}%"
        pitch_str = "+0Hz"

        def on_manual_complete(path, error_msg=None):
            if self.root.winfo_exists(): self.generate_button.configure(state="normal")
            if path:
                self.update_status(f"生成成功: {os.path.basename(path)}", duration=10)
                print("音频生成完成:", path)
                play_enabled = self.play_audio_var.get()
                print(f"DEBUG: Autoplay enabled (manual)? {play_enabled}")
                if play_enabled:
                    self.play_audio_pygame(path) # Use pygame player
                if self.copy_to_clipboard_var.get(): copy_file_to_clipboard(path)
            else:
                err_str = f"音频生成失败: {error_msg or '未知错误'}"
                print(err_str); self.update_status(err_str, error=True) # Keep error visible
            manage_audio_files() # Manage files after operation

        self.generate_button.configure(state="disabled")
        display_name = self._get_display_voice_name(voice)
        self.update_status(f"正在生成音频 (声音: {display_name})...", permanent=True, show_progress=True)
        generate_audio(text, voice, rate_str, volume_str, pitch_str, on_manual_complete)

    def play_audio_pygame(self, audio_path):
        """使用 pygame.mixer 播放音频"""
        print(f"DEBUG: play_audio_pygame called with path: {audio_path}")
        if not pygame.mixer.get_init():
            print("ERROR: Pygame mixer 未初始化，无法播放。")
            if self.root.winfo_exists(): self.update_status("播放错误: Mixer未初始化", error=True)
            return
        if not os.path.exists(audio_path):
             print(f"ERROR: 音频文件不存在: {audio_path}")
             if self.root.winfo_exists(): self.update_status("播放错误: 文件不存在", error=True)
             return

        try:
            # If music is playing, stop and unload it first
            if pygame.mixer.music.get_busy():
                print("DEBUG: 停止当前播放...")
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                # Give a tiny moment for the system to potentially release the file
                time.sleep(0.05)

            print(f"DEBUG: 尝试加载并播放: {audio_path}")
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            print("DEBUG: Pygame 播放已启动。")
        except pygame.error as e:
            print(f"ERROR: Pygame 播放错误: {e}")
            if self.root.winfo_exists(): self.update_status(f"播放错误: {e}", error=True)
        except Exception as e:
            # Catch other potential errors during load/play
            print(f"ERROR: 播放时发生未知错误: {e}")
            if self.root.winfo_exists(): self.update_status(f"播放错误: {e}", error=True)


    def _get_display_voice_name(self, full_voice_name):
        if not full_voice_name: return "未知"
        for dn, fn in self.voice_display_to_full_map.items():
            if fn == full_voice_name: return dn
        match = re.search(r", (.*Neural)\)$", full_voice_name)
        return match.group(1) if match else full_voice_name

    # --------------------------------------------------------------------------
    # 浮窗相关方法 (包含 SyntaxError 修复)
    # --------------------------------------------------------------------------
    def show_float_window(self, text):
        """在鼠标位置显示蓝色“音”字浮窗"""
        if self.float_window:
            try: self.float_window.destroy()
            except tk.TclError: pass
        self.destroy_generating_window(); self.destroy_ok_window()
        self._text_for_float_trigger = text
        self.float_window = tk.Toplevel(self.root)
        self.float_window.overrideredirect(True)
        x, y = self.last_mouse_pos
        self.float_window.geometry(f"50x50+{x + 10}+{y + 10}")
        self.float_window.attributes("-topmost", True)
        float_button = ctk.CTkButton( self.float_window, text="音", width=50, height=50, corner_radius=25, font=ctk.CTkFont(size=20, weight="bold"), fg_color="#1E90FF", hover_color="#1C86EE", text_color="white", command=self.trigger_generate_from_float )
        float_button.pack(fill="both", expand=True) # Ensure button fills the Toplevel

        # Cancel previous auto-close job if any
        if hasattr(self, '_float_window_close_job') and self._float_window_close_job:
            try: self.root.after_cancel(self._float_window_close_job)
            except: pass

        def auto_close():
            if self.float_window:
                try: self.float_window.destroy()
                except tk.TclError: pass
            self.float_window = None; self._float_window_close_job = None
        self._float_window_close_job = self.float_window.after(FLOAT_WINDOW_TIMEOUT * 1000, auto_close)

    def show_generating_window(self, position):
        """在指定位置显示绿色旋转浮窗"""
        self.destroy_float_window(); self.destroy_ok_window(); self.destroy_generating_window()
        self.generating_window = tk.Toplevel(self.root)
        self.generating_window.overrideredirect(True)
        x, y = position
        self.generating_window.geometry(f"50x50+{x + 10}+{y + 10}")
        self.generating_window.attributes("-topmost", True)
        self.generating_window_label = ctk.CTkButton( self.generating_window, text="/", width=50, height=50, corner_radius=25, font=ctk.CTkFont(size=20, weight="bold"), fg_color="#4CAF50", hover_color="#45a049", text_color="white", state="disabled" )
        self.generating_window_label.pack(fill="both", expand=True)
        self._animate_green_dot()

    def _animate_green_dot(self, char_index=0):
        """更新绿色浮窗的旋转字符"""
        if self.generating_window and self.generating_window.winfo_exists():
            chars = ["/", "-", "\\", "|"]
            char = chars[char_index % len(chars)]
            if self.generating_window_label: self.generating_window_label.configure(text=char)
            self.generating_animation_job = self.root.after(150, lambda: self._animate_green_dot(char_index + 1))
        else: self.generating_animation_job = None

    def destroy_generating_window(self):
        """安全地销毁绿色浮窗并取消动画"""
        if self.generating_animation_job:
            try: self.root.after_cancel(self.generating_animation_job)
            except Exception as e: pass # print(f"DEBUG: Error cancelling generating animation job: {e}")
            self.generating_animation_job = None
        if self.generating_window:
            try: self.generating_window.destroy()
            except tk.TclError: pass
            except Exception as e: pass # print(f"DEBUG: Error destroying generating window: {e}")
            self.generating_window = None; self.generating_window_label = None

    def destroy_float_window(self):
        """安全地销毁蓝色浮窗并取消自动关闭计时器"""
        if hasattr(self, '_float_window_close_job') and self._float_window_close_job:
            try: self.root.after_cancel(self._float_window_close_job)
            except Exception as e: pass # print(f"DEBUG: Error cancelling float window close job: {e}")
            self._float_window_close_job = None
        if self.float_window:
            try: self.float_window.destroy()
            except tk.TclError: pass
            except Exception as e: pass # print(f"DEBUG: Error destroying float window: {e}")
            self.float_window = None

    def destroy_ok_window(self):
        """安全地销毁红色 OK 浮窗并取消自动关闭计时器"""
        if hasattr(self, '_ok_window_close_job') and self._ok_window_close_job:
            try: self.root.after_cancel(self._ok_window_close_job)
            except Exception as e: pass # print(f"DEBUG: Error cancelling ok window close job: {e}")
            self._ok_window_close_job = None
        if self.ok_window:
            try: self.ok_window.destroy()
            except tk.TclError: pass
            except Exception as e: pass # print(f"DEBUG: Error destroying ok window: {e}")
            self.ok_window = None

    # <<<<<<< CORRECTED SyntaxError >>>>>>>>>
    def show_ok_window(self, position=None):
        """在指定位置 (或最后记录的鼠标位置) 显示 'OK' 浮窗"""
        self.destroy_ok_window(); self.destroy_generating_window() # Destroy others first
        self.ok_window = tk.Toplevel(self.root)
        self.ok_window.overrideredirect(True)
        pos = position or self.last_mouse_pos; x, y = pos
        self.ok_window.geometry(f"50x50+{x + 10}+{y + 10}")
        self.ok_window.attributes("-topmost", True)
        ok_button = ctk.CTkButton( self.ok_window, text="OK", width=50, height=50, corner_radius=25, font=ctk.CTkFont(size=20, weight="bold"), fg_color="#DC143C", hover_color="#B22222", text_color="white", command=self.destroy_ok_window )
        ok_button.pack(fill="both", expand=True)

        # Cancel previous auto-close if any
        if hasattr(self, '_ok_window_close_job') and self._ok_window_close_job:
            try:
                self.root.after_cancel(self._ok_window_close_job)
            except Exception as e:
                # print(f"DEBUG: Error cancelling previous ok window job: {e}") # Optional debug
                pass
            # Reset job id even if cancel fails (might happen if job already ran)
            self._ok_window_close_job = None

        def auto_close():
            # Check if window still exists before trying to destroy
            # Using self.ok_window directly, destroy_ok_window handles internal check
            if self.ok_window:
                 self.destroy_ok_window() # Call the safe destroy method
            # Ensure job id is reset after execution or cancellation attempt
            self._ok_window_close_job = None

        self._ok_window_close_job = self.ok_window.after(MOUSE_TIP_TIMEOUT * 1000, auto_close)


    def trigger_generate_from_float(self):
        """处理浮窗按钮点击事件：使用之前存储的文本，显示绿色窗口，开始生成"""
        text = getattr(self, '_text_for_float_trigger', None)
        if not text: print("ERROR: No text found for float trigger."); self.destroy_float_window(); return
        print(f"通过浮窗触发生成: {text[:50]}...")
        voice = self.current_full_voice_name
        if not voice: self.update_status("错误：请选择一个声音", error=True, duration=5); self.destroy_float_window(); return
        rate_str = f"{self.rate_slider_var.get():+}%"
        volume_str = f"{self.volume_slider_var.get():+}%"
        pitch_str = "+0Hz"
        float_pos = self.last_mouse_pos
        self.destroy_float_window()
        self.show_generating_window(float_pos)

        def on_float_complete(path, error_msg=None):
            self.destroy_generating_window() # Destroy green window regardless of outcome
            copy_enabled = self.copy_to_clipboard_var.get()
            play_enabled = self.play_audio_var.get()

            if path:
                print("音频生成完成:", path)
                print(f"DEBUG: Autoplay enabled (float)? {play_enabled}")
                print(f"DEBUG: Autocopy enabled (float)? {copy_enabled}")
                if play_enabled:
                    self.play_audio_pygame(path) # Use pygame player
                if copy_enabled:
                    copy_file_to_clipboard(path)
                    if self.root.winfo_exists(): self.show_ok_window(float_pos)
            else:
                err_str = f"音频生成失败: {error_msg or '未知错误'}"
                print(err_str)
                if self.root.winfo_exists(): self.update_status(err_str, error=True) # Keep error visible

            # Manage files after operation
            manage_audio_files()

        generate_audio(text, voice, rate_str, volume_str, pitch_str, on_float_complete)

    # --------------------------------------------------------------------------
    # 剪贴板监控方法 (轮询逻辑 - 修正版)
    # --------------------------------------------------------------------------
    def toggle_select_to_audio(self):
        global clipboard_monitor_active
        if self.select_to_audio_switch.get():
            if not clipboard_monitor_active: self.start_clipboard_monitor()
        else: self.stop_clipboard_monitor()
        self.save_settings()

    def start_clipboard_monitor(self):
        global clipboard_monitor_active, clipboard_polling_thread, previous_clipboard_poll_content
        if clipboard_polling_thread and clipboard_polling_thread.is_alive(): print("剪贴板监控已在运行"); return

        clipboard_monitor_active = True
        print("启动剪贴板监控 (轮询)...")
        self.update_status("剪贴板监控已启用", duration=5)
        # Initialize previous content to current content to avoid immediate trigger
        try:
             previous_clipboard_poll_content = pyperclip.paste()
             print(f"DEBUG: Initial clipboard content set: {previous_clipboard_poll_content[:50]}...")
        except Exception as e:
             print(f"DEBUG: Error getting initial paste for monitor start: {e}")
             previous_clipboard_poll_content = "" # Fallback

        def poll_clipboard():
            global clipboard_monitor_active, previous_clipboard_poll_content
            print("DEBUG: Clipboard polling thread started.")

            while clipboard_monitor_active:
                current_text = None
                try:
                    current_text = pyperclip.paste() # Get current clipboard content

                    # Check if content is new, not None, not just whitespace
                    if current_text is not None and current_text.strip() and current_text != previous_clipboard_poll_content:
                        sanitized = sanitize_text(current_text)
                        if sanitized:
                            print(f"检测到新的剪贴板内容: {sanitized[:50]}...")
                            # Update previous content *before* triggering UI
                            prev_content_before_trigger = previous_clipboard_poll_content # Store for debug if needed
                            previous_clipboard_poll_content = current_text
                            # Trigger float window in main thread
                            if self.root.winfo_exists():
                                self.root.after(0, self._trigger_float_from_poll, sanitized)
                        else:
                            # Update previous even if sanitized is empty but original wasn't
                            previous_clipboard_poll_content = current_text
                    # If content didn't change but *was* valid text, ensure previous is updated
                    elif current_text is not None:
                         previous_clipboard_poll_content = current_text
                    # If current_text is None (e.g., clipboard cleared or non-text), update previous
                    elif current_text is None:
                        previous_clipboard_poll_content = None

                    time.sleep(0.5) # Polling interval

                except pyperclip.PyperclipException as e:
                     print(f"剪贴板访问错误 (忽略): {e}")
                     # Avoid false triggers after error resolves by setting previous to current state
                     previous_clipboard_poll_content = current_text
                     time.sleep(1)
                except Exception as e:
                    print(f"剪贴板监控错误: {e}")
                    previous_clipboard_poll_content = current_text # Update on other errors too
                    time.sleep(1)

            print("剪贴板监控线程已停止。")

        clipboard_polling_thread = threading.Thread(target=poll_clipboard, daemon=True)
        clipboard_polling_thread.start()

    def _trigger_float_from_poll(self, text_to_show):
        """在主线程中获取鼠标位置并显示浮窗"""
        if not clipboard_monitor_active or not self.root.winfo_exists(): return
        try:
            self.last_mouse_pos = (self.root.winfo_pointerx(), self.root.winfo_pointery())
            print(f"轮询检测到变化，鼠标位置: {self.last_mouse_pos}")
            self.show_float_window(text_to_show)
        except Exception as e: print(f"Error triggering float window from poll: {e}")

    def stop_clipboard_monitor(self):
        """停止剪贴板轮询线程"""
        global clipboard_monitor_active, clipboard_polling_thread
        if not clipboard_monitor_active: print("剪贴板监控未运行"); return
        print("正在停止剪贴板监控...")
        clipboard_monitor_active = False
        clipboard_polling_thread = None # Allow thread to exit naturally
        if self.root.winfo_exists():
            self.root.after(0, self.destroy_float_window)
            self.root.after(0, self.destroy_generating_window)
            self.root.after(0, self.destroy_ok_window)
        self.update_status("剪贴板监控已禁用", duration=3)

    # --------------------------------------------------------------------------
    # 窗口关闭处理 (使用 pygame 关闭)
    # --------------------------------------------------------------------------
    def on_closing(self):
        """处理窗口关闭事件"""
        print("窗口关闭...")
        self.stop_clipboard_monitor()
        self.save_settings()
        # Stop pygame playback and quit pygame
        try:
            if pygame.mixer.get_init():
                 print("停止 Pygame mixer...")
                 pygame.mixer.music.stop(); pygame.mixer.quit()
            if pygame.get_init():
                 print("退出 Pygame..."); pygame.quit()
        except Exception as e: print(f"关闭 pygame 时出错: {e}")
        # Destroy Tkinter window
        try:
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    try: widget.destroy()
                    except tk.TclError: pass
            self.root.destroy()
        except tk.TclError as e: print(f"Error during root destroy: {e}")

# ==============================================================================
# 程序入口点
# ==============================================================================
if __name__ == "__main__":
    try: # Set DPI awareness
        if sys.platform == "win32": ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e: print(f"设置 DPI 感知失败: {e}")

    root = ctk.CTk()
    app = EdgeTTSApp(root) # Pygame is initialized inside EdgeTTSApp
    try: root.mainloop()
    except KeyboardInterrupt: print("用户中断程序。"); app.on_closing()
    finally: print("程序退出。")