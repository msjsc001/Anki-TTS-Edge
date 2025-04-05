# main.py
# Main entry point for the Anki-TTS-Edge application.

import sys
import os # Needed for check_dependencies
import ctypes
import customtkinter as ctk
import pygame # Needed for quit check

# Import necessary components from our modules
import config # To load config and translations first
# Removed: from utils import check_dependencies
from ui import EdgeTTSApp # The main UI class

# ==============================================================================
# <<<<<<< 添加: 依赖检查函数 (从 utils 移动过来) >>>>>>>>>
# ==============================================================================
def check_dependencies():
    """检查所有依赖库是否安装"""
    # This check relies on imports happening correctly later, which isn't ideal for strict checking
    # but necessary to avoid loading modules too early. A better approach might be a separate setup script.
    dependencies = { "customtkinter": "pip install customtkinter", "edge_tts": "pip install edge-tts", "pyperclip": "pip install pyperclip", "pygame": "pip install pygame", "pynput": "pip install pynput", "win32clipboard": "pip install pywin32", "win32con": "pip install pywin32" }
    missing = []; checked_pywin32 = False
    print("正在检查依赖库...") # Add print to show it's running
    for module, install_cmd in dependencies.items():
        try:
            # Simple import check - might not catch all submodule issues
            if module == "pynput": from pynput import mouse, keyboard # Specific check
            elif module.startswith("win32"):
                 if not checked_pywin32: __import__("win32clipboard"); checked_pywin32 = True
            else: __import__(module)
            # print(f"  {module}: OK") # Optional: Show successful checks
        except ImportError:
            # print(f"  {module}: MISSING") # Optional: Show missing checks
            if module.startswith("win32"):
                if not checked_pywin32: missing.append((module, install_cmd)); checked_pywin32 = True
            else: missing.append((module, install_cmd))
    if missing:
        print("\n错误：以下依赖库未安装："); install_cmds = set()
        for module, install_cmd in missing: print(f"- {module}"); install_cmds.add(install_cmd)
        print("\n请确保在激活的虚拟环境 (.venv) 中安装以上依赖库后重新运行脚本。")
        print(f"建议安装命令: {' '.join(install_cmds)}"); sys.exit(1)
    else: print("所有依赖库已安装！")
# ==============================================================================

# --- Global App Reference ---
app = None # This will be populated after EdgeTTSApp is instantiated

# --- Main Execution ---
if __name__ == "__main__":
    # 1. <<<<<<< 修改: 直接调用检查函数 >>>>>>>>>
    check_dependencies()

    # 2. Set DPI Awareness (Windows specific)
    try:
        if sys.platform == "win32": ctypes.windll.shcore.SetProcessDpiAwareness(1) # System Aware
    except Exception as e: print(f"设置 DPI 感知失败: {e}")

    # 3. Create the main Tkinter window
    root = ctk.CTk()

    # 4. Instantiate the Application UI
    try:
        app_instance = EdgeTTSApp(root)
        # Set the global 'app' reference *after* instantiation
        app = app_instance
    except Exception as e:
         print(f"CRITICAL ERROR: Failed to initialize EdgeTTSApp: {e}")
         try: tk.messagebox.showerror("Application Error", f"Failed to initialize application:\n{e}")
         except: pass
         if pygame.get_init(): pygame.quit()
         sys.exit(1)

    # 5. Start the Tkinter main loop
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("用户中断程序。")
        if app: app.on_closing()
        else:
             if pygame.get_init(): pygame.quit()
             try: root.destroy()
             except: pass
    finally:
        print("程序退出。")
        if pygame.get_init(): pygame.quit()