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
from tkinter import messagebox # 不再需要 ttk
import json

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
    # 移除非字母、数字、空格及常用标点符号的字符
    text = re.sub(r"[^\w\s.,!?;:\"'()\[\]{}<>%&$@#*+-=/]", "", text, flags=re.UNICODE)
    # 将连续的空白字符替换为单个空格，并去除首尾空格
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else ""

# ==============================================================================
# 模块 2：剪贴板操作
# ==============================================================================
def copy_file_to_clipboard(file_path):
    """将指定文件的路径复制到系统剪贴板，使其能像在文件管理器中复制文件一样被粘贴"""
    try:
        # 定义 Windows API 需要的 DROPFILES 结构体
        class DROPFILES(ctypes.Structure):
            _fields_ = [
                ("pFiles", wintypes.DWORD),
                ("pt", wintypes.POINT),
                ("fNC", wintypes.BOOL),
                ("fWide", wintypes.BOOL),
            ]

        file_path = os.path.abspath(file_path)  # 获取绝对路径
        # 准备数据：UTF-16 LE 编码的文件路径，以两个空字节结束
        data = file_path.encode('utf-16-le') + b'\0\0'
        
        # 填充 DROPFILES 结构体
        dropfiles = DROPFILES()
        dropfiles.pFiles = ctypes.sizeof(DROPFILES)  # 文件列表偏移量
        dropfiles.pt.x = 0  # 拖放点 X 坐标 (未使用)
        dropfiles.pt.y = 0  # 拖放点 Y 坐标 (未使用)
        dropfiles.fNC = False  # 是否包含非客户区坐标 (未使用)
        dropfiles.fWide = True  # 是否使用宽字符 (Unicode)

        # 创建内存缓冲区，包含结构体和文件路径数据
        buffer_size = ctypes.sizeof(DROPFILES) + len(data)
        buffer = (ctypes.c_char * buffer_size)()
        # 将结构体和数据复制到缓冲区
        ctypes.memmove(buffer, ctypes.byref(dropfiles), ctypes.sizeof(DROPFILES))
        ctypes.memmove(ctypes.byref(buffer, ctypes.sizeof(DROPFILES)), data, len(data))

        # 打开、清空并设置剪贴板数据 (CF_HDROP 格式)
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
    """异步获取所有可用的 Edge TTS 声音，并按 语言->地区->名称 的层级结构分类"""
    try:
        # 使用 VoicesManager 获取声音列表
        voices = await VoicesManager.create()
        raw_voices_list = voices.find() 
        
        # 正则表达式用于从声音完整名称中提取语言、地区和名称部分
        # (zh-CN, XiaoxiaoNeural) -> lang='zh', region='CN', name_part='XiaoxiaoNeural'
        voice_pattern = re.compile(r"^Microsoft Server Speech Text to Speech Voice \(([a-z]{2,3})-([A-Z]{2,}(?:-[A-Za-z]+)?), (.*Neural)\)$") 
        
        hierarchical_voices = {} # 用于存储层级结构的声音数据

        # 遍历原始声音列表
        for v in raw_voices_list:
            full_name = v['Name'] 
            match = voice_pattern.match(full_name)
            if match:
                lang, region, name_part = match.groups() 
                # 构建层级字典
                if lang not in hierarchical_voices: hierarchical_voices[lang] = {}
                if region not in hierarchical_voices[lang]: hierarchical_voices[lang][region] = []
                hierarchical_voices[lang][region].append(full_name) # 存储完整名称
            else:
                # 打印无法匹配的声音名称 (用于调试)
                print(f"声音格式不匹配层级分类，跳过: {full_name}")

        # 对内部结构进行排序 (地区按字母排序，声音按完整名称排序)
        for lang in hierarchical_voices:
            for region in hierarchical_voices[lang]:
                hierarchical_voices[lang][region].sort()
            hierarchical_voices[lang] = dict(sorted(hierarchical_voices[lang].items()))

        # 将中文和英文提到最前面，其他语言按字母排序
        sorted_hierarchical_voices = {}
        if "zh" in hierarchical_voices: sorted_hierarchical_voices["zh"] = hierarchical_voices.pop("zh")
        if "en" in hierarchical_voices: sorted_hierarchical_voices["en"] = hierarchical_voices.pop("en")
        for lang in sorted(hierarchical_voices.keys()): sorted_hierarchical_voices[lang] = hierarchical_voices[lang]

        # 统计获取到的声音总数
        total_voices = sum(len(voices) for lang_data in sorted_hierarchical_voices.values() for voices in lang_data.values())
        print(f"获取到 {total_voices} 个声音，已按 语言->地区->名称 层级分类。")
        return sorted_hierarchical_voices 

    except Exception as e:
        print(f"获取声音列表失败: {e}")
        if app: app.update_status(f"获取声音列表失败: {e}", error=True)
        return {}

# --- 在后台线程中刷新声音列表的函数 ---
def refresh_voices_list():
    """启动一个后台线程来异步获取声音列表，获取完成后通过 app.root.after 调用主线程的 UI 更新函数"""
    def run_async_get_voices():
        hierarchical_voice_data = {} 
        try:
            # 创建并运行新的事件循环来执行异步获取函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            hierarchical_voice_data = loop.run_until_complete(get_available_voices_async()) 
            loop.close()
        except Exception as e:
            print(f"运行异步获取声音任务时出错: {e}")
            if app: app.update_status(f"获取声音时出错: {e}", error=True)
        finally:
            # 确保在主线程中更新 UI
            if app and app.root.winfo_exists():
                # 使用 after(0, ...) 将 UI 更新任务添加到 Tkinter 的事件队列中
                app.root.after(0, app.update_voice_tree, hierarchical_voice_data)

    # 启动后台线程
    threading.Thread(target=run_async_get_voices, daemon=True).start()


# ==============================================================================
# 模块 4：音频生成
# ==============================================================================
async def generate_audio_edge_tts_async(text, voice, rate, volume, pitch, output_path):
    """使用 edge-tts 库异步生成音频文件"""
    try:
        # 创建 Communicate 对象并设置参数
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        # 保存音频文件
        await communicate.save(output_path)
        print(f"Edge TTS 音频生成成功: {output_path}")
        return output_path
    except Exception as e:
        print(f"Edge TTS 音频生成失败: {e}")
        return None

