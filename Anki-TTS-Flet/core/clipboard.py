import time
import threading
import math
import multiprocessing
import ctypes
import pyperclip
import win32con
import win32gui
from ctypes import wintypes
from pynput import mouse, keyboard
from config.constants import MOUSE_DRAG_THRESHOLD
from config.settings import settings_manager
from utils.text import sanitize_text
from utils.i18n import i18n
from core.satellite import run_satellite
from core.files import capture_clipboard_snapshot, restore_clipboard_snapshot
import logging
from logging.handlers import RotatingFileHandler
from config.constants import LOG_FILE

_clipboard_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=1*1024*1024, backupCount=1, encoding='utf-8'
)
_clipboard_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.basicConfig(level=logging.DEBUG, handlers=[_clipboard_handler])

class MonitorManager:
    def __init__(self, on_clipboard_change=None, on_selection_trigger=None, on_selection_captured=None):
        self.clipboard_monitor_active = False
        self.clipboard_polling_thread = None
        self.mouse_listener_thread = None
        self.mouse_listener = None
        self.keyboard_listener_thread = None
        self.keyboard_listener = None
        self.previous_clipboard_content = None
        self._startup_time = time.time()
        self._ignore_until_time = self._startup_time + 1.2
        self._skip_initial_clipboard = True  # Logic flag to skip first poll
        self._selection_triggered = False  # Legacy flag kept for compatibility only
        self._ignore_internal_clipboard_until = 0
        self._ignore_internal_shortcuts_until = 0
        self._selection_capture_token = 0
        self._active_selection_capture_token = 0
        self._selection_capture_lock = threading.Lock()
        self._selection_simulation_lock = threading.Lock()
        self._pending_selection_token = 0
        self._active_pending_selection_token = 0
        self._pending_selection_lock = threading.Lock()
        self._selection_busy_lock = threading.Lock()
        self._selection_overlay_active = False
        self._selection_generation_active = False
        self._ctrl_pressed = False
        self._shift_pressed = False
        self._last_user_clipboard_shortcut_at = 0.0
        
        # Satellite State
        self.sat_input_q = multiprocessing.Queue()
        self.sat_output_q = multiprocessing.Queue()
        self.sat_process = None
        
        # Callbacks
        self.on_clipboard_change = on_clipboard_change
        self.on_selection_trigger = on_selection_trigger
        self.on_selection_captured = on_selection_captured
        
        # Mouse state
        self.is_dragging = False
        self.drag_start_pos = (0, 0)
        self.drag_start_time = 0

    def suppress_clipboard(self, duration=0.8):
        self._ignore_internal_clipboard_until = max(
            self._ignore_internal_clipboard_until,
            time.time() + duration,
        )

    def suppress_shortcuts(self, duration=0.8):
        self._ignore_internal_shortcuts_until = max(
            self._ignore_internal_shortcuts_until,
            time.time() + duration,
        )

    def _begin_selection_capture(self):
        with self._selection_capture_lock:
            self._selection_capture_token += 1
            self._active_selection_capture_token = self._selection_capture_token
            return self._active_selection_capture_token

    def _end_selection_capture(self, token):
        with self._selection_capture_lock:
            if self._active_selection_capture_token == token:
                self._active_selection_capture_token = 0

    def _selection_capture_active(self):
        with self._selection_capture_lock:
            return self._active_selection_capture_token != 0

    def set_selection_overlay_active(self, active):
        with self._selection_busy_lock:
            self._selection_overlay_active = bool(active)

    def set_selection_generation_active(self, active):
        with self._selection_busy_lock:
            self._selection_generation_active = bool(active)

    def selection_flow_busy(self):
        with self._selection_busy_lock:
            return self._selection_overlay_active or self._selection_generation_active

    def _cancel_pending_selection_trigger(self):
        with self._pending_selection_lock:
            self._active_pending_selection_token = 0

    def _schedule_selection_trigger(self, release_pos, delay=0.22):
        if not self.on_selection_trigger:
            return
        if self.selection_flow_busy():
            logging.debug("Selection trigger ignored because selection flow is busy.")
            return

        with self._pending_selection_lock:
            self._pending_selection_token += 1
            token = self._pending_selection_token
            self._active_pending_selection_token = token

        scheduled_at = time.time()

        def _worker():
            time.sleep(delay)
            with self._pending_selection_lock:
                if self._active_pending_selection_token != token:
                    return
                self._active_pending_selection_token = 0

            if self.selection_flow_busy():
                logging.debug("Selection trigger cancelled because selection flow is busy.")
                return

            if self._last_user_clipboard_shortcut_at >= scheduled_at:
                logging.debug("Selection trigger cancelled due to user Ctrl+C/X shortcut.")
                return

            self._selection_triggered = True
            self.on_selection_trigger(release_pos)

        threading.Thread(target=_worker, daemon=True).start()

    def _emit_clipboard_change(self, text, source):
        if not self.on_clipboard_change or not text:
            return
        try:
            self.on_clipboard_change(text, source)
        except TypeError:
            self.on_clipboard_change(text)

    def _emit_selection_captured(self, text):
        if not self.on_selection_captured or not text:
            return
        try:
            self.on_selection_captured(text)
        except TypeError:
            self.on_selection_captured(text, "selection")

    def _record_user_clipboard_action(self, action_name):
        self._last_user_clipboard_shortcut_at = time.time()
        self._cancel_pending_selection_trigger()
        logging.debug(f"User clipboard action detected: {action_name}")

    def _start_satellite(self):
        if self.sat_process and self.sat_process.is_alive():
            return
        self.sat_process = multiprocessing.Process(target=run_satellite, args=(self.sat_input_q, self.sat_output_q), daemon=True)
        self.sat_process.start()
        logging.info("Satellite Process Started")

    def start_monitors(self):
        """Starts monitoring threads based on settings."""
        clipboard_needed = settings_manager.get("monitor_clipboard_enabled")
        mouse_needed = settings_manager.get("monitor_selection_enabled")

        if not clipboard_needed and not mouse_needed:
            self.stop_monitors()
            return

        if self.clipboard_monitor_active:
            self._adjust_running_monitors()
            return

        self.clipboard_monitor_active = True
        print(i18n.get("debug_monitor_start"))
        logging.info(f"Starting Monitors. Selection Enabled: {settings_manager.get('monitor_selection_enabled')}")

        if clipboard_needed:
            self._start_clipboard_polling_thread()
        if mouse_needed:
            self._start_satellite()
            self._start_mouse_listener_thread()
            self._start_keyboard_listener_thread()

    def stop_monitors(self):
        """Stops all monitoring threads."""
        if not self.clipboard_monitor_active:
            return

        print(i18n.get("debug_monitor_stop"))
        self.clipboard_monitor_active = False
        self.set_selection_overlay_active(False)
        self.set_selection_generation_active(False)

        if self.mouse_listener and self.mouse_listener.is_alive():
            try:
                self.mouse_listener.stop()
            except Exception as e:
                print(i18n.get("debug_mouse_listener_stop_error", e))
        
        self.mouse_listener = None
        self._cancel_pending_selection_trigger()

        if self.keyboard_listener and self.keyboard_listener.is_alive():
            try:
                self.keyboard_listener.stop()
            except Exception:
                pass
        self.keyboard_listener = None
        
        # Stop Satellite
        if self.sat_process:
            try:
                self.sat_input_q.put(("EXIT",))
                self.sat_process = None
            except Exception:
                pass

    def stop(self):
        """Alias for stop_monitors() — used by handle_app_restart."""
        self.stop_monitors()

    def _adjust_running_monitors(self):
        """Adjusts monitors without full restart."""
        clipboard_needed = settings_manager.get("monitor_clipboard_enabled")
        mouse_needed = settings_manager.get("monitor_selection_enabled")

        if not clipboard_needed and not mouse_needed:
            self.stop_monitors()
            return
        
        # Clipboard Thread Logic
        is_clip_running = self.clipboard_polling_thread and self.clipboard_polling_thread.is_alive()
        if clipboard_needed and not is_clip_running:
             self._start_clipboard_polling_thread()
        
        # Mouse Thread Logic
        is_mouse_running = self.mouse_listener_thread and self.mouse_listener_thread.is_alive()
        if mouse_needed and not is_mouse_running:
            self._start_satellite()
            self._start_mouse_listener_thread()
            self._start_keyboard_listener_thread()
        elif not mouse_needed and is_mouse_running:
             if self.mouse_listener:
                 try: self.mouse_listener.stop() 
                 except Exception: pass
             self.mouse_listener = None
             self._cancel_pending_selection_trigger()

        is_keyboard_running = self.keyboard_listener_thread and self.keyboard_listener_thread.is_alive()
        if mouse_needed and not is_keyboard_running:
            self._start_keyboard_listener_thread()
        elif not mouse_needed and is_keyboard_running:
            if self.keyboard_listener:
                try:
                    self.keyboard_listener.stop()
                except Exception:
                    pass
            self.keyboard_listener = None

        if not mouse_needed and self.sat_process:
            try:
                self.sat_input_q.put(("EXIT",))
            except Exception:
                pass
            self.sat_process = None

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
                
                if not clipboard_enabled:
                    time.sleep(1)
                    continue

                try:
                    current_text = pyperclip.paste()
                    now = time.time()

                    if self._selection_capture_active():
                        self.previous_clipboard_content = current_text
                        time.sleep(0.05)
                        continue

                    if now < self._ignore_internal_clipboard_until:
                        self.previous_clipboard_content = current_text
                        time.sleep(0.08)
                        continue
                    
                    # 1. Startup Protection
                    if now < self._ignore_until_time:
                         # Still in startup "warmup" period
                         self.previous_clipboard_content = current_text
                         time.sleep(0.2)
                         continue

                    # 2. Logic Skip (First valid poll)
                    if self._skip_initial_clipboard:
                        if not self._selection_triggered:
                            self._skip_initial_clipboard = False
                            self.previous_clipboard_content = current_text
                            time.sleep(0.2)
                            continue
                        else:
                            # Selection triggered! Cancel skip and process this text.
                            # Even if it's the very first poll, if USER clicked blue dot, we respect it.
                            logging.debug("Initial skip cancel: Selection Triggered!")
                            self._skip_initial_clipboard = False
                    
                    # 3. Handle Changes
                    if clipboard_enabled and current_text and current_text != self.previous_clipboard_content:
                        sanitized = sanitize_text(current_text)
                        
                        # Only trigger if text is valid AND changed
                        if sanitized:
                            logging.debug(f"New Clipboard Content: {sanitized[:50]}")
                            self.previous_clipboard_content = current_text
                            self._emit_clipboard_change(sanitized, "clipboard")
                        else:
                            # Just update reference if invalid
                            self.previous_clipboard_content = current_text
                    
                    # Update previous content if changed (but ignored above)
                    elif current_text != self.previous_clipboard_content:
                         self.previous_clipboard_content = current_text

                    time.sleep(0.2)
                except Exception as e:
                    logging.error(f"Poll Error: {e}")
                    time.sleep(0.4)

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

            if button == mouse.Button.right and pressed:
                self._record_user_clipboard_action("right_click_context")
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
                                logging.debug(f"Selection Detected. Dist={dist}. Scheduling Trigger.")
                                self._schedule_selection_trigger(release_pos)
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

    def _start_keyboard_listener_thread(self):
        if self.keyboard_listener_thread and self.keyboard_listener_thread.is_alive():
            return

        def on_press(key):
            now = time.time()
            if now < self._ignore_internal_shortcuts_until:
                return

            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self._ctrl_pressed = True
                return
            if key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
                self._shift_pressed = True
                return

            if self._ctrl_pressed:
                key_char = getattr(key, "char", None)
                if key_char and key_char.lower() in {"c", "x", "v"}:
                    self._record_user_clipboard_action(f"ctrl+{key_char.lower()}")
                    return
                if key == keyboard.Key.insert:
                    self._record_user_clipboard_action("ctrl+insert")
                    return

            if self._shift_pressed:
                if key == keyboard.Key.insert:
                    self._record_user_clipboard_action("shift+insert")
                    return
                if key == keyboard.Key.delete:
                    self._record_user_clipboard_action("shift+delete")
                    return

        def on_release(key):
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self._ctrl_pressed = False
            elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
                self._shift_pressed = False

        def listen():
            listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self.keyboard_listener = listener
            try:
                listener.start()
                listener.join()
            except Exception as e:
                logging.error(f"Keyboard listener error: {e}")

        self.keyboard_listener_thread = threading.Thread(target=listen, daemon=True)
        self.keyboard_listener_thread.start()

    def _get_focused_hwnd(self):
        class GUITHREADINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("hwndActive", wintypes.HWND),
                ("hwndFocus", wintypes.HWND),
                ("hwndCapture", wintypes.HWND),
                ("hwndMenuOwner", wintypes.HWND),
                ("hwndMoveSize", wintypes.HWND),
                ("hwndCaret", wintypes.HWND),
                ("rcCaret", wintypes.RECT),
            ]

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        gui = GUITHREADINFO(cbSize=ctypes.sizeof(GUITHREADINFO))
        if user32.GetGUIThreadInfo(0, ctypes.byref(gui)):
            return gui.hwndFocus or gui.hwndActive
        return None

    def _try_extract_selection_without_clipboard(self):
        hwnd = self._get_focused_hwnd()
        if not hwnd:
            return ""

        try:
            class_name = win32gui.GetClassName(hwnd)
        except Exception:
            return ""

        if "Edit" not in class_name and "RICHEDIT" not in class_name.upper():
            return ""

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        EM_GETSEL = 0x00B0
        WM_GETTEXT = 0x000D
        WM_GETTEXTLENGTH = 0x000E

        start = wintypes.DWORD()
        end = wintypes.DWORD()
        user32.SendMessageW(hwnd, EM_GETSEL, ctypes.byref(start), ctypes.byref(end))
        if end.value <= start.value:
            return ""

        text_length = user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0)
        if text_length <= 0:
            return ""

        buffer = ctypes.create_unicode_buffer(text_length + 1)
        user32.SendMessageW(hwnd, WM_GETTEXT, text_length + 1, ctypes.byref(buffer))
        return sanitize_text(buffer.value[start.value:end.value])

    def simulate_copy(self, mouse_pos=None):
        """Try non-intrusive selection capture first, then fall back to Ctrl+C with clipboard restore."""
        if not settings_manager.get("monitor_selection_enabled"):
            logging.debug("Simulate Copy called but Monitor Disabled.")
            return
        if self.selection_flow_busy():
            logging.debug("Selection capture skipped because selection flow is busy.")
            return
        if not self._selection_simulation_lock.acquire(blocking=False):
            logging.debug("Selection capture skipped because a previous capture is still running.")
            return
        capture_token = None
        snapshot = None
        previous_text = ""
        selection_started_at = time.time()
        try:
            direct_text = self._try_extract_selection_without_clipboard()
            if direct_text:
                logging.debug("Selection captured without clipboard access.")
                if mouse_pos:
                    x, y = mouse_pos
                    is_dual = settings_manager.get("selection_dual_mode_enabled", False)
                    focus_hwnd = win32gui.GetForegroundWindow()
                    try:
                        self.set_selection_overlay_active(True)
                        self.sat_input_q.put(("SHOW", direct_text, x + 10, y - 40, is_dual, focus_hwnd))
                    except Exception:
                        self.set_selection_overlay_active(False)
                self._emit_selection_captured(direct_text)
                self._selection_triggered = False
                return

            capture_token = self._begin_selection_capture()
            self.suppress_clipboard(2.0)
            snapshot = capture_clipboard_snapshot()
            try:
                previous_text = pyperclip.paste()
            except Exception:
                previous_text = ""

            time.sleep(0.03)
            logging.debug("Executing Simulate Copy (ctypes fallback)...")
            
            # Robust Win32 injection
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            self.suppress_shortcuts(1.0)
            
            INPUT_KEYBOARD = 1
            KEYEVENTF_KEYUP = 0x0002
            VK_CONTROL = 0x11
            VK_C = 0x43
            before_seq = user32.GetClipboardSequenceNumber()
            
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
            
            # 1. Press Ctrl
            _send_key(VK_CONTROL, 0)
            time.sleep(0.015)
            # 2. Press C
            _send_key(VK_C, 0)
            time.sleep(0.015)
            # 3. Release C
            _send_key(VK_C, KEYEVENTF_KEYUP)
            time.sleep(0.015)
            # 4. Release Ctrl
            _send_key(VK_CONTROL, KEYEVENTF_KEYUP)

            current = previous_text
            sanitized = ""
            for _ in range(12):
                try:
                    current_seq = user32.GetClipboardSequenceNumber()
                    current = pyperclip.paste()
                    if current and (current_seq != before_seq or current != previous_text):
                        sanitized = sanitize_text(current)
                        if sanitized:
                            break
                except Exception as ex:
                    print(f"DEBUG: Paste Exception: {ex}")
                time.sleep(0.03)

            # Fallback for Terminal/Stubborn Apps
            if not sanitized:
                print("DEBUG: Primary Copy Failed (Clipboard Empty). Trying Pynput Fallback...")
                try:
                    self.suppress_shortcuts(1.0)
                    controller = keyboard.Controller()
                    with controller.pressed(keyboard.Key.ctrl):
                        controller.press('c')
                        controller.release('c')
                    time.sleep(0.08)
                    
                    # Retry Fetch
                    current = pyperclip.paste()
                    if current and current != previous_text:
                        sanitized = sanitize_text(current)
                        print(f"DEBUG: Fallback sanitized: {sanitized[:10] if sanitized else 'None'}")
                except Exception as e:
                    print(f"DEBUG: Fallback Error: {e}")

            if sanitized:
                should_restore_snapshot = self._last_user_clipboard_shortcut_at <= selection_started_at
                if snapshot is not None and should_restore_snapshot:
                    try:
                        restore_clipboard_snapshot(snapshot)
                        snapshot = None
                    except Exception as restore_error:
                        logging.error(f"Early Restore Clipboard Error: {restore_error}")
                elif snapshot is not None and not should_restore_snapshot:
                    logging.debug("Skip restoring snapshot because user copied/cut during selection capture.")
                    snapshot = None

                self.suppress_clipboard(0.6)
                self.previous_clipboard_content = previous_text
                if capture_token is not None:
                    self._end_selection_capture(capture_token)
                    capture_token = None

                if mouse_pos:
                    x, y = mouse_pos
                    is_dual = settings_manager.get("selection_dual_mode_enabled", False)
                    focus_hwnd = win32gui.GetForegroundWindow()
                    try:
                        self.set_selection_overlay_active(True)
                        self.sat_input_q.put(("SHOW", sanitized, x + 10, y - 40, is_dual, focus_hwnd))
                        logging.info(f"Sent SHOW to Satellite: {sanitized[:10]} at {x},{y}, Dual={is_dual}")
                    except Exception:
                        self.set_selection_overlay_active(False)

                self._emit_selection_captured(sanitized)

        except Exception as e:
            print(i18n.get("debug_simulate_copy_error", e))
            # Fallback to pynput just in case
            try:
                controller = keyboard.Controller()
                with controller.pressed(keyboard.Key.ctrl):
                    controller.press('c')
                    controller.release('c')
            except Exception: pass
        finally:
            try:
                if snapshot is not None:
                    restore_clipboard_snapshot(snapshot)
            except Exception as restore_error:
                logging.error(f"Restore Clipboard Error: {restore_error}")
            self.suppress_clipboard(0.6)
            self.previous_clipboard_content = previous_text
            if capture_token is not None:
                self._end_selection_capture(capture_token)
            self._selection_triggered = False
            self._selection_simulation_lock.release()

# Global instance could be created here, or instantiated in main_window
