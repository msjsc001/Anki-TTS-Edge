# ==============================================================================
# 导入所需库  1
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
# 依赖检查与导入
# ==============================================================================
# 检查必要的第三方库是否已安装
def check_dependencies():
    """检查所有依赖库是否安装"""
    dependencies = {
        "customtkinter": "pip install customtkinter",
        "edge_tts": "pip install edge-tts",  # 用于调用 Edge TTS 服务
        "pyperclip": "pip install pyperclip",  # 用于剪贴板操作
        "playsound": "pip install playsound",  # 用于播放音频
        "pynput": "pip install pynput",        # 用于监听鼠标事件 (浮窗定位)
        "win32clipboard": "pip install pywin32",  # 用于复制文件到剪贴板
        "win32con": "pip install pywin32"         # 用于复制文件到剪贴板
    }
    missing = []
    checked_pywin32 = False
    for module, install_cmd in dependencies.items():
        try:
            # 特殊处理 edge_tts (检查子模块)
            if module == "edge_tts":
                import edge_tts.communicate
            # 特殊处理 pywin32 (只需检查一次)
            elif module.startswith("win32"):
                if not checked_pywin32:
                    __import__("win32clipboard")
                    checked_pywin32 = True
            else:
                __import__(module)
        except ImportError:
            # 如果是 pywin32 缺失，只添加一次安装命令
            if module.startswith("win32"):
                if not checked_pywin32:
                    missing.append((module, install_cmd))
                    checked_pywin32 = True  # 标记已检查（虽然失败）
            else:
                missing.append((module, install_cmd))
    
    if missing:
        print("以下依赖库未安装：")
        install_cmds = set()
        for module, install_cmd in missing:
            print(f"- {module}")
            install_cmds.add(install_cmd)
        print("\n请确保在激活的虚拟环境 (.venv) 中安装以上依赖库后重新运行脚本。")
        print(f"建议安装命令: {' '.join(install_cmds)}")
        sys.exit(1)
    else:
        print("所有依赖库已安装！")

# 执行依赖检查
check_dependencies()

# 导入检查通过的库
import customtkinter as ctk  # 自定义 Tkinter 界面库
import pyperclip            # 剪贴板操作
from playsound import playsound  # 播放声音
from pynput import mouse         # 鼠标监听
import win32clipboard       # Windows 剪贴板 API
import win32con             # Windows 常量
import edge_tts             # Edge TTS 核心库
from edge_tts import VoicesManager  # Edge TTS 声音管理器

# ==============================================================================
# 全局配置变量
# ==============================================================================
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "音频")              # 音频文件保存目录
DEFAULT_MAX_AUDIO_FILES = 20                                             # 默认最大缓存音频文件数量
DEFAULT_VOICE = "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)"  # 默认使用的声音 (完整名称)
DEFAULT_APPEARANCE_MODE = "light"                                        # 默认外观模式
DEFAULT_CUSTOM_COLOR = "#1F6AA5" # 默认自定义颜色 (CustomTkinter 蓝色)
FLOAT_WINDOW_TIMEOUT = 2                                                 # 浮窗自动关闭时间 (秒)
MOUSE_TIP_TIMEOUT = 1                                                    # 鼠标提示 (OK 浮窗) 显示时间 (秒)
SETTINGS_FILE = "voice_settings.json"                                    # 配置文件名

# 确保音频目录存在，如果不存在则创建
os.makedirs(AUDIO_DIR, exist_ok=True)

# ==============================================================================
# 全局变量
# ==============================================================================
app = None                  # 指向 EdgeTTSApp 实例的全局引用
status_update_job = None  # 用于存储状态栏自动清除任务的 ID
clipboard_monitor_active = False  # 剪贴板监控线程活动状态标志

# ==============================================================================
# 模块 1：文本处理
# ==============================================================================
def sanitize_text(text):
    """清理文本，去除可能导致问题的特殊字符，并将多个空格合并为一个"""
    if not text:
        return ""
    text = re.sub(r"[^\w\s.,!?;:\"'()\[\]{}<>%&$@#*+-=/]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else ""

# ==============================================================================
# 模块 2：剪贴板操作
# ==============================================================================
def copy_file_to_clipboard(file_path):
    """将指定文件的路径复制到系统剪贴板"""
    try:
        class DROPFILES(ctypes.Structure):
            _fields_ = [("pFiles", wintypes.DWORD), ("pt", wintypes.POINT), ("fNC", wintypes.BOOL), ("fWide", wintypes.BOOL)]
        file_path = os.path.abspath(file_path)
        data = file_path.encode('utf-16-le') + b'\0\0'
        dropfiles = DROPFILES()
        dropfiles.pFiles = ctypes.sizeof(DROPFILES)
        dropfiles.fWide = True
        buffer_size = ctypes.sizeof(DROPFILES) + len(data)
        buffer = (ctypes.c_char * buffer_size)()
        ctypes.memmove(buffer, ctypes.byref(dropfiles), ctypes.sizeof(DROPFILES))
        ctypes.memmove(ctypes.byref(buffer, ctypes.sizeof(DROPFILES)), data, len(data))
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_HDROP, buffer) 
        win32clipboard.CloseClipboard()
        print(f"文件已复制到剪贴板: {file_path}")
        if app: app.update_status("文件路径已复制到剪贴板", duration=3)
    except Exception as e:
        print(f"复制文件到剪贴板失败: {e}")
        if app: app.update_status(f"复制文件失败: {e}", error=True)

# ==============================================================================
# 模块 3：声音列表获取
# ==============================================================================
async def get_available_voices_async():
    """异步获取所有可用的 Edge TTS 声音"""
    try:
        voices = await VoicesManager.create()
        raw_voices_list = voices.find() 
        voice_pattern = re.compile(r"^Microsoft Server Speech Text to Speech Voice \(([a-z]{2,3})-([A-Z]{2,}(?:-[A-Za-z]+)?), (.*Neural)\)$") 
        hierarchical_voices = {} 
        for v in raw_voices_list:
            full_name = v['Name'] 
            match = voice_pattern.match(full_name)
            if match:
                lang, region, name_part = match.groups() 
                if lang not in hierarchical_voices: hierarchical_voices[lang] = {}
                if region not in hierarchical_voices[lang]: hierarchical_voices[lang][region] = []
                hierarchical_voices[lang][region].append(full_name) 
            else:
                print(f"声音格式不匹配层级分类，跳过: {full_name}")
        for lang in hierarchical_voices:
            for region in hierarchical_voices[lang]:
                hierarchical_voices[lang][region].sort()
            hierarchical_voices[lang] = dict(sorted(hierarchical_voices[lang].items()))
        sorted_hierarchical_voices = {}
        if "zh" in hierarchical_voices: sorted_hierarchical_voices["zh"] = hierarchical_voices.pop("zh")
        if "en" in hierarchical_voices: sorted_hierarchical_voices["en"] = hierarchical_voices.pop("en")
        for lang in sorted(hierarchical_voices.keys()): sorted_hierarchical_voices[lang] = hierarchical_voices[lang]
        total_voices = sum(len(voices) for lang_data in sorted_hierarchical_voices.values() for voices in lang_data.values())
        print(f"获取到 {total_voices} 个声音，已按 语言->地区->名称 层级分类。")
        return sorted_hierarchical_voices 
    except Exception as e:
        print(f"获取声音列表失败: {e}")
        if app: app.update_status(f"获取声音列表失败: {e}", error=True)
        return {}

def refresh_voices_list():
    """启动一个后台线程来异步获取声音列表"""
    def run_async_get_voices():
        hierarchical_voice_data = {} 
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            hierarchical_voice_data = loop.run_until_complete(get_available_voices_async()) 
            loop.close()
        except Exception as e:
            print(f"运行异步获取声音任务时出错: {e}")
            if app: app.update_status(f"获取声音时出错: {e}", error=True)
        finally:
            if app and app.root.winfo_exists():
                app.root.after(0, app.update_voice_ui, hierarchical_voice_data) 
    threading.Thread(target=run_async_get_voices, daemon=True).start()

# ==============================================================================
# 模块 4：音频生成
# ==============================================================================
async def generate_audio_edge_tts_async(text, voice, rate, volume, pitch, output_path):
    """使用 edge-tts 库异步生成音频文件"""
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        await communicate.save(output_path)
        print(f"Edge TTS 音频生成成功: {output_path}")
        return output_path
    except Exception as e:
        print(f"Edge TTS 音频生成失败: {e}")
        return None

def generate_audio(text, voice, rate_str, volume_str, pitch_str, on_complete=None):
    """启动一个后台线程来异步生成音频"""
    text = sanitize_text(text)
    if not text:
        print("文本为空，无法生成音频")
        if app: app.update_status("错误：文本不能为空", error=True)
        if on_complete: on_complete(None, "文本为空") 
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_part_match = re.search(r", (.*Neural)\)$", voice) 
    safe_voice_part = re.sub(r'\W+', '', name_part_match.group(1)) if name_part_match else "UnknownVoice"
    filename = f"Anki-TTS-Edge_{safe_voice_part}_{timestamp}.mp3"
    output_path = os.path.join(AUDIO_DIR, filename)
    print(f"准备生成音频: voice='{voice}', rate='{rate_str}', volume='{volume_str}', pitch='{pitch_str}'")
    print(f"输出路径: {output_path}")
    if app: app.update_status(f"正在生成音频 (声音: {safe_voice_part})...", permanent=True, show_progress=True) 
    def run_async_in_thread():
        result_path = None; error_message = None
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            result_path = loop.run_until_complete(generate_audio_edge_tts_async(text, voice, rate_str, volume_str, pitch_str, output_path))
            loop.close()
            if not result_path: error_message = "Edge TTS 内部错误"
        except Exception as e:
            print(f"运行异步生成任务时出错: {e}"); error_message = str(e)
        finally:
            if app and app.root.winfo_exists(): 
                final_path = result_path if result_path else None
                final_error = error_message if not result_path else None
                app.root.after(0, on_complete, final_path, final_error) 
    threading.Thread(target=run_async_in_thread, daemon=True).start()

# ==============================================================================
# 模块 5：文件管理
# ==============================================================================
def manage_audio_files():
    """删除旧的音频文件，只保留最新的指定数量的文件"""
    try:
        max_files_str = app.max_files_entry.get() if app and hasattr(app, 'max_files_entry') else str(DEFAULT_MAX_AUDIO_FILES)
        max_files = int(max_files_str) if max_files_str.isdigit() else DEFAULT_MAX_AUDIO_FILES
        if not (1 <= max_files <= 50): max_files = DEFAULT_MAX_AUDIO_FILES
    except (ValueError, AttributeError): max_files = DEFAULT_MAX_AUDIO_FILES
    try:
        if not os.path.exists(AUDIO_DIR): return 
        files = sorted(
            [f for f in os.listdir(AUDIO_DIR) if f.endswith(".mp3")],
            key=lambda x: os.path.getctime(os.path.join(AUDIO_DIR, x))
        )
        while len(files) > max_files:
            file_to_remove = files.pop(0)
            file_path_to_remove = os.path.join(AUDIO_DIR, file_to_remove)
            try:
                os.remove(file_path_to_remove)
                print(f"删除旧音频文件: {file_to_remove}")
            except OSError as e: print(f"删除文件 {file_to_remove} 失败: {e}")
    except Exception as e: print(f"文件管理出错: {e}")

# ==============================================================================
# 模块 6：UI 主类 (EdgeTTSApp)
# ==============================================================================
class EdgeTTSApp:
    def __init__(self, root):
        """初始化应用程序 UI 和状态"""
        self.root = root
        self.root.title("Anki-TTS-Edge ✨")
        self.root.geometry("550x750") 
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing) 
        global app; app = self 
        
        # 存储声音数据
        self.voice_display_to_full_map = {} 
        self.hierarchical_voice_data = {} 
        self.current_full_voice_name = None 
        self.current_custom_color = None 

        # --- 加载设置 ---
        settings = self.load_settings()
        
        # --- 应用加载的主题和颜色 ---
        loaded_appearance_mode = settings.get("appearance_mode", DEFAULT_APPEARANCE_MODE)
        self.current_custom_color = settings.get("custom_theme_color", DEFAULT_CUSTOM_COLOR) 
        ctk.set_appearance_mode(loaded_appearance_mode) 

        # --- 创建主框架 ---
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20) 
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=0) 
        self.main_frame.grid_rowconfigure(1, weight=1) # 让包含 TabView 的行可扩展
        self.main_frame.grid_rowconfigure(2, weight=0) 
        self.main_frame.grid_rowconfigure(3, weight=0) 

        # --- 创建顶部：文本输入区域 ---
        self.text_input_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.text_input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15)) # 减少底部边距
        self.text_input_frame.grid_columnconfigure(0, weight=1)
        self.text_input_label = ctk.CTkLabel(self.text_input_frame, text="📝 输入文本:", font=ctk.CTkFont(size=14, weight="bold"))
        self.text_input_label.grid(row=0, column=0, sticky="w", pady=(0, 5)) # 减少底部边距
        self.text_input = ctk.CTkTextbox(self.text_input_frame, height=100, wrap="word", corner_radius=8, border_width=1) # 调整样式
        self.text_input.grid(row=1, column=0, sticky="nsew")

        # --- 创建中部：选项卡视图 ---
        self.tab_view = ctk.CTkTabview(self.main_frame, corner_radius=8) # 应用圆角
        self.tab_view.grid(row=1, column=0, sticky="nsew", pady=0) # 移除边距，让它填充

        # 添加选项卡
        self.tab_view.add("🔊 声音") # 简化名称
        self.tab_view.add("⚙️ 设置") # 合并设置项
        self.tab_view.add("🎨 外观") # 简化名称

        # --- 填充 "声音" 选项卡 (双列内联选择器) ---
        voice_tab = self.tab_view.tab("🔊 声音")
        voice_tab.grid_columnconfigure(0, weight=1) # 左列
        voice_tab.grid_columnconfigure(1, weight=1) # 右列
        voice_tab.grid_rowconfigure(1, weight=1) # 让声音列表行扩展 (重要)

        # 左侧框架
        self.left_voice_frame_outer = ctk.CTkFrame(voice_tab, fg_color="transparent")
        self.left_voice_frame_outer.grid(row=0, column=0, rowspan=2, padx=(0, 5), pady=5, sticky="nsew")
        self.left_voice_frame_outer.grid_rowconfigure(1, weight=1) # 让滚动框扩展
        self.language_filter_entry_left = ctk.CTkEntry(self.left_voice_frame_outer, placeholder_text="筛选语言 (如: zh)...")
        self.language_filter_entry_left.grid(row=0, column=0, padx=0, pady=(0, 5), sticky="ew")
        self.language_filter_entry_left.bind("<KeyRelease>", lambda e: self._filter_voices_inline('left'))
        self.inline_voice_list_frame_left = ctk.CTkScrollableFrame(self.left_voice_frame_outer, label_text="声音列表 1", height=150) # 设置初始高度
        self.inline_voice_list_frame_left.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        self.inline_voice_list_frame_left.grid_columnconfigure(0, weight=1) # 单列显示

        # 右侧框架
        self.right_voice_frame_outer = ctk.CTkFrame(voice_tab, fg_color="transparent")
        self.right_voice_frame_outer.grid(row=0, column=1, rowspan=2, padx=(5, 0), pady=5, sticky="nsew")
        self.right_voice_frame_outer.grid_rowconfigure(1, weight=1)
        self.language_filter_entry_right = ctk.CTkEntry(self.right_voice_frame_outer, placeholder_text="筛选语言 (如: en)...")
        self.language_filter_entry_right.grid(row=0, column=0, padx=0, pady=(0, 5), sticky="ew")
        self.language_filter_entry_right.bind("<KeyRelease>", lambda e: self._filter_voices_inline('right'))
        self.inline_voice_list_frame_right = ctk.CTkScrollableFrame(self.right_voice_frame_outer, label_text="声音列表 2", height=150)
        self.inline_voice_list_frame_right.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        self.inline_voice_list_frame_right.grid_columnconfigure(0, weight=1)

        # 加载保存的筛选条件
        saved_filter_left = settings.get("language_filter_left", "zh") # 默认筛选中文
        saved_filter_right = settings.get("language_filter_right", "en") # 默认筛选英文
        self.language_filter_entry_left.insert(0, saved_filter_left)
        self.language_filter_entry_right.insert(0, saved_filter_right)

        # 刷新按钮、语速、音量 (移到声音列表下方，跨列)
        controls_frame = ctk.CTkFrame(voice_tab, fg_color="transparent")
        controls_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        controls_frame.grid_columnconfigure(1, weight=1) # 让滑块列扩展

        self.refresh_button = ctk.CTkButton(controls_frame, text="🔄 刷新声音列表", 
                                          command=self.refresh_voices_ui,
                                          font=ctk.CTkFont(size=12))
        self.refresh_button.grid(row=0, column=0, columnspan=3, padx=0, pady=(0, 10), sticky="ew")

        self.rate_label = ctk.CTkLabel(controls_frame, text="语速:")
        self.rate_label.grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w") 
        self.rate_slider_var = ctk.IntVar(value=settings.get("rate", 0)) 
        self.rate_slider = ctk.CTkSlider(controls_frame, from_=-100, to=100, number_of_steps=40, variable=self.rate_slider_var, command=self.update_rate_label) 
        self.rate_slider.grid(row=1, column=1, padx=5, pady=5, sticky="ew") 
        self.rate_value_label = ctk.CTkLabel(controls_frame, text=f"{self.rate_slider_var.get():+}%", width=45) 
        self.rate_value_label.grid(row=1, column=2, padx=(5, 0), pady=5, sticky="w") 

        self.volume_label = ctk.CTkLabel(controls_frame, text="音量:")
        self.volume_label.grid(row=2, column=0, padx=(0, 5), pady=5, sticky="w") 
        self.volume_slider_var = ctk.IntVar(value=settings.get("volume", 0)) 
        self.volume_slider = ctk.CTkSlider(controls_frame, from_=-100, to=100, number_of_steps=40, variable=self.volume_slider_var, command=self.update_volume_label)
        self.volume_slider.grid(row=2, column=1, padx=5, pady=5, sticky="ew") 
        self.volume_value_label = ctk.CTkLabel(controls_frame, text=f"{self.volume_slider_var.get():+}%", width=45) 
        self.volume_value_label.grid(row=2, column=2, padx=(5, 0), pady=5, sticky="w") 

        # --- 填充 "设置" 选项卡 ---
        settings_tab = self.tab_view.tab("⚙️ 设置")
        settings_tab.grid_columnconfigure(0, weight=1) # 让列扩展

        # 输出与缓存框架
        output_cache_frame = ctk.CTkFrame(settings_tab)
        output_cache_frame.pack(fill="x", padx=10, pady=10)
        output_cache_frame.grid_columnconfigure(1, weight=1) # 让第二列扩展
        output_cache_label = ctk.CTkLabel(output_cache_frame, text="输出与缓存", font=ctk.CTkFont(weight="bold"))
        output_cache_label.grid(row=0, column=0, columnspan=3, pady=(5, 10), padx=10, sticky="w") 
        self.copy_to_clipboard_var = ctk.BooleanVar(value=settings.get("copy_path_enabled", True))
        self.copy_to_clipboard_switch = ctk.CTkSwitch(output_cache_frame, text="🔗 复制文件路径", variable=self.copy_to_clipboard_var, onvalue=True, offvalue=False)
        self.copy_to_clipboard_switch.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.play_audio_var = ctk.BooleanVar(value=settings.get("autoplay_enabled", False))
        self.play_audio_switch = ctk.CTkSwitch(output_cache_frame, text="▶️ 自动播放", variable=self.play_audio_var, onvalue=True, offvalue=False)
        self.play_audio_switch.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.max_files_label = ctk.CTkLabel(output_cache_frame, text="🔢 最大缓存数:")
        self.max_files_label.grid(row=2, column=0, padx=(10, 5), pady=(5, 10), sticky="w") 
        self.max_files_entry = ctk.CTkEntry(output_cache_frame, width=60)
        self.max_files_entry.insert(0, str(settings.get("max_audio_files", DEFAULT_MAX_AUDIO_FILES))) 
        self.max_files_entry.grid(row=2, column=1, padx=5, pady=(5, 10), sticky="w") 

        # 剪贴板功能框架
        clipboard_frame = ctk.CTkFrame(settings_tab)
        clipboard_frame.pack(fill="x", padx=10, pady=(0, 10))
        clipboard_frame.grid_columnconfigure(0, weight=1)
        clipboard_label = ctk.CTkLabel(clipboard_frame, text="剪贴板功能", font=ctk.CTkFont(weight="bold"))
        clipboard_label.grid(row=0, column=0, columnspan=2, pady=(5, 10), padx=10, sticky="w") 
        self.select_to_audio_var = ctk.BooleanVar(value=settings.get("monitor_enabled", False))
        self.select_to_audio_switch = ctk.CTkSwitch(clipboard_frame, text="🖱️ 启用复制生音频浮窗", variable=self.select_to_audio_var, command=self.toggle_select_to_audio, onvalue=True, offvalue=False)
        self.select_to_audio_switch.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="w") 

        # --- 填充 "外观" 选项卡 ---
        appearance_tab = self.tab_view.tab("🎨 外观")
        appearance_tab.grid_columnconfigure(1, weight=1) 

        # 亮暗模式切换
        self.appearance_label = ctk.CTkLabel(appearance_tab, text="界面主题:")
        self.appearance_label.grid(row=0, column=0, padx=(15, 5), pady=15, sticky="w")
        self.appearance_mode_segmented_button = ctk.CTkSegmentedButton(
            appearance_tab, 
            values=["浅色模式", "深色模式"],
            command=self._change_appearance_mode
        )
        self.appearance_mode_segmented_button.grid(row=0, column=1, columnspan=3, padx=5, pady=15, sticky="ew") 
        initial_mode_text = "浅色模式" if loaded_appearance_mode == "light" else "深色模式"
        self.appearance_mode_segmented_button.set(initial_mode_text)

        # 自定义主颜色
        self.custom_color_label = ctk.CTkLabel(appearance_tab, text="自定义主色 (Hex):")
        self.custom_color_label.grid(row=1, column=0, padx=(15, 5), pady=(5, 15), sticky="w")
        self.custom_color_entry = ctk.CTkEntry(appearance_tab, placeholder_text="#1F6AA5")
        self.custom_color_entry.grid(row=1, column=1, padx=5, pady=(5, 15), sticky="ew")
        self.custom_color_entry.insert(0, self.current_custom_color or "") 
        self.pick_color_button = ctk.CTkButton(appearance_tab, text="🎨", width=30, command=self._pick_custom_color)
        self.pick_color_button.grid(row=1, column=2, padx=(0, 5), pady=(5, 15), sticky="w")
        self.apply_color_button = ctk.CTkButton(appearance_tab, text="应用颜色", command=self._apply_custom_color)
        self.apply_color_button.grid(row=1, column=3, padx=(0, 15), pady=(5, 15), sticky="e")


        # --- 创建底部：操作按钮 & 状态栏 ---
        self.bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.bottom_frame.grid(row=2, column=0, sticky="ew", pady=(15, 5)) 
        self.bottom_frame.grid_columnconfigure(0, weight=1)

        # “生成音频”按钮
        button_text = "生成音频" 
        self.generate_button = ctk.CTkButton(
            self.bottom_frame, 
            text=button_text, 
            command=self.generate_audio_manual, 
            height=40, 
            font=ctk.CTkFont(size=16, weight="bold"), 
            corner_radius=10 
        )
        self.generate_button.grid(row=0, column=0, pady=(0, 15), sticky="") 
       
        # 状态栏框架
        self.status_bar_frame = ctk.CTkFrame(self.main_frame, height=25, corner_radius=0)
        self.status_bar_frame.grid(row=3, column=0, sticky="ew")
        self.status_bar_frame.grid_columnconfigure(0, weight=1) 
        self.status_bar_frame.grid_columnconfigure(1, weight=0) 
        # 状态标签
        self.status_label = ctk.CTkLabel(self.status_bar_frame, text="✅ 准备就绪", anchor="w", font=ctk.CTkFont(size=12)) 
        self.status_label.grid(row=0, column=0, sticky="ew", padx=(10, 5))
        # 进度条
        self.progress_bar = ctk.CTkProgressBar(self.status_bar_frame, height=10, width=100, corner_radius=5)
        self.progress_bar.set(0)
        self.progress_bar.grid_remove() 

        # --- 初始化浮窗相关变量 ---
        self.float_window = None 
        self.ok_window = None    
        self.clipboard_thread = None 
        self.last_mouse_pos = (0, 0) 

        # --- 初始化操作 ---
        self._apply_custom_color(save=False) # 应用加载的或默认的自定义颜色
        self.refresh_voices_ui() # 启动时刷新声音列表
        # 如果设置中启用了剪贴板监控，则启动它
        if self.select_to_audio_var.get():
            self.start_clipboard_monitor()

    # --------------------------------------------------------------------------
    # UI 更新与状态管理方法
    # --------------------------------------------------------------------------
    def update_status(self, message, duration=0, error=False, permanent=False, show_progress=False):
        """更新状态栏信息。"""
        global status_update_job
        def _update(): 
            global status_update_job
            if status_update_job:
                try: self.status_label.after_cancel(status_update_job)
                except: pass
                status_update_job = None
            
            status_text = message
            label_fg_color = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
            text_color = label_fg_color

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
                progress_bar_color = self.current_custom_color or ctk.ThemeManager.theme["CTkProgressBar"]["progress_color"]
                self.progress_bar.configure(mode="indeterminate", progress_color=progress_bar_color) 
                self.progress_bar.start()
            else:
                self.progress_bar.stop()
                self.progress_bar.grid_remove() 
            if not permanent and duration > 0:
                status_update_job = self.status_label.after(duration * 1000, lambda: self.update_status("准备就绪"))
        
        if threading.current_thread() is not threading.main_thread():
            if self.root.winfo_exists(): self.root.after(0, _update)
        else: 
            _update()

    def update_rate_label(self, value):
        """更新语速滑块旁边的百分比标签"""
        val = int(value)
        self.rate_value_label.configure(text=f"{val:+}%")

    def update_volume_label(self, value):
        """更新音量滑块旁边的百分比标签"""
        val = int(value)
        self.volume_value_label.configure(text=f"{val:+}%")

    def refresh_voices_ui(self):
        """刷新声音列表的 UI 反馈：禁用按钮，显示加载状态，然后调用后台刷新"""
        self.update_status("正在获取声音列表...", permanent=True) 
        self.refresh_button.configure(state="disabled") 
        # 清空两个列表并显示加载提示
        for frame in [self.inline_voice_list_frame_left, self.inline_voice_list_frame_right]:
            for widget in frame.winfo_children():
                widget.destroy()
            loading_label = ctk.CTkLabel(frame, text="正在加载...", text_color="gray")
            loading_label.pack(pady=20) # 使用 pack 居中显示
        # 调用后台线程刷新声音列表
        refresh_voices_list()
        
    def update_voice_ui(self, hierarchical_voice_data):
        """
        (在主线程中调用) 使用获取到的声音数据更新声音数据存储和两个内联列表。
        """
        print("DEBUG: update_voice_ui called")
        self.hierarchical_voice_data = hierarchical_voice_data 

        self.refresh_button.configure(state="normal")
        self.voice_display_to_full_map.clear()

        if not hierarchical_voice_data:
            print("DEBUG: No voice data received.")
            for frame in [self.inline_voice_list_frame_left, self.inline_voice_list_frame_right]:
                for widget in frame.winfo_children(): widget.destroy()
                error_label = ctk.CTkLabel(frame, text="获取失败", text_color="red")
                error_label.pack(pady=20)
            self.update_status("获取声音列表失败", error=True)
            return

        name_extract_pattern = re.compile(r", (.*Neural)\)$") 
        for lang_data in hierarchical_voice_data.values():
            for region_voices in lang_data.values():
                for full_name in region_voices:
                    name_part_match = name_extract_pattern.search(full_name)
                    display_name = name_part_match.group(1) if name_part_match else full_name
                    original_display_name = display_name
                    count = 1
                    while display_name in self.voice_display_to_full_map:
                        display_name = f"{original_display_name}_{count}"
                        count += 1
                    self.voice_display_to_full_map[display_name] = full_name

        if not self.current_full_voice_name or self.current_full_voice_name not in self.voice_display_to_full_map.values():
            if DEFAULT_VOICE in self.voice_display_to_full_map.values():
                self.current_full_voice_name = DEFAULT_VOICE
            else:
                available_full_names = list(self.voice_display_to_full_map.values())
                self.current_full_voice_name = available_full_names[0] if available_full_names else None

        # 更新两个列表
        self._populate_inline_voice_list('left') 
        self._populate_inline_voice_list('right') 

        print(f"DEBUG: Voice UI updated. Current Voice: {self.current_full_voice_name}")
        self.update_status("声音列表已更新", duration=3)

    # --------------------------------------------------------------------------
    # 内联声音选择器方法 (双列版本)
    # --------------------------------------------------------------------------
    def _populate_inline_voice_list(self, side):
        """填充指定侧的内联声音列表，支持过滤"""
        if side == 'left':
            frame = self.inline_voice_list_frame_left
            filter_entry = self.language_filter_entry_left
        elif side == 'right':
            frame = self.inline_voice_list_frame_right
            filter_entry = self.language_filter_entry_right
        else:
            return # 无效侧

        filter_term = filter_entry.get() if hasattr(self, f'language_filter_entry_{side}') else ""
        
        for widget in frame.winfo_children():
            widget.destroy()

        # 使用单列布局更清晰
        row_count = 0
        filter_codes = [code.strip().lower() for code in re.split(r'[,\s]+', filter_term) if code.strip()]
        sorted_voices = sorted(self.voice_display_to_full_map.items())

        found_match = False
        for display_name, full_name in sorted_voices:
            apply_filter = len(filter_codes) > 0
            match_filter = False
            if apply_filter:
                lang_match = re.search(r'\(([a-z]{2,3})-', full_name)
                lang_code = lang_match.group(1).lower() if lang_match else ""
                if lang_code in filter_codes:
                    match_filter = True
            
            if apply_filter and not match_filter:
                continue

            found_match = True 

            is_selected = (full_name == self.current_full_voice_name)
            # 使用当前自定义颜色或默认按钮颜色
            btn_fg_color = self.current_custom_color or ctk.ThemeManager.theme["CTkButton"]["fg_color"]
            btn_hover_color = self._calculate_hover_color(btn_fg_color) # 基于 fg_color 计算悬停色
            
            # 确定文本颜色以确保对比度
            text_color_normal = ctk.ThemeManager.theme["CTkLabel"]["text_color"] # 未选中时的默认文本色
            text_color_selected = self._get_contrasting_text_color(btn_fg_color) # 选中时的反色

            btn = ctk.CTkButton(
                frame,
                text=display_name,
                anchor="w",
                fg_color = btn_fg_color if is_selected else "transparent", # 选中时用主色，否则透明
                hover_color= btn_hover_color, 
                text_color = text_color_selected if is_selected else text_color_normal, 
                command=lambda fn=full_name: self._select_voice_inline(fn)
            )
            btn.grid(row=row_count, column=0, padx=5, pady=2, sticky="ew") # 单列显示，减少垂直间距
            row_count += 1
        
        if not found_match:
             no_result_label = ctk.CTkLabel(frame, text="无匹配声音", text_color="gray")
             no_result_label.grid(row=0, column=0, pady=20)

    def _filter_voices_inline(self, side):
        """根据指定侧的语言筛选框内容过滤声音列表并保存筛选条件"""
        self._populate_inline_voice_list(side) 
        self.save_settings() 

    def _select_voice_inline(self, full_name):
        """处理内联声音按钮点击事件"""
        if self.current_full_voice_name != full_name:
            self.current_full_voice_name = full_name 
            print(f"DEBUG _select_voice_inline: Selected {full_name}") 
            # 更新两个列表的高亮状态
            self._populate_inline_voice_list('left') 
            self._populate_inline_voice_list('right')
            self.save_settings() # 保存选择

    # --------------------------------------------------------------------------
    # 主题与颜色切换方法
    # --------------------------------------------------------------------------
    def _change_appearance_mode(self, selected_value):
        """处理外观模式切换按钮的事件"""
        mode_map = {"浅色模式": "light", "深色模式": "dark"}
        new_mode = mode_map.get(selected_value, DEFAULT_APPEARANCE_MODE) 
        print(f"切换外观模式到: {new_mode}")
        ctk.set_appearance_mode(new_mode)
        self._apply_custom_color(save=True) # 切换模式后也应用并保存颜色

    def _pick_custom_color(self):
        """打开颜色选择器让用户选择颜色"""
        initial_color = self.custom_color_entry.get() or self.current_custom_color or DEFAULT_CUSTOM_COLOR
        chosen_color = colorchooser.askcolor(title="选择主颜色", initialcolor=initial_color)
        
        if chosen_color and chosen_color[1]: 
            hex_color = chosen_color[1]
            self.custom_color_entry.delete(0, tk.END)
            self.custom_color_entry.insert(0, hex_color)
            self._apply_custom_color() # 选择后立即应用

    def _apply_custom_color(self, save=True):
        """应用自定义颜色到关键控件并可选择保存"""
        new_color_hex = self.custom_color_entry.get().strip()
        
        if not re.match(r"^#[0-9a-fA-F]{6}$", new_color_hex):
            if new_color_hex: 
                 messagebox.showerror("无效颜色", f"请输入有效的 6 位十六进制颜色代码 (例如 #FF5733)，而不是 '{new_color_hex}'")
            self.current_custom_color = DEFAULT_CUSTOM_COLOR 
            self.custom_color_entry.delete(0, tk.END)
            self.custom_color_entry.insert(0, self.current_custom_color)
            new_color_hex = self.current_custom_color 
            save = False 
        else:
             self.current_custom_color = new_color_hex 

        print(f"应用自定义颜色: {self.current_custom_color}")
        button_hover_color = self._calculate_hover_color(self.current_custom_color) 

        # --- 应用到关键控件 ---
        button_elements = [getattr(self, name, None) for name in ['generate_button', 'refresh_button', 'apply_color_button', 'pick_color_button']]
        for btn in button_elements:
             if btn: btn.configure(fg_color=self.current_custom_color, hover_color=button_hover_color)

        switch_elements = [getattr(self, name, None) for name in ['copy_to_clipboard_switch', 'play_audio_switch', 'select_to_audio_switch']]
        for switch in switch_elements:
             if switch: switch.configure(progress_color=self.current_custom_color)

        slider_elements = [getattr(self, name, None) for name in ['rate_slider', 'volume_slider']]
        for slider in slider_elements:
             if slider: slider.configure(button_color=self.current_custom_color, progress_color=self.current_custom_color, button_hover_color=button_hover_color)
            
        if hasattr(self, 'progress_bar'):
             progress_bar_color = self.current_custom_color or ctk.ThemeManager.theme["CTkProgressBar"]["progress_color"]
             self.progress_bar.configure(progress_color=progress_bar_color)

        if hasattr(self, 'tab_view'):
             self.tab_view.configure(segmented_button_selected_color=self.current_custom_color, segmented_button_selected_hover_color=button_hover_color)
             
        if hasattr(self, 'appearance_mode_segmented_button'):
             self.appearance_mode_segmented_button.configure(selected_color=self.current_custom_color, selected_hover_color=button_hover_color)

        # 重新填充两个声音列表以应用高亮和文本颜色
        self._populate_inline_voice_list('left')
        self._populate_inline_voice_list('right')

        if save:
            self.save_settings() 

    def _calculate_hover_color(self, hex_color):
        """简单计算悬停颜色 (比原色稍暗)"""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            hover_r = max(0, r - 20)
            hover_g = max(0, g - 20)
            hover_b = max(0, b - 20)
            return f"#{hover_r:02x}{hover_g:02x}{hover_b:02x}"
        except:
            default_hover = ctk.ThemeManager.theme["CTkButton"]["hover_color"]
            return default_hover[ctk.get_appearance_mode() == 'dark'] if isinstance(default_hover, (list, tuple)) else default_hover


    def _get_contrasting_text_color(self, bg_hex_color):
        """根据背景色计算对比度高的文本颜色 (黑或白)"""
        try:
            bg_hex_color = bg_hex_color.lstrip('#')
            r, g, b = tuple(int(bg_hex_color[i:i+2], 16) for i in (0, 2, 4))
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return "#000000" if brightness > 128 else "#FFFFFF" 
        except:
            # 确保返回当前模式下的默认文本颜色
            default_text_color = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
            return default_text_color[ctk.get_appearance_mode() == 'dark'] if isinstance(default_text_color, (list, tuple)) else default_text_color


    # --------------------------------------------------------------------------
    # 设置加载与保存 (修改)
    # --------------------------------------------------------------------------
    def load_settings(self):
        """从 JSON 文件加载应用程序设置"""
        default_settings = {
            "copy_path_enabled": True,
            "autoplay_enabled": False,
            "monitor_enabled": False,
            "max_audio_files": DEFAULT_MAX_AUDIO_FILES,
            "selected_voice": DEFAULT_VOICE, 
            "rate": 0, 
            "volume": 0,
            "appearance_mode": DEFAULT_APPEARANCE_MODE,
            "language_filter_left": "zh", # 左侧筛选默认中文
            "language_filter_right": "en", # 右侧筛选默认英文
            "custom_theme_color": DEFAULT_CUSTOM_COLOR 
        }
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    merged_settings = default_settings.copy()
                    merged_settings.update(settings) 
                    self.current_full_voice_name = merged_settings.get("selected_voice", DEFAULT_VOICE)
                    loaded_color = merged_settings.get("custom_theme_color", DEFAULT_CUSTOM_COLOR)
                    if not re.match(r"^#[0-9a-fA-F]{6}$", loaded_color):
                        print(f"警告：加载的自定义颜色 '{loaded_color}' 无效，将使用默认颜色。")
                        merged_settings["custom_theme_color"] = DEFAULT_CUSTOM_COLOR
                    return merged_settings 
        except (json.JSONDecodeError, IOError, Exception) as e:
            print(f"加载设置失败: {e}")
        self.current_full_voice_name = DEFAULT_VOICE 
        return default_settings

    def save_settings(self):
        """将当前应用程序设置保存到 JSON 文件"""
        try:
            max_files_val = int(self.max_files_entry.get())
            if not (1 <= max_files_val <= 50):
                 max_files_val = DEFAULT_MAX_AUDIO_FILES
        except ValueError:
             max_files_val = DEFAULT_MAX_AUDIO_FILES
             
        settings_to_save = {
            "selected_voice": self.current_full_voice_name, 
            "copy_path_enabled": self.copy_to_clipboard_var.get(),
            "autoplay_enabled": self.play_audio_var.get(),
            "monitor_enabled": self.select_to_audio_var.get(),
            "max_audio_files": max_files_val, 
            "rate": self.rate_slider_var.get(), 
            "volume": self.volume_slider_var.get(),
            "appearance_mode": ctk.get_appearance_mode().lower(),
            "language_filter_left": self.language_filter_entry_left.get() if hasattr(self, 'language_filter_entry_left') else "zh", 
            "language_filter_right": self.language_filter_entry_right.get() if hasattr(self, 'language_filter_entry_right') else "en",
            "custom_theme_color": self.current_custom_color or DEFAULT_CUSTOM_COLOR 
        }
        
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings_to_save, f, ensure_ascii=False, indent=4)
            print("设置已保存。")
        except (IOError, Exception) as e:
            print(f"保存设置失败: {e}")


    # --------------------------------------------------------------------------
    # 音频生成与处理方法 (无需修改)
    # --------------------------------------------------------------------------
    def generate_audio_manual(self):
        """处理“生成音频”按钮点击事件"""
        text = self.text_input.get("1.0", "end").strip() 
        if not text:
            self.update_status("错误：请输入文本", error=True, duration=5)
            return
        voice = self.current_full_voice_name 
        if not voice: 
            self.update_status("错误：请选择一个声音", error=True, duration=5) 
            return
        rate_val = self.rate_slider_var.get()
        volume_val = self.volume_slider_var.get()
        rate_str = f"{rate_val:+}%"
        volume_str = f"{volume_val:+}%"
        pitch_str = "+0Hz" 
        self.generate_with_animation(text, voice, rate_str, volume_str, pitch_str)

    def generate_with_animation(self, text, voice, rate, volume, pitch):
        """生成音频，并在生成过程中禁用按钮、显示进度条。"""
        self.generate_button.configure(state="disabled") 
        display_voice_name = "未知"
        if voice: 
            for dn, fn in self.voice_display_to_full_map.items():
                if fn == voice:
                    display_voice_name = dn
                    break
            if display_voice_name == "未知":
                name_part_match = re.search(r", (.*Neural)\)$", voice)
                display_voice_name = name_part_match.group(1) if name_part_match else voice
        self.update_status(f"正在生成音频 (声音: {display_voice_name})...", permanent=True, show_progress=True)
        def on_complete(path, error_msg=None): 
            self.generate_button.configure(state="normal") 
            if path: 
                self.update_status(f"生成成功: {os.path.basename(path)}", duration=10)
                print("音频生成完成:", path)
                if self.play_audio_var.get(): 
                    try:
                        threading.Thread(target=lambda p=path: playsound(p), daemon=True).start()
                        print("音频播放已启动")
                    except Exception as e:
                        print(f"音频播放失败: {e}")
                        self.update_status(f"播放失败: {e}", error=True)
                if self.copy_to_clipboard_var.get(): 
                    copy_file_to_clipboard(path) 
                    if hasattr(self, 'show_ok_window'):
                        self.root.after(0, self.show_ok_window)
            else: 
                err_str = f"音频生成失败: {error_msg}" if error_msg else "音频生成失败，请检查网络或声音选择。"
                print(err_str)
                self.update_status(err_str, error=True)
            if self.float_window:
                try: self.float_window.destroy()
                except tk.TclError: pass
                self.float_window = None
            manage_audio_files() 
        generate_audio(text, voice, rate, volume, pitch, on_complete)

    # --------------------------------------------------------------------------
    # 浮窗相关方法 (无需修改)
    # --------------------------------------------------------------------------
    def show_float_window(self, text):
        """在鼠标位置显示“音”字浮窗"""
        if self.float_window:
            try: self.float_window.destroy()
            except tk.TclError: pass 
            self.float_window = None
        self.float_window = tk.Toplevel(self.root)
        self.float_window.overrideredirect(True) 
        x, y = self.last_mouse_pos 
        self.float_window.geometry(f"50x50+{x + 10}+{y + 10}") 
        self.float_window.attributes("-topmost", True) 
        float_button = ctk.CTkButton(
            self.float_window, text="音", width=50, height=50, corner_radius=25, 
            font=ctk.CTkFont(size=20, weight="bold"), fg_color="#1E90FF", 
            hover_color="#1C86EE", text_color="white",
            command=lambda t=text: self.trigger_generate_from_float(t) 
        )
        float_button.pack()
        def auto_close():
            if self.float_window:
                try: self.float_window.destroy()
                except tk.TclError: pass
                self.float_window = None 
        self.float_window.after(FLOAT_WINDOW_TIMEOUT * 1000, auto_close)
        
    def show_ok_window(self):
        """在鼠标位置显示 'OK' 浮窗"""
        if hasattr(self, 'ok_window') and self.ok_window:
            try: self.ok_window.destroy()
            except tk.TclError: pass
            self.ok_window = None
        self.ok_window = tk.Toplevel(self.root)
        self.ok_window.overrideredirect(True)
        x, y = self.last_mouse_pos
        self.ok_window.geometry(f"50x50+{x + 10}+{y + 10}")
        self.ok_window.attributes("-topmost", True)
        ok_button = ctk.CTkButton(
            self.ok_window, text="OK", width=50, height=50, corner_radius=25,
            font=ctk.CTkFont(size=20, weight="bold"), fg_color="#DC143C", 
            hover_color="#B22222", text_color="white",
            command=lambda: self.ok_window.destroy() if self.ok_window else None 
        )
        ok_button.pack()
        def auto_close():
            if hasattr(self, 'ok_window') and self.ok_window:
                try: self.ok_window.destroy()
                except tk.TclError: pass
                self.ok_window = None 
        self.ok_window.after(MOUSE_TIP_TIMEOUT * 1000, auto_close)

    def trigger_generate_from_float(self, text):
        """处理浮窗按钮点击事件"""
        print(f"通过浮窗触发生成: {text[:50]}...")
        if self.float_window:
            try: self.float_window.destroy() 
            except tk.TclError: pass
            self.float_window = None
        voice = self.current_full_voice_name 
        if not voice: 
             self.update_status("错误：请选择一个声音", error=True, duration=5)
             return
        rate_val = self.rate_slider_var.get()
        volume_val = self.volume_slider_var.get()
        rate_str = f"{rate_val:+}%"
        volume_str = f"{volume_val:+}%"
        pitch_str = "+0Hz"
        self.generate_with_animation(text, voice, rate_str, volume_str, pitch_str)

    # --------------------------------------------------------------------------
    # 剪贴板监控方法 (无需修改)
    # --------------------------------------------------------------------------
    def toggle_select_to_audio(self):
        """切换“启用复制生音频”开关的状态"""
        global clipboard_monitor_active
        if self.select_to_audio_switch.get(): 
            if not clipboard_monitor_active: self.start_clipboard_monitor() 
        else: 
            self.stop_clipboard_monitor() 
        self.save_settings() 

    def start_clipboard_monitor(self):
        """启动剪贴板监控线程"""
        global clipboard_monitor_active
        if self.clipboard_thread and self.clipboard_thread.is_alive():
            print("剪贴板监控已在运行")
            return
        clipboard_monitor_active = True 
        print("启动剪贴板监控...")
        self.update_status("剪贴板监控已启用", duration=5)
        def monitor_clipboard():
            global clipboard_monitor_active
            last_text = ""
            try: last_text = pyperclip.paste() 
            except Exception: pass
            while clipboard_monitor_active: 
                try:
                    current_text = pyperclip.paste() 
                    if current_text and current_text != last_text and current_text.strip():
                        sanitized = sanitize_text(current_text) 
                        if sanitized:
                            last_text = current_text 
                            print(f"检测到剪贴板变化: {sanitized[:50]}...")
                            def show_float_wrapper(txt=sanitized):
                                if clipboard_monitor_active and self.root.winfo_exists():
                                    self.last_mouse_pos = (self.root.winfo_pointerx(), self.root.winfo_pointery())
                                    print(f"复制时的鼠标位置: {self.last_mouse_pos}")
                                    self.show_float_window(txt)
                            if self.root.winfo_exists():
                                self.root.after(0, show_float_wrapper)
                    time.sleep(0.5) 
                except Exception as e: 
                    print(f"剪贴板监控错误: {e}")
                    time.sleep(1) 
            print("剪贴板监控线程已停止。")
        self.clipboard_thread = threading.Thread(target=monitor_clipboard, daemon=True)
        self.clipboard_thread.start()

    def stop_clipboard_monitor(self):
        """停止剪贴板监控线程"""
        global clipboard_monitor_active
        if not clipboard_monitor_active:
            print("剪贴板监控未运行")
            return
        print("正在停止剪贴板监控...")
        clipboard_monitor_active = False 
        if self.float_window:
            try: self.float_window.destroy()
            except tk.TclError: pass
            self.float_window = None
        if self.ok_window:
             try: self.ok_window.destroy()
             except tk.TclError: pass
             self.ok_window = None
        self.clipboard_thread = None 
        self.update_status("剪贴板监控已禁用", duration=3)

    # --------------------------------------------------------------------------
    # 窗口关闭处理 (无需修改)
    # --------------------------------------------------------------------------
    def on_closing(self):
        """处理窗口关闭事件"""
        print("窗口关闭...")
        self.stop_clipboard_monitor() 
        self.save_settings() 
        self.root.destroy() 

# ==============================================================================
# 程序入口点
# ==============================================================================
if __name__ == "__main__":
    root = ctk.CTk()
    app = EdgeTTSApp(root)
    root.mainloop()