def generate_audio(text, voice, rate_str, volume_str, pitch_str, on_complete=None):
    """
    启动一个后台线程来异步生成音频。
    参数:
        text (str): 要转换的文本。
        voice (str): 使用的声音的完整名称。
        rate_str (str): 语速调整字符串 (例如 "+10%")。
        volume_str (str): 音量调整字符串 (例如 "-5%")。
        pitch_str (str): 音高调整字符串 (例如 "+0Hz")。
        on_complete (callable): 生成完成后的回调函数，接收 (path, error_message) 参数。
    """
    # 清理输入文本
    text = sanitize_text(text)
    if not text:
        print("文本为空，无法生成音频")
        if app: app.update_status("错误：文本不能为空", error=True)
        if on_complete: on_complete(None, "文本为空") 
        return

    # 生成包含时间戳和声音名称的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_part_match = re.search(r", (.*Neural)\)$", voice) # 提取声音名称部分
    safe_voice_part = re.sub(r'\W+', '', name_part_match.group(1)) if name_part_match else "UnknownVoice"
    filename = f"Anki-TTS-Edge_{safe_voice_part}_{timestamp}.mp3"
    output_path = os.path.join(AUDIO_DIR, filename)

    print(f"准备生成音频: voice='{voice}', rate='{rate_str}', volume='{volume_str}', pitch='{pitch_str}'")
    print(f"输出路径: {output_path}")
    if app: app.update_status(f"正在生成音频 (声音: {safe_voice_part})...", permanent=True, show_progress=True) 

    # 定义在后台线程中运行的函数
    def run_async_in_thread():
        result_path = None; error_message = None
        try:
            # 创建并运行新的事件循环来执行异步生成函数
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            result_path = loop.run_until_complete(generate_audio_edge_tts_async(text, voice, rate_str, volume_str, pitch_str, output_path))
            loop.close()
            if not result_path: error_message = "Edge TTS 内部错误"
        except Exception as e:
            print(f"运行异步生成任务时出错: {e}"); error_message = str(e)
        finally:
            # 确保在主线程中调用完成回调
            if app and app.root.winfo_exists(): 
                final_path = result_path if result_path else None
                final_error = error_message if not result_path else None
                # 使用 after(0, ...) 将回调任务添加到 Tkinter 的事件队列中
                app.root.after(0, on_complete, final_path, final_error) 

    # 启动后台线程
    threading.Thread(target=run_async_in_thread, daemon=True).start()


# ==============================================================================
# 模块 5：文件管理
# ==============================================================================
def manage_audio_files():
    """删除旧的音频文件，只保留最新的指定数量的文件"""
    try:
        # 从 UI 获取最大文件数设置，如果失败则使用默认值
        max_files_str = app.max_files_entry.get() if app and hasattr(app, 'max_files_entry') else str(DEFAULT_MAX_AUDIO_FILES)
        max_files = int(max_files_str) if max_files_str.isdigit() else DEFAULT_MAX_AUDIO_FILES
        # 限制最大文件数在 1 到 50 之间
        if not (1 <= max_files <= 50): max_files = DEFAULT_MAX_AUDIO_FILES
    except (ValueError, AttributeError): max_files = DEFAULT_MAX_AUDIO_FILES

    try:
        if not os.path.exists(AUDIO_DIR): return # 如果目录不存在则返回
        # 获取目录下所有 mp3 文件，并按创建时间排序 (旧的在前)
        files = sorted(
            [f for f in os.listdir(AUDIO_DIR) if f.endswith(".mp3")],
            key=lambda x: os.path.getctime(os.path.join(AUDIO_DIR, x))
        )
        # 如果文件数量超过限制，则删除最旧的文件
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
        self.root.geometry("550x750") # 设置窗口大小
        self.root.configure(bg="#F0F0F0") # 设置背景色
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing) # 绑定窗口关闭事件
        global app; app = self # 设置全局 app 引用
        
        # 存储声音名称映射 (显示名称 -> 完整名称)
        self.voice_display_to_full_map = {} 
        # 存储当前选中的声音的完整名称
        self.current_full_voice_name = None 
        # 不再需要 self.selected_voices_full

        # --- 加载设置 ---
        settings = self.load_settings()
        
        # 设置 customtkinter 外观模式和主题
        ctk.set_appearance_mode("light") 
        ctk.set_default_color_theme("blue") 

        # --- 创建主框架 ---
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        # 配置主框架网格布局权重
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=0) # 文本输入区不扩展
        self.main_frame.grid_rowconfigure(1, weight=1) # 设置区域可垂直扩展
        self.main_frame.grid_rowconfigure(2, weight=0) # 操作按钮区不扩展
        self.main_frame.grid_rowconfigure(3, weight=0) # 状态栏不扩展

        # --- 创建顶部：文本输入区域 ---
        self.text_input_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.text_input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15)) 
        self.text_input_frame.grid_columnconfigure(0, weight=1)
        self.text_input_label = ctk.CTkLabel(self.text_input_frame, text="输入文本:", font=ctk.CTkFont(weight="bold"))
        self.text_input_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.text_input = ctk.CTkTextbox(self.text_input_frame, height=120, wrap="word", corner_radius=8, border_width=1)
        self.text_input.grid(row=1, column=0, sticky="nsew")

        # --- 创建中部：可滚动的设置区域 ---
        self.settings_area_frame = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent", label_text="") 
        self.settings_area_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        self.settings_area_frame.grid_columnconfigure(0, weight=1)

        # --- 分组 1: 声音筛选与效果 ---
        self.voice_effects_frame = ctk.CTkFrame(self.settings_area_frame, corner_radius=8, border_width=1) 
        self.voice_effects_frame.pack(fill="x", pady=(0, 15)) 
        self.voice_effects_frame.grid_columnconfigure(1, weight=1) # 自定义下拉按钮列可扩展
        self.voice_effects_frame.grid_columnconfigure(2, weight=0) # 滑块标签列不扩展
        self.voice_effects_frame.grid_rowconfigure(1, weight=1) # 双列声音列表行可扩展
        self.voice_effects_frame.grid_rowconfigure(3, weight=0) # 自定义下拉列表行不扩展

        # 分组标题
        self.voice_effects_label = ctk.CTkLabel(self.voice_effects_frame, text="声音筛选与效果", font=ctk.CTkFont(weight="bold"))
        self.voice_effects_label.grid(row=0, column=0, columnspan=3, pady=(10, 10), padx=10, sticky="w") 

        # 包含左右两列声音列表的框架
        self.voice_columns_frame = ctk.CTkFrame(self.voice_effects_frame)
        self.voice_columns_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=(0,5), sticky="nsew")
        
        # 刷新声音列表按钮
        self.refresh_button = ctk.CTkButton(self.voice_effects_frame, text="🔄 刷新声音列表",
                                          command=self.refresh_voices_ui,
                                          width=120, corner_radius=5,
                                          font=ctk.CTkFont(size=12))
        self.refresh_button.grid(row=0, column=2, padx=(5, 10), pady=(0, 5), sticky="ne")
        
        # 配置双列框架的列宽权重
        self.voice_columns_frame.grid_columnconfigure(0, weight=1)
        self.voice_columns_frame.grid_columnconfigure(1, weight=1)
        
        # 左侧声音列表滚动框架
        self.left_voice_frame = ctk.CTkScrollableFrame(self.voice_columns_frame, width=220, height=250)
        self.left_voice_frame.grid(row=0, column=0, padx=(0,10), pady=5, sticky="nsew")
        
        # 右侧声音列表滚动框架
        self.right_voice_frame = ctk.CTkScrollableFrame(self.voice_columns_frame, width=220, height=250)
        self.right_voice_frame.grid(row=0, column=1, padx=(10,0), pady=5, sticky="nsew")

        # --- 自定义下拉选择器 ---
        self.selected_voice_label = ctk.CTkLabel(self.voice_effects_frame, text="选用:")
        self.selected_voice_label.grid(row=2, column=0, padx=(10, 5), pady=5, sticky="w")
        
        # 触发按钮，显示当前选中的声音（显示名称）
        self.selected_voice_button = ctk.CTkButton(self.voice_effects_frame, text="选择声音", command=self._toggle_voice_options_list)
        self.selected_voice_button.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        # 选项列表框架 (可滚动，初始隐藏)
        self.voice_options_frame = ctk.CTkScrollableFrame(self.voice_effects_frame, label_text="")
        # 初始不 grid，在 _toggle_voice_options_list 中控制显示/隐藏
        
        # 占位标签，保持布局
        ctk.CTkLabel(self.voice_effects_frame, text="").grid(row=2, column=2)

        # 语速滑块
        self.rate_label = ctk.CTkLabel(self.voice_effects_frame, text="语速:")
        self.rate_label.grid(row=4, column=0, padx=(10, 5), pady=5, sticky="w") # 行号调整
        self.rate_slider_var = ctk.IntVar(value=settings.get("rate", 0)) # 加载设置
        self.rate_slider = ctk.CTkSlider(self.voice_effects_frame, from_=-100, to=100, number_of_steps=40, variable=self.rate_slider_var, command=self.update_rate_label)
        self.rate_slider.grid(row=4, column=1, padx=5, pady=5, sticky="ew") # 行号调整
        self.rate_value_label = ctk.CTkLabel(self.voice_effects_frame, text=f"{self.rate_slider_var.get():+}%", width=40) # 显示滑块值的标签
        self.rate_value_label.grid(row=4, column=2, padx=(5, 10), pady=5) # 行号调整

        # 音量滑块
        self.volume_label = ctk.CTkLabel(self.voice_effects_frame, text="音量:")
        self.volume_label.grid(row=5, column=0, padx=(10, 5), pady=(5, 10), sticky="w") # 行号调整
        self.volume_slider_var = ctk.IntVar(value=settings.get("volume", 0)) # 加载设置
        self.volume_slider = ctk.CTkSlider(self.voice_effects_frame, from_=-100, to=100, number_of_steps=40, variable=self.volume_slider_var, command=self.update_volume_label)
        self.volume_slider.grid(row=5, column=1, padx=5, pady=(5, 10), sticky="ew") # 行号调整
        self.volume_value_label = ctk.CTkLabel(self.voice_effects_frame, text=f"{self.volume_slider_var.get():+}%", width=40) # 显示滑块值的标签
        self.volume_value_label.grid(row=5, column=2, padx=(5, 10), pady=(5, 10)) # 行号调整

        # --- 分组 2 & 3: 输出缓存与剪贴板功能 (并排显示) ---
        self.combined_settings_frame = ctk.CTkFrame(self.settings_area_frame, fg_color="transparent")
        self.combined_settings_frame.pack(fill="x", pady=(0, 15)) 
        self.combined_settings_frame.grid_columnconfigure(0, weight=1) # 左侧列可扩展
        self.combined_settings_frame.grid_columnconfigure(1, weight=1) # 右侧列可扩展

        # -- 输出与缓存设置 (左侧) --
        self.output_cache_frame = ctk.CTkFrame(self.combined_settings_frame, corner_radius=8, border_width=1) 
        self.output_cache_frame.grid(row=0, column=0, padx=(0, 5), sticky="nsew") 
        self.output_cache_frame.grid_columnconfigure(1, weight=1) 
        self.output_cache_label = ctk.CTkLabel(self.output_cache_frame, text="输出与缓存", font=ctk.CTkFont(weight="bold"))
        self.output_cache_label.grid(row=0, column=0, columnspan=3, pady=(10, 10), padx=10, sticky="w") 
        # 复制文件路径开关
        self.copy_to_clipboard_var = ctk.BooleanVar(value=settings.get("copy_path_enabled", True))
        self.copy_to_clipboard_switch = ctk.CTkSwitch(self.output_cache_frame, text="复制文件路径", variable=self.copy_to_clipboard_var, onvalue=True, offvalue=False)
        self.copy_to_clipboard_switch.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        # 自动播放音频开关
        self.play_audio_var = ctk.BooleanVar(value=settings.get("autoplay_enabled", False))
        self.play_audio_switch = ctk.CTkSwitch(self.output_cache_frame, text="自动播放音频", variable=self.play_audio_var, onvalue=True, offvalue=False)
        self.play_audio_switch.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        # 最大缓存数输入框
        self.max_files_label = ctk.CTkLabel(self.output_cache_frame, text="最大缓存数:")
        self.max_files_label.grid(row=2, column=0, padx=(10, 5), pady=(5, 10), sticky="w") 
        self.max_files_entry = ctk.CTkEntry(self.output_cache_frame, width=60)
        self.max_files_entry.insert(0, str(settings.get("max_audio_files", DEFAULT_MAX_AUDIO_FILES))) # 使用加载的设置
        self.max_files_entry.grid(row=2, column=1, padx=5, pady=(5, 10), sticky="w") 

        # -- 剪贴板功能设置 (右侧) --
        self.clipboard_frame = ctk.CTkFrame(self.combined_settings_frame, corner_radius=8, border_width=1) 
        self.clipboard_frame.grid(row=0, column=1, padx=(5, 0), sticky="nsew") 
        self.clipboard_frame.grid_columnconfigure(0, weight=1) 
        self.clipboard_label = ctk.CTkLabel(self.clipboard_frame, text="剪贴板功能", font=ctk.CTkFont(weight="bold"))
        self.clipboard_label.grid(row=0, column=0, columnspan=2, pady=(10, 10), padx=10, sticky="w") 
        # 启用复制生音频开关
        self.select_to_audio_var = ctk.BooleanVar(value=settings.get("monitor_enabled", False))
        self.select_to_audio_switch = ctk.CTkSwitch(self.clipboard_frame, text="启用复制生音频", variable=self.select_to_audio_var, command=self.toggle_select_to_audio, onvalue=True, offvalue=False) 
        self.select_to_audio_switch.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="w") 

        # --- 创建底部：操作按钮 & 状态栏 ---
        self.bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.bottom_frame.grid(row=2, column=0, sticky="ew", pady=(15, 5)) 
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        # “生成音频”按钮
        self.generate_button = ctk.CTkButton(self.bottom_frame, text="生成音频", command=self.generate_audio_manual, height=35, font=ctk.CTkFont(size=14, weight="bold"), corner_radius=8)
        self.generate_button.pack(pady=(0, 10)) 

        # 状态栏框架
        self.status_bar_frame = ctk.CTkFrame(self.main_frame, height=25, corner_radius=0, fg_color="gray80")
        self.status_bar_frame.grid(row=3, column=0, sticky="ew")
        self.status_bar_frame.grid_columnconfigure(0, weight=1) # 状态文本列可扩展
        self.status_bar_frame.grid_columnconfigure(1, weight=0) # 进度条列不扩展
        # 状态标签
        self.status_label = ctk.CTkLabel(self.status_bar_frame, text="准备就绪", anchor="w", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=0, column=0, sticky="ew", padx=(10, 5))
        # 进度条 (默认隐藏)
        self.progress_bar = ctk.CTkProgressBar(self.status_bar_frame, height=10, width=100, corner_radius=5)
        self.progress_bar.set(0)
        self.progress_bar.grid_remove() # 初始隐藏

        # --- 初始化浮窗相关变量 ---
        self.float_window = None # 复制生音频浮窗
        self.ok_window = None    # 复制成功提示浮窗
        self.clipboard_thread = None # 剪贴板监控线程
        self.last_mouse_pos = (0, 0) # 最后记录的鼠标位置

        # --- 初始化操作 ---
        self.refresh_voices_ui() # 启动时刷新声音列表
        # 如果设置中启用了剪贴板监控，则启动它
        if self.select_to_audio_var.get():
            self.start_clipboard_monitor()

    # --------------------------------------------------------------------------
    # UI 更新与状态管理方法
    # --------------------------------------------------------------------------
    def update_status(self, message, duration=0, error=False, permanent=False, show_progress=False):
        """
        更新状态栏信息。
        参数:
            message (str): 要显示的消息。
            duration (int): 消息显示时间 (秒)，0 表示永久显示直到下次更新。
            error (bool): 是否为错误消息 (红色显示)。
            permanent (bool): 是否永久显示 (覆盖 duration)。
            show_progress (bool): 是否显示不确定进度条。
        """
        global status_update_job
        def _update(): # 实际更新 UI 的内部函数 (确保在主线程执行)
            global status_update_job
            # 取消之前的自动清除任务
            if status_update_job:
                try: self.status_label.after_cancel(status_update_job)
                except: pass
                status_update_job = None
            # 更新状态标签文本和颜色
            self.status_label.configure(text=message, text_color="red" if error else "black")
            # 控制进度条显示
            if show_progress:
                self.progress_bar.grid(row=0, column=1, padx=(0, 10), sticky="e") 
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start()
            else:
                self.progress_bar.stop()
                self.progress_bar.grid_remove() 
            # 设置自动清除任务 (如果需要)
            if not permanent and duration > 0:
                status_update_job = self.status_label.after(duration * 1000, lambda: self.update_status("准备就绪"))
        
        # 如果不在主线程，使用 after(0, ...) 调度到主线程执行
        if threading.current_thread() is not threading.main_thread():
            if self.root.winfo_exists(): self.root.after(0, _update)
        else: # 如果在主线程，直接执行
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
        self.refresh_button.configure(state="disabled") # 禁用刷新按钮
        # 更新自定义下拉按钮为加载状态
        if hasattr(self, 'selected_voice_button'):
             self.selected_voice_button.configure(text="正在加载...", state="disabled") 
        # 调用后台线程刷新声音列表
        refresh_voices_list()
        
    def update_voice_tree(self, hierarchical_voice_data):
        """
        (在主线程中调用) 使用获取到的声音数据更新双列声音列表 UI。
        """
        print("DEBUG: update_voice_tree called") 
        # 存储当前声音数据，供展开时使用
        self.current_voice_data = hierarchical_voice_data
        
        # 重新启用刷新按钮
        self.refresh_button.configure(state="normal")
        # 清空旧的显示名称到完整名称的映射
        self.voice_display_to_full_map.clear()
        
        print("DEBUG: Clearing old UI elements") 
        # 清空左右两列的旧 UI 元素
        for widget in self.left_voice_frame.winfo_children():
            widget.destroy()
        for widget in self.right_voice_frame.winfo_children():
            widget.destroy()

        # 处理获取声音失败的情况
        if not hierarchical_voice_data:
            print("DEBUG: No voice data received, returning.") 
            if hasattr(self, 'selected_voice_button'):
                 self.selected_voice_button.configure(text="获取失败", state="disabled")
            self.update_status("获取声音列表失败", error=True)
            return

        # --- 填充 voice_display_to_full_map ---
        self.voice_display_to_full_map.clear() # 先清空
        name_extract_pattern = re.compile(r", (.*Neural)\)$") # 用于提取显示名称的正则
        for lang_data in hierarchical_voice_data.values():
            for region_voices in lang_data.values(): # 修正：应该迭代 lang_data.values()
                for full_name in region_voices:
                    name_part_match = name_extract_pattern.search(full_name)
                    display_name = name_part_match.group(1) if name_part_match else full_name
                    self.voice_display_to_full_map[display_name] = full_name
        # --- 结束填充 ---

        # 语言代码到显示名称的映射 (可扩展)
        lang_name_map = {
            "zh": "中文", "en": "英文", "ja": "日文", "ko": "韩文",
            "fr": "法文", "de": "德文", "es": "西班牙文", "it": "意大利文",
            "ru": "俄文", "pt": "葡萄牙文"
            # ... 可根据需要添加更多语言 ...
        }

        print("DEBUG: Preparing language lists") 
        # 准备语言列表并排序
        languages = sorted(hierarchical_voice_data.keys())
        
        # 将中文和英文分别分配到左右列
        left_languages = []
        right_languages = []
        if "zh" in languages:
            left_languages.append("zh")
            languages.remove("zh")
        if "en" in languages:
            right_languages.append("en")
            languages.remove("en")
            
        # 其他语言按字母顺序轮流分配到左右列
        for i, lang in enumerate(languages):
            if i % 2 == 0:
                left_languages.append(lang)
            else:
                right_languages.append(lang)
                
        print(f"DEBUG: Left languages: {left_languages}") 
        print(f"DEBUG: Right languages: {right_languages}") 

        # --- 创建左右列的语言选择 UI ---
        def create_language_column(parent_frame, languages_list): 
            """在指定的父框架中创建一列语言按钮和对应的折叠区域"""
            row = 0
            for lang_code in languages_list: 
                # 获取语言显示名称
                lang_name = lang_name_map.get(lang_code, lang_code) # 如果映射中没有，则直接使用 lang_code
                # 创建包含按钮和折叠区的框架
                lang_frame = ctk.CTkFrame(parent_frame)
                lang_frame.grid(row=row, column=0, pady=(5,0), sticky="ew")
                
                # 创建可点击的语言按钮 (一级菜单)
                lang_btn = ctk.CTkButton(
                    lang_frame,
                    text=f"▶ {lang_name}", # 初始显示折叠图标
                    command=lambda l=lang_code: self.toggle_language_expansion(l), # 点击时切换展开/折叠
                    anchor="w", # 文本左对齐
                    fg_color="transparent", # 背景透明
                    text_color=("gray10", "gray90"), # 设置文字颜色 (适配深浅模式)
                    hover_color="#f0f0f0" # 鼠标悬停颜色
                )
                lang_btn.grid(row=0, column=0, sticky="ew")
                self.lang_buttons[lang_code] = lang_btn # 存储按钮引用
                row += 1
                
                # 创建用于显示地区和声音的折叠框架 (二级菜单，默认隐藏)
                # 父控件是 lang_frame，使其在布局上跟随一级菜单
                self.lang_expansion_frames[lang_code] = ctk.CTkFrame(lang_frame) 
                # 内容将在 toggle_language_expansion 中填充和显示/隐藏
        
        # 初始化用于存储语言展开状态和控件引用的字典
        self.lang_expansion_frames = {} # 存储二级菜单框架 {lang_code: frame}
        self.lang_buttons = {}        # 存储一级菜单按钮 {lang_code: button}
        self.lang_expansion_states = {lang_code: False for lang_code in left_languages + right_languages} # 存储展开状态 {lang_code: bool}
        
        # 分别创建左右两列的 UI
        print("DEBUG: Creating left column UI") 
        create_language_column(self.left_voice_frame, left_languages)
        print("DEBUG: Creating right column UI") 
        create_language_column(self.right_voice_frame, right_languages)
        
        print("DEBUG: update_voice_tree finished") 
        # 更新“选用”下拉框和状态栏
        self._update_voice_options_list() # 调用新的更新函数
        self.update_status("声音列表已更新", duration=3)


    def toggle_language_expansion(self, lang): 
        """切换指定语言项的展开/折叠状态"""
        # 检查状态字典是否存在
        if not hasattr(self, 'lang_expansion_states'):
            return
            
        # 切换状态 (True -> False, False -> True)
        self.lang_expansion_states[lang] = not self.lang_expansion_states[lang]
        
        # 获取对应的二级菜单框架和一级菜单按钮
        frame = self.lang_expansion_frames.get(lang)
        lang_btn = self.lang_buttons.get(lang) 
        
        # 如果找不到框架或按钮，则直接返回 (防御性编程)
        if not frame or not lang_btn: 
            return
            
        # 清空二级菜单框架的现有内容 (防止重复添加)
        for widget in frame.winfo_children():
            widget.destroy()
            
        # 根据新的状态更新 UI
        if self.lang_expansion_states[lang]:
            # --- 展开状态 ---
            # 更新按钮图标为向下箭头
            lang_btn.configure(text=f"▼ {lang_btn.cget('text')[2:]}")
            
            # 获取当前语言的声音数据
            lang_data = self.current_voice_data.get(lang, {})
            row = 0
            
            # 遍历地区和声音，创建标签和按钮并添加到二级菜单框架中
            for region, voices in lang_data.items():
                # 创建地区标签
                region_lbl = ctk.CTkLabel(frame, text=f"  {region}", anchor="w", text_color=("gray10", "gray90"))
                region_lbl.grid(row=row, column=0, sticky="w")
                row += 1
                
                # 创建声音按钮
                for voice in voices:
                    # 提取显示名称 (例如 "XiaoxiaoNeural")
                    display_name = voice.split(',')[-1].strip(') ')
                    voice_btn = ctk.CTkButton(
                        frame,
                        text=f"    {display_name}",
                        # 点击声音按钮时，调用 _select_voice_option 并传递完整名称
                        command=lambda v=voice: self._select_voice_option(v), 
                        anchor="w",
                        fg_color="transparent",
                        text_color=("gray10", "gray90"),
                        hover_color="#e0e0e0"
                    )
                    voice_btn.grid(row=row, column=0, sticky="ew")
                    row += 1
            
            # 显示二级菜单框架 (放置在 lang_frame 的第 1 行)
            frame.grid(row=1, column=0, pady=(0,5), sticky="ew")
            
        else:
            # --- 折叠状态 ---
            # 更新按钮图标为向右箭头
            lang_btn.configure(text=f"▶ {lang_btn.cget('text')[2:]}")
            # 隐藏二级菜单框架
            frame.grid_forget()

    # --------------------------------------------------------------------------
    # 自定义下拉列表与声音选择处理
    # --------------------------------------------------------------------------
    def _toggle_voice_options_list(self):
        """显示或隐藏声音选项列表"""
        if self.voice_options_frame.winfo_ismapped():
            self.voice_options_frame.grid_forget()  # 如果已显示，则隐藏
        else:
            self._update_voice_options_list()  # 确保选项是最新的
            # 将选项列表放置在触发按钮下方
            self.voice_options_frame.grid(row=3, column=1, padx=5, pady=(0,5), sticky="nsew", columnspan=1) 
            self.voice_options_frame.tkraise(self.selected_voice_button) # 尝试置顶

    def _update_voice_options_list(self):
        """更新声音选项列表的内容和触发按钮的文本"""
        # 清空之前的选项
        for widget in self.voice_options_frame.winfo_children():
            widget.destroy()

        # 获取所有可用的声音 (从映射字典中获取)
        all_voices = list(self.voice_display_to_full_map.items()) # [(display_name, full_name), ...]
        all_voices.sort() # 按显示名称排序

        print(f"DEBUG _update_options: Found {len(all_voices)} total voices.") # 调试打印

        # 如果有可用的声音
        if all_voices:
            # 为每个显示名称创建 CTkButton (选项)
            for display_name, full_name in all_voices:
                option_button = ctk.CTkButton(
                    self.voice_options_frame, 
                    text=display_name, 
                    anchor="w",
                    fg_color="transparent",
                    hover_color="#e0e0e0",
                    text_color=("gray10", "gray90"),
                    # 点击选项按钮时，调用 _select_voice_option 并传递完整名称
                    command=lambda fn=full_name: self._select_voice_option(fn) 
                )
                option_button.pack(fill="x", padx=2, pady=1)

            # --- 确定应该默认选中的完整名称 ---
            full_name_to_select = None
            # 尝试保持当前选中的完整名称 (如果它仍然可用)
            if self.current_full_voice_name and self.current_full_voice_name in self.voice_display_to_full_map.values():
                full_name_to_select = self.current_full_voice_name
            elif DEFAULT_VOICE in self.voice_display_to_full_map.values():
                # 否则，如果默认声音可用，则选中它
                full_name_to_select = DEFAULT_VOICE
            elif all_voices:
                # 否则，选中列表中的第一个
                full_name_to_select = all_voices[0][1] # 获取第一个声音的完整名称

            # --- 根据确定的完整名称，找到对应的显示名称 ---
            display_name_to_set = "选择声音" # 默认文本
            if full_name_to_select:
                 # 反向查找显示名称 (效率不高，但对于少量选项可行)
                 for dn, fn in self.voice_display_to_full_map.items():
                     if fn == full_name_to_select:
                         display_name_to_set = dn
                         break
                 # 如果找不到（理论上不应该），则使用完整名称的一部分
                 if display_name_to_set == "选择声音":
                     name_part_match = re.search(r", (.*Neural)\)$", full_name_to_select)
                     display_name_to_set = name_part_match.group(1) if name_part_match else full_name_to_select

            # --- 更新存储的完整名称和触发按钮的文本 ---
            self.current_full_voice_name = full_name_to_select
            print(f"DEBUG _update_options: Setting current_full_voice_name = {self.current_full_voice_name}") # 调试打印
            self.selected_voice_button.configure(text=display_name_to_set, state="normal") # 更新按钮文本并启用
            print(f"DEBUG _update_options: Setting button text = {display_name_to_set}") # 调试打印

        # 如果没有可用的声音
        else: 
            label = ctk.CTkLabel(self.voice_options_frame, text="无可用声音")
            label.pack(fill="x", padx=5, pady=2)
            self.current_full_voice_name = None
            print(f"DEBUG _update_options: No voices available, setting current_full_voice_name = None") # 调试打印
            self.selected_voice_button.configure(text="无可用声音", state="disabled") # 更新按钮文本并禁用
            print(f"DEBUG _update_options: Setting button text = '无可用声音'") # 调试打印

    def _select_voice_option(self, full_name):
        """处理声音选项按钮的点击事件"""
        self.current_full_voice_name = full_name # 更新存储的完整名称
        
        # 从完整名称查找显示名称
        display_name = "未知声音" # 默认值
        for dn, fn in self.voice_display_to_full_map.items():
            if fn == full_name:
                display_name = dn
                break
        # 如果找不到（理论上不应该），则使用完整名称的一部分
        if display_name == "未知声音":
            name_part_match = re.search(r", (.*Neural)\)$", full_name)
            display_name = name_part_match.group(1) if name_part_match else full_name

        print(f"DEBUG _select_option: Selected {display_name}, Full name set to {self.current_full_voice_name}") # 调试打印

        # 更新触发按钮的文本
        self.selected_voice_button.configure(text=display_name)
        # 隐藏选项列表
        self.voice_options_frame.grid_forget()

    # --------------------------------------------------------------------------
    # 设置加载与保存
    # --------------------------------------------------------------------------
    def load_settings(self):
        """从 JSON 文件加载应用程序设置"""
        default_settings = {
            "copy_path_enabled": True,
            "autoplay_enabled": False,
            "monitor_enabled": False,
            "max_audio_files": DEFAULT_MAX_AUDIO_FILES,
            "selected_voice": DEFAULT_VOICE, # 保存上次选中的声音
            "rate": 0, # 保存语速
            "volume": 0 # 保存音量
        }
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    default_settings.update(settings)
                    # 加载上次选中的声音
                    self.current_full_voice_name = default_settings.get("selected_voice", DEFAULT_VOICE)
                    # 注意：这里不需要更新 selected_voices_full
                    return default_settings
        except (json.JSONDecodeError, IOError, Exception) as e:
            print(f"加载设置失败: {e}")
        # 如果加载失败或文件不存在，设置默认声音
        self.current_full_voice_name = DEFAULT_VOICE
        return default_settings

    def save_settings(self):
        """将当前应用程序设置保存到 JSON 文件"""
        settings_to_save = {
            "selected_voice": self.current_full_voice_name, # 保存当前选中的声音
            "copy_path_enabled": self.copy_to_clipboard_var.get(),
            "autoplay_enabled": self.play_audio_var.get(),
            "monitor_enabled": self.select_to_audio_var.get(),
            "max_audio_files": int(self.max_files_entry.get()) if self.max_files_entry.get().isdigit() else DEFAULT_MAX_AUDIO_FILES, # 保存缓存数量
            "rate": self.rate_slider_var.get(), # 保存语速
            "volume": self.volume_slider_var.get() # 保存音量
        }
        
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings_to_save, f, ensure_ascii=False, indent=4)
            print("设置已保存。")
        except (IOError, Exception) as e:
            print(f"保存设置失败: {e}")


    # --------------------------------------------------------------------------
    # 音频生成与处理方法
    # --------------------------------------------------------------------------
    def generate_audio_manual(self):
        """处理“生成音频”按钮点击事件"""
        text = self.text_input.get("1.0", "end").strip() # 获取输入文本
        if not text:
            self.update_status("错误：请输入文本", error=True, duration=5)
            return

        # --- 直接从 self.current_full_voice_name 获取完整名称 ---
        voice = self.current_full_voice_name # 获取存储的完整名称

        # 检查获取到的 voice 是否有效
        if not voice: # 只需要检查是否为 None
            self.update_status("错误：请在声音筛选菜单中至少选择一个声音", error=True, duration=5)
            return

        # 获取语速和音量设置
        rate_val = self.rate_slider_var.get()
        volume_val = self.volume_slider_var.get()
        rate_str = f"{rate_val:+}%"
        volume_str = f"{volume_val:+}%"
        pitch_str = "+0Hz" # 音高暂时固定

        # 调用带动画的生成方法
        self.generate_with_animation(text, voice, rate_str, volume_str, pitch_str)

    def generate_with_animation(self, text, voice, rate, volume, pitch):
        """
        生成音频，并在生成过程中禁用按钮、显示进度条。
        (voice 参数应为完整名)
        """
        self.generate_button.configure(state="disabled") # 禁用生成按钮
        # 提取声音显示名称用于状态栏提示
        display_voice_name = "未知"
        if voice: # 检查 voice 是否为 None
            # 反向查找显示名称
            for dn, fn in self.voice_display_to_full_map.items():
                if fn == voice:
                    display_voice_name = dn
                    break
            # 如果找不到，尝试用正则提取
            if display_voice_name == "未知":
                name_part_match = re.search(r", (.*Neural)\)$", voice)
                display_voice_name = name_part_match.group(1) if name_part_match else voice
        self.update_status(f"正在生成音频 (声音: {display_voice_name})...", permanent=True, show_progress=True)

        # 定义生成完成后的回调函数
        def on_complete(path, error_msg=None): 
            self.generate_button.configure(state="normal") # 重新启用生成按钮
            if path: # 如果生成成功
                self.update_status(f"生成成功: {os.path.basename(path)}", duration=10)
                print("音频生成完成:", path)
                # 如果启用了自动播放
                if self.play_audio_var.get(): 
                    try:
                        # 在新线程中播放音频，避免阻塞 UI
                        threading.Thread(target=lambda p=path: playsound(p), daemon=True).start()
                        print("音频播放已启动")
                    except Exception as e:
                        print(f"音频播放失败: {e}")
                        self.update_status(f"播放失败: {e}", error=True)
                # 如果启用了复制文件路径
                if self.copy_to_clipboard_var.get(): 
                    copy_file_to_clipboard(path) 
                    # 显示复制成功提示浮窗
                    if hasattr(self, 'show_ok_window'):
                        self.root.after(0, self.show_ok_window)
            else: # 如果生成失败
                err_str = f"音频生成失败: {error_msg}" if error_msg else "音频生成失败，请检查网络或声音选择。"
                print(err_str)
                self.update_status(err_str, error=True)
            # 关闭可能存在的复制生音频浮窗
            if self.float_window:
                try: self.float_window.destroy()
                except tk.TclError: pass
                self.float_window = None
            # 执行文件管理，清理旧文件
            manage_audio_files() # 在生成完成后清理

        # 调用后台生成音频函数，并传入回调
        generate_audio(text, voice, rate, volume, pitch, on_complete)

    # --------------------------------------------------------------------------
    # 浮窗相关方法
    # --------------------------------------------------------------------------
    def show_float_window(self, text):
        """在鼠标位置显示“音”字浮窗，用于触发复制生音频"""
        # 如果已存在旧浮窗，先销毁
        if self.float_window:
            try: self.float_window.destroy()
            except tk.TclError: pass 
            self.float_window = None
        # 创建新的顶层窗口
        self.float_window = tk.Toplevel(self.root)
        self.float_window.overrideredirect(True) # 隐藏窗口边框和标题栏
        x, y = self.last_mouse_pos # 获取最后记录的鼠标位置
        self.float_window.geometry(f"50x50+{x + 10}+{y + 10}") # 设置窗口位置
        self.float_window.attributes("-topmost", True) # 保持窗口在最前
        # 创建按钮
        float_button = ctk.CTkButton(
            self.float_window, text="音", width=50, height=50, corner_radius=25, 
            font=ctk.CTkFont(size=20, weight="bold"), fg_color="#1E90FF", 
            hover_color="#1C86EE", text_color="white",
            command=lambda t=text: self.trigger_generate_from_float(t) # 点击按钮触发生成
        )
        float_button.pack()
        # 设置定时器自动关闭浮窗
        def auto_close():
            if self.float_window:
                try: self.float_window.destroy()
                except tk.TclError: pass
                self.float_window = None 
        self.float_window.after(FLOAT_WINDOW_TIMEOUT * 1000, auto_close)
        
    def show_ok_window(self):
        """在鼠标位置显示红色的 'OK' 浮窗，提示复制成功"""
        # 如果已存在旧浮窗，先销毁
        if hasattr(self, 'ok_window') and self.ok_window:
            try: self.ok_window.destroy()
            except tk.TclError: pass
            self.ok_window = None
        # 创建新的顶层窗口
        self.ok_window = tk.Toplevel(self.root)
        self.ok_window.overrideredirect(True)
        x, y = self.last_mouse_pos
        self.ok_window.geometry(f"50x50+{x + 10}+{y + 10}")
        self.ok_window.attributes("-topmost", True)
        # 创建按钮
        ok_button = ctk.CTkButton(
            self.ok_window, text="OK", width=50, height=50, corner_radius=25,
            font=ctk.CTkFont(size=20, weight="bold"), fg_color="#DC143C", 
            hover_color="#B22222", text_color="white",
            command=lambda: self.ok_window.destroy() if self.ok_window else None # 点击关闭
        )
        ok_button.pack()
        # 设置定时器自动关闭浮窗
        def auto_close():
            if hasattr(self, 'ok_window') and self.ok_window:
                try: self.ok_window.destroy()
                except tk.TclError: pass
                self.ok_window = None 
        self.ok_window.after(MOUSE_TIP_TIMEOUT * 1000, auto_close)

    def trigger_generate_from_float(self, text):
        """处理浮窗按钮点击事件，触发音频生成"""
        print(f"通过浮窗触发生成: {text[:50]}...")
        # 关闭浮窗
        if self.float_window:
            try: self.float_window.destroy() 
            except tk.TclError: pass
            self.float_window = None

        # 获取当前选中的声音 (从 self.current_full_voice_name)
        voice = self.current_full_voice_name 
        if not voice: # 只需要检查是否为 None
             self.update_status("错误：请在声音筛选菜单中至少选择一个声音", error=True, duration=5)
             return
        # 获取语速和音量设置
        rate_val = self.rate_slider_var.get()
        volume_val = self.volume_slider_var.get()
        rate_str = f"{rate_val:+}%"
        volume_str = f"{volume_val:+}%"
        pitch_str = "+0Hz"

        # 调用带动画的生成方法
        self.generate_with_animation(text, voice, rate_str, volume_str, pitch_str)

    # --------------------------------------------------------------------------
    # 剪贴板监控方法
    # --------------------------------------------------------------------------
    def toggle_select_to_audio(self):
        """切换“启用复制生音频”开关的状态，启动或停止监控"""
        global clipboard_monitor_active
        if self.select_to_audio_switch.get(): # 如果开关打开
            if not clipboard_monitor_active: self.start_clipboard_monitor() # 如果监控未运行，则启动
        else: # 如果开关关闭
            self.stop_clipboard_monitor() # 停止监控
        self.save_settings() # 保存开关状态

    def start_clipboard_monitor(self):
        """启动剪贴板监控线程"""
        global clipboard_monitor_active
        if self.clipboard_thread and self.clipboard_thread.is_alive():
            print("剪贴板监控已在运行")
            return
        clipboard_monitor_active = True 
        print("启动剪贴板监控...")
        self.update_status("剪贴板监控已启用", duration=5)
        
        # 定义在后台线程中运行的监控函数
        def monitor_clipboard():
            global clipboard_monitor_active
            last_text = ""
            try: last_text = pyperclip.paste() # 获取初始剪贴板内容
            except Exception: pass
            
            while clipboard_monitor_active: # 循环监控，直到标志位变为 False
                try:
                    current_text = pyperclip.paste() # 获取当前剪贴板内容
                    # 如果内容非空、与上次不同且去除空格后非空
                    if current_text and current_text != last_text and current_text.strip():
                        sanitized = sanitize_text(current_text) # 清理文本
                        if sanitized:
                            last_text = current_text # 更新上次内容
                            print(f"检测到剪贴板变化: {sanitized[:50]}...")
                            
                            # 定义在主线程中显示浮窗的包装函数
                            def show_float_wrapper(txt=sanitized):
                                # 再次检查标志位和窗口是否存在
                                if clipboard_monitor_active and self.root.winfo_exists():
                                    # 获取当前鼠标位置
                                    self.last_mouse_pos = (self.root.winfo_pointerx(), self.root.winfo_pointery())
                                    print(f"复制时的鼠标位置: {self.last_mouse_pos}")
                                    # 显示浮窗
                                    self.show_float_window(txt)
                            
                            # 使用 after(0, ...) 将显示浮窗任务添加到 Tkinter 事件队列
                            if self.root.winfo_exists():
                                self.root.after(0, show_float_wrapper)
                                
                    time.sleep(0.5) # 每隔 0.5 秒检查一次
                except Exception as e: 
                    print(f"剪贴板监控错误: {e}")
                    time.sleep(1) # 出错时等待时间稍长
            print("剪贴板监控线程已停止。")

        # 启动监控线程
        self.clipboard_thread = threading.Thread(target=monitor_clipboard, daemon=True)
        self.clipboard_thread.start()

    def stop_clipboard_monitor(self):
        """停止剪贴板监控线程"""
        global clipboard_monitor_active
        if not clipboard_monitor_active:
            print("剪贴板监控未运行")
            return
        print("正在停止剪贴板监控...")
        clipboard_monitor_active = False # 设置标志位为 False，让线程循环结束
        # 关闭可能存在的浮窗
        if self.float_window:
            try: self.float_window.destroy()
            except tk.TclError: pass
            self.float_window = None
        if self.ok_window:
             try: self.ok_window.destroy()
             except tk.TclError: pass
             self.ok_window = None
        self.clipboard_thread = None # 清除线程引用
        self.update_status("剪贴板监控已禁用", duration=3)

    # --------------------------------------------------------------------------
    # 窗口关闭处理
    # --------------------------------------------------------------------------
    print("DEBUG: Defining on_closing method...") # 调试打印
    def on_closing(self):
        """处理窗口关闭事件：停止监控、保存设置、销毁窗口"""
        print("窗口关闭...")
        self.stop_clipboard_monitor() 
        self.save_settings() # 保存设置
        self.root.destroy() # 销毁主窗口

# ==============================================================================
# 程序入口点
# ==============================================================================
if __name__ == "__main__":
    # 创建主窗口
    root = ctk.CTk()
    # 创建应用程序实例
    app = EdgeTTSApp(root)
    # 进入 Tkinter 事件循环
    root.mainloop()
