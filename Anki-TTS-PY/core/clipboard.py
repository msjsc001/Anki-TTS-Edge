import time
import threading
import math
import pyperclip
from pynput import mouse, keyboard
from config.constants import MOUSE_DRAG_THRESHOLD
from config.settings import settings_manager
from utils.text import sanitize_text
from utils.i18n import i18n

class MonitorManager:
    def __init__(self, on_clipboard_change=None, on_selection_trigger=None):
        self.clipboard_monitor_active = False
        self.clipboard_polling_thread = None
        self.mouse_listener_thread = None
        self.mouse_listener = None
        self.previous_clipboard_content = None
        
        # Callbacks
        self.on_clipboard_change = on_clipboard_change
        self.on_selection_trigger = on_selection_trigger
        
        # Mouse state
        self.is_dragging = False
        self.drag_start_pos = (0, 0)
        self.drag_start_time = 0

    def start_monitors(self):
        """Starts monitoring threads based on settings."""
        if self.clipboard_monitor_active:
            self._adjust_running_monitors()
            return

        self.clipboard_monitor_active = True
        print(i18n.get("debug_monitor_start"))

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
        # Threads will exit naturally when they see clipboard_monitor_active is False

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
                    
                    # Trigger logic for Clipboard Monitor
                    if clipboard_enabled and current_text and current_text.strip() and current_text != self.previous_clipboard_content:
                        sanitized = sanitize_text(current_text)
                        if sanitized:
                            print(i18n.get("debug_new_clipboard_content", sanitized[:50]))
                            self.previous_clipboard_content = current_text
                            if self.on_clipboard_change:
                                self.on_clipboard_change(sanitized)
                        else:
                            self.previous_clipboard_content = current_text
                    
                    # Update content for Selection Monitor (to detect copy after selection)
                    elif current_text != self.previous_clipboard_content:
                        self.previous_clipboard_content = current_text
                    
                    time.sleep(0.5)
                except Exception as e:
                    print(i18n.get("debug_poll_clipboard_error", e))
                    time.sleep(1)

        self.clipboard_polling_thread = threading.Thread(target=poll, daemon=True)
        self.clipboard_polling_thread.start()

    def _start_mouse_listener_thread(self):
        if self.mouse_listener_thread and self.mouse_listener_thread.is_alive():
            return

        def on_click(x, y, button, pressed):
            if not settings_manager.get("monitor_selection_enabled"):
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
                            
                            if dist > MOUSE_DRAG_THRESHOLD:
                                print(i18n.get("debug_selection_detected"))
                                if self.on_selection_trigger:
                                    self.on_selection_trigger(release_pos)
                        except Exception as e:
                            print(i18n.get("debug_mouse_release_error", e))

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

    def simulate_copy(self):
        """Simulates Ctrl+C."""
        if not settings_manager.get("monitor_selection_enabled"):
            return
        try:
            time.sleep(0.15)
            print(i18n.get("debug_simulate_copy"))
            controller = keyboard.Controller()
            with controller.pressed(keyboard.Key.ctrl):
                controller.press('c')
                controller.release('c')
            print(i18n.get("debug_simulate_copy_complete"))
        except Exception as e:
            print(i18n.get("debug_simulate_copy_error", e))

# Global instance could be created here, or instantiated in main_window