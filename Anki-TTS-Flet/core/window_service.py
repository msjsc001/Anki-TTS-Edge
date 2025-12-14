import ctypes
import os
from ctypes import wintypes
import time

# Constants
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040

class WindowService:
    @staticmethod
    def set_always_on_top(enable: bool):
        """
        Sets the main application window to Always On Top (or not) using PID matching.
        This is more robust than finding by title because it targets THIS specific process.
        """
        target_pid = os.getpid()
        print(f"DEBUG: WindowService searching for visible windows of PID {target_pid}")
        
        found_hwnds = []

        def enum_windows_callback(hwnd, _):
            # Check if window belongs to our PID
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            
            if pid.value == target_pid:
                # Get Title
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                
                # Get Class Name (Crucial for Flet/Flutter)
                class_buff = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetClassNameW(hwnd, class_buff, 256)
                class_name = class_buff.value
                
                print(f"DEBUG: Found Window. PID={pid.value}, HWND={hwnd}, Visible={ctypes.windll.user32.IsWindowVisible(hwnd)}, Class='{class_name}', Title='{title}'")
                
                # Logic: Target visible windows OR specific Flutter class
                is_visible = ctypes.windll.user32.IsWindowVisible(hwnd)
                is_flutter = "FLUTTER" in class_name.upper()
                
                if (is_visible or is_flutter) and title: 
                     found_hwnds.append((hwnd, title, class_name))
            return True

        # Define Callback Type
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)

        if not found_hwnds:
            print("ERROR: WindowService found NO candidate windows for this PID.")
            return False

        success = False
        flag = HWND_TOPMOST if enable else HWND_NOTOPMOST
        
        for hwnd, title, class_name in found_hwnds:
            # print(f"DEBUG: Setting TopMost={enable} on HWND {hwnd} (Class: {class_name})") # Reduce spam
            try:
                # Force SWP_SHOWWINDOW to ensure it pops up if hidden?
                ctypes.windll.user32.SetWindowPos(hwnd, flag, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
                success = True
            except Exception as e:
                print(f"ERROR: Failed to set window pos for {hwnd}: {e}")
                
        return success

    # Persist Pinning State Logic
    _pinning_thread = None
    _stop_pinning = None
    
    @classmethod
    def start_pinning_loop(cls, enable: bool):
        """
        Starts or stops a background thread that continually asserts the Always-On-Top state.
        This overcomes frameworks/OS events that might reset the Z-order.
        """
        import threading
        
        # Stop existing thread if any
        if cls._stop_pinning:
            cls._stop_pinning.set()
            if cls._pinning_thread and cls._pinning_thread.is_alive():
                 cls._pinning_thread.join(timeout=1.0)
            cls._stop_pinning = None
            cls._pinning_thread = None
            
        if not enable:
            # Just ensure it is turned off once
            cls.set_always_on_top(False)
            print("DEBUG: Pinning Loop Stopped.")
            return

        # Start new thread
        cls._stop_pinning = threading.Event()
        
        def _loop():
            print("DEBUG: Pinning Loop Started.")
            while not cls._stop_pinning.is_set():
                cls.set_always_on_top(True)
                time.sleep(0.5) # Re-assert every 500ms
            print("DEBUG: Pinning Loop Exited.")

        cls._pinning_thread = threading.Thread(target=_loop, daemon=True)
        cls._pinning_thread.start()
