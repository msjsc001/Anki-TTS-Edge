import sys
import os
import ctypes
import customtkinter as ctk

# Add current directory to sys.path to allow imports from subdirectories
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow

def main():
    # Set DPI Awareness for Windows and AppUserModelID
    try:
        if sys.platform == "win32":
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            
            # Set AppUserModelID to ensure taskbar icon shows correctly
            myappid = 'mycompany.ankittsedge.v1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"Failed to set DPI awareness or AppUserModelID: {e}")

    # Initialize Root Window
    root = ctk.CTk()
    
    # Initialize Main App Logic
    app = MainWindow(root)
    
    # Start Main Loop
    try:
        print("启动 Tkinter 主循环...")
        root.mainloop()
    except KeyboardInterrupt:
        print("User interrupted.")
        app.quit_application()
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        print("Program exited.")

if __name__ == "__main__":
    main()