import time
import threading
import math
import multiprocessing
import pyperclip
from pynput import mouse, keyboard
from config.constants import MOUSE_DRAG_THRESHOLD
from config.settings import settings_manager
from utils.text import sanitize_text
from utils.i18n import i18n
from core.satellite import run_satellite
import logging

logging.basicConfig(
    filename='monitor_debug.log', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

class MonitorManager:
    def __init__(self, on_clipboard_change=None, on_selection_trigger=None):
        self.clipboard_monitor_active = False
        self.clipboard_polling_thread = None
        self.mouse_listener_thread = None
        self.mouse_listener = None
        self.previous_clipboard_content = None
        self._startup_time = time.time()
        self._ignore_until_time = self._startup_time + 4.0  # Strict ignore period during startup
        self._skip_initial_clipboard = True  # Logic flag to skip first poll
        self._selection_triggered = False  # Flag to track if clipboard change was from selection
        
        # Satellite State
        self.sat_input_q = multiprocessing.Queue()
        self.sat_output_q = multiprocessing.Queue()
        self.sat_process = None
        self._start_satellite()
        
        # Callbacks
        self.on_clipboard_change = on_clipboard_change
        self.on_selection_trigger = on_selection_trigger
        
        # Mouse state
        self.is_dragging = False
        self.drag_start_pos = (0, 0)
        self.drag_start_time = 0

    def _start_satellite(self):
        if self.sat_process and self.sat_process.is_alive():
            return
        self.sat_process = multiprocessing.Process(target=run_satellite, args=(self.sat_input_q, self.sat_output_q), daemon=True)
        self.sat_process.start()
        logging.info("Satellite Process Started")

    def start_monitors(self):
        """Starts monitoring threads based on settings."""
        if self.clipboard_monitor_active:
            self._adjust_running_monitors()
            return

        self.clipboard_monitor_active = True
        print(i18n.get("debug_monitor_start"))
        logging.info(f"Starting Monitors. Selection Enabled: {settings_manager.get('monitor_selection_enabled')}")

        self._start_clipboard_polling_thread()
        self._start_mouse_listener_thread()

    def stop_monitors(self):
        """Stops all monitoring threads."""
        if not self.clipboard_monitor_active:
            return

        print(i18n.get("debug_monitor_stop"))
        self.clipboard_monitor_active = False

        if self.mouse_listener and self.mouse_listener.is_alive():
            try:
                self.mouse_listener.stop()
            except Exception as e:
                print(i18n.get("debug_mouse_listener_stop_error", e))
        
        self.mouse_listener = None
        
        # Stop Satellite
        if self.sat_process:
            try:
                self.sat_input_q.put(("EXIT",))
                # self.sat_process.join(timeout=1) # Don't block too long
                self.sat_process = None
            except: pass

    def _adjust_running_monitors(self):
        """Adjusts monitors without full restart."""
        clipboard_needed = settings_manager.get("monitor_clipboard_enabled") or settings_manager.get("monitor_selection_enabled")
        mouse_needed = settings_manager.get("monitor_selection_enabled")
        
        # Clipboard Thread Logic
        is_clip_running = self.clipboard_polling_thread and self.clipboard_polling_thread.is_alive()
        if clipboard_needed and not is_clip_running:
             self._start_clipboard_polling_thread()
        
        # Mouse Thread Logic
        is_mouse_running = self.mouse_listener_thread and self.mouse_listener_thread.is_alive()
        if mouse_needed and not is_mouse_running:
            self._start_mouse_listener_thread()
        elif not mouse_needed and is_mouse_running:
             if self.mouse_listener:
                 try: self.mouse_listener.stop() 
                 except: pass

    def _start_clipboard_polling_thread(self):
        if self.clipboard_polling_thread and self.clipboard_polling_thread.is_alive():
            return
            
        try:
            self.previous_clipboard_content = pyperclip.paste()
        except Exception as e:
            print(i18n.get("debug_initial_paste_error", e))
            self.previous_clipboard_content = ""

        def poll():
            while self.clipboard_monitor_active:
                clipboard_enabled = settings_manager.get("monitor_clipboard_enabled")
                selection_enabled = settings_manager.get("monitor_selection_enabled")
                
                if not clipboard_enabled and not selection_enabled:
                    time.sleep(1)
                    continue

                try:
                    current_text = pyperclip.paste()
                    now = time.time()
                    
                    # 1. Startup Protection
                    if now < self._ignore_until_time:
                         # Still in startup "warmup" period
                         self.previous_clipboard_content = current_text
                         time.sleep(0.5)
                         continue

                    # 2. Logic Skip (First valid poll)
                    if self._skip_initial_clipboard:
                        if not self._selection_triggered:
                            self._skip_initial_clipboard = False
                            self.previous_clipboard_content = current_text
                            time.sleep(0.5)
                            continue
                        else:
                            # Selection triggered! Cancel skip and process this text.
                            # Even if it's the very first poll, if USER clicked blue dot, we respect it.
                            logging.debug("Initial skip cancel: Selection Triggered!")
                            self._skip_initial_clipboard = False
                    
                    # 3. Handle Changes
                    
                    # Priority: Handle selection-triggered clipboard changes FIRST
                    # This ensures blue dot selection works even if clipboard monitor is disabled
                    if self._selection_triggered:
                        # Logic: If triggered, we process whatever is in clipboard (if sanitized)
                        # We don't care if it equals previous content (user might want to re-process same text)
                        self._selection_triggered = False  # Reset flag
                        sanitized = sanitize_text(current_text)
                        
                        if sanitized:
                             logging.debug(f"Selection-triggered Clipboard: {sanitized[:50]}")
                             self.previous_clipboard_content = current_text
                             if self.on_clipboard_change:
                                 self.on_clipboard_change(sanitized)
                        else:
                             # Empty or invalid selection
                             logging.debug("Selection Triggered but text empty/invalid.")
                    
                    # Normal Clipboard Monitor logic (only if clipboard_enabled is ON)
                    elif clipboard_enabled and current_text and current_text != self.previous_clipboard_content:
                        sanitized = sanitize_text(current_text)
                        
                        # Only trigger if text is valid AND changed
                        if sanitized:
                            logging.debug(f"New Clipboard Content: {sanitized[:50]}")
                            self.previous_clipboard_content = current_text
                            if self.on_clipboard_change:
                                self.on_clipboard_change(sanitized)
                        else:
                            # Just update reference if invalid
                            self.previous_clipboard_content = current_text
                    
                    # Update previous content if changed (but ignored above)
                    elif current_text != self.previous_clipboard_content:
                         self.previous_clipboard_content = current_text

                    time.sleep(0.5)
                except Exception as e:
                    logging.error(f"Poll Error: {e}")
                    time.sleep(1)

        self.clipboard_polling_thread = threading.Thread(target=poll, daemon=True)
        self.clipboard_polling_thread.start()

    def _start_mouse_listener_thread(self):
        if self.mouse_listener_thread and self.mouse_listener_thread.is_alive():
            return

        def on_click(x, y, button, pressed):
            # logging.debug(f"Mouse click: {x},{y}, {button}, {pressed}") # Too verbose?
            enabled = settings_manager.get("monitor_selection_enabled")
            if not enabled:
                return

            if button == mouse.Button.left:
                if pressed:
                    self.is_dragging = True
                    self.drag_start_pos = (x, y)
                    self.drag_start_time = time.time()
                else:
                    if self.is_dragging:
                        self.is_dragging = False
                        release_pos = (x, y)
                        try:
                            dist = math.sqrt((release_pos[0] - self.drag_start_pos[0])**2 + 
                                           (release_pos[1] - self.drag_start_pos[1])**2)
                            logging.debug(f"Mouse Release: dist={dist}, thresh={MOUSE_DRAG_THRESHOLD}")
                            if dist > MOUSE_DRAG_THRESHOLD:
                                logging.debug(f"Selection Detected. Dist={dist}. Calling Trigger.")
                                if self.on_selection_trigger:
                                    self.on_selection_trigger(release_pos)
                            else:
                                logging.debug(f"Mouse Drag too short: {dist}")
                        except Exception as e:
                            logging.error(f"Mouse Release Error: {e}")

        def listen():
            # Use local variable for join to avoid race condition with stop_monitors setting self.mouse_listener to None
            listener = mouse.Listener(on_click=on_click)
            self.mouse_listener = listener
            try:
                listener.start()
                listener.join()
            except Exception as e:
                 print(f"Mouse listener error: {e}")

        self.mouse_listener_thread = threading.Thread(target=listen, daemon=True)
        self.mouse_listener_thread.start()

    def simulate_copy(self, mouse_pos=None):
        """Simulates Ctrl+C using reliable ctypes (win32 API)."""
        if not settings_manager.get("monitor_selection_enabled"):
            logging.debug("Simulate Copy called but Monitor Disabled.")
            return
        try:
            # Set flag to indicate this is a selection-triggered copy
            self._selection_triggered = True
            
            time.sleep(0.1) # Reduced from 0.3s for responsiveness
            logging.debug("Executing Simulate Copy (ctypes)...")
            
            # Robust Win32 injection
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            
            INPUT_KEYBOARD = 1
            KEYEVENTF_KEYUP = 0x0002
            VK_CONTROL = 0x11
            VK_C = 0x43
            
            class KEYBDINPUT(ctypes.Structure):
                _fields_ = (("wVk", wintypes.WORD),
                            ("wScan", wintypes.WORD),
                            ("dwFlags", wintypes.DWORD),
                            ("time", wintypes.DWORD),
                            ("dwExtraInfo", ctypes.c_ulonglong))
            
            class INPUT(ctypes.Structure):
                _fields_ = (("type", wintypes.DWORD),
                            ("ki", KEYBDINPUT))
                            
            def _send_key(vk, flags=0):
                inp = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, time=0, dwExtraInfo=0))
                user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

            # 0. CLEAR Clipboard to define "Success" as "Non-Empty"
            # This handles the race condition: if we read old data, it fails.
            try:
                pyperclip.copy("") 
            except: pass
            
            time.sleep(0.05)
            
            # 1. Press Ctrl
            _send_key(VK_CONTROL, 0)
            time.sleep(0.02) # Safer delay
            # 2. Press C
            _send_key(VK_C, 0)
            time.sleep(0.02)
            # 3. Release C
            _send_key(VK_C, KEYEVENTF_KEYUP)
            time.sleep(0.02)
            # 4. Release Ctrl
            _send_key(VK_CONTROL, KEYEVENTF_KEYUP)
            
            # Force Trigger Callback to ensure UI pops even if text is identical to previous
            time.sleep(0.05)
            
            # Retry loop for robust clipboard fetching
            # STRATEGY: Wait for content to become NON-EMPTY.
            # Since we cleared it, any content implies a successful new copy.
            current = ""
            sanitized = ""
            found_new = False
            
            for i in range(15): # 15 * 0.05 = 0.75s max wait
                try:
                    current = pyperclip.paste()
                    if current:
                         # Found content!
                         sanitized = sanitize_text(current)
                         if sanitized:
                             found_new = True
                             break
                except Exception as ex:
                     print(f"DEBUG: Paste Exception: {ex}")
                time.sleep(0.05)
                
            if not found_new and current:
                 # Fallback: Just use whatever we have (maybe whitespace?)
                 sanitized = sanitize_text(current)

            # Fallback for Terminal/Stubborn Apps
            if not sanitized:
                print("DEBUG: Primary Copy Failed (Clipboard Empty). Trying Pynput Fallback...")
                try:
                    controller = keyboard.Controller()
                    with controller.pressed(keyboard.Key.ctrl):
                        controller.press('c')
                        controller.release('c')
                    time.sleep(0.2)
                    
                    # Retry Fetch
                    current = pyperclip.paste()
                    if current:
                         sanitized = sanitize_text(current)
                         print(f"DEBUG: Fallback sanitized: {sanitized[:10] if sanitized else 'None'}")
                except Exception as e:
                    print(f"DEBUG: Fallback Error: {e}")

            if current:
                if sanitized:
                    # Satellite Trigger
                    if mouse_pos:
                        x, y = mouse_pos
                        is_dual = settings_manager.get("dual_blue_dot_enabled", False)
                        self.sat_input_q.put(("SHOW", sanitized, x + 10, y - 40, is_dual)) 
                        logging.info(f"Sent SHOW to Satellite: {sanitized[:10]} at {x},{y}, Dual={is_dual}")
                    
                    # Store as previous so Monitor loop doesn't re-trigger
                    self.previous_clipboard_content = current

        except Exception as e:
            print(i18n.get("debug_simulate_copy_error", e))
            # Fallback to pynput just in case
            try:
                controller = keyboard.Controller()
                with controller.pressed(keyboard.Key.ctrl):
                    controller.press('c')
                    controller.release('c')
            except: pass

# Global instance could be created here, or instantiated in main_window