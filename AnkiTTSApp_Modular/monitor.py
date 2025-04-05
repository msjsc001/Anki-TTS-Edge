# monitor.py
# Handles clipboard polling and mouse event listening.

import threading
import time
import math
import re # <<<<<<< 添加: 导入 re 模块 >>>>>>>>>
import pyperclip
from pynput import mouse, keyboard

# Import necessary variables/objects from other modules
import config # Import config for shared state variables
# Removed: from utils import sanitize_text

# --- Global reference for the callback function from UI ---
_trigger_callback_ref = None
_app_ref = None # Store reference to the app instance for translations

# ==============================================================================
# <<<<<<< 添加: sanitize_text 函数 (从 utils 移动过来) >>>>>>>>>
# ==============================================================================
def sanitize_text(text):
    """Cleans text by removing potentially problematic characters and extra spaces."""
    if not text: return ""
    # Keep a broad range of useful punctuation
    text = re.sub(r'[^\w\s\.,!?;:\'"()\[\]{}<>%&$@#*+\-=/]', '', text, flags=re.UNICODE)
    text = re.sub(r'\s+', ' ', text).strip() # Consolidate whitespace
    return text if text else ""
# ==============================================================================

# --- Clipboard Polling ---
def poll_clipboard():
    """Polls clipboard for changes and triggers float window if needed."""
    # Access app_ref safely
    app = _app_ref
    print(app._("debug_poll_thread_start") if app else "DEBUG: Clipboard polling thread started.")

    while config.clipboard_monitor_active: # Use flag from config
        current_text = None
        try:
            current_text = pyperclip.paste()

            # Check if content is new, not None, not just whitespace
            if current_text is not None and current_text.strip() and current_text != config.previous_clipboard_poll_content:
                # <<<<<<< 修改: 直接调用本模块内的 sanitize_text >>>>>>>>>
                sanitized = sanitize_text(current_text)
                if sanitized:
                    if app: print(app._("debug_new_clipboard_content", sanitized[:50]))
                    else: print(f"New clipboard content: {sanitized[:50]}...")

                    # Update previous content *before* triggering UI
                    config.previous_clipboard_poll_content = current_text

                    if _trigger_callback_ref and app and app.root.winfo_exists():
                        app.root.after(0, _trigger_callback_ref, sanitized)
                    elif not _trigger_callback_ref:
                         print("ERROR: Trigger callback not set in monitor!")

                else:
                    config.previous_clipboard_poll_content = current_text
            elif current_text is not None:
                 config.previous_clipboard_poll_content = current_text
            elif current_text is None:
                config.previous_clipboard_poll_content = None

            time.sleep(0.5) # Polling interval

        except pyperclip.PyperclipException as e:
             if app: print(app._("debug_poll_clipboard_error", e))
             else: print(f"Clipboard access error (ignored): {e}")
             config.previous_clipboard_poll_content = current_text
             time.sleep(1)
        except Exception as e:
            if app: print(app._("debug_poll_generic_error", e))
            else: print(f"Clipboard monitor error: {e}")
            config.previous_clipboard_poll_content = current_text
            time.sleep(1)

    if app: print(app._("debug_poll_thread_stop"))
    else: print("DEBUG: Clipboard polling thread stopped.")


# --- Mouse Monitoring ---
def on_mouse_click(x, y, button, pressed):
    # ... (函数内容保持不变) ...
    app = _app_ref # Access app_ref safely
    if button == mouse.Button.left:
        if pressed:
            config.is_dragging = True
            config.drag_start_pos = (x, y)
            config.drag_start_time = time.time()
            # if app: print(app._("debug_mouse_pressed", config.drag_start_pos))
        else: # Released
            if config.is_dragging:
                config.is_dragging = False
                release_pos=(x,y); release_time=time.time()
                if app and hasattr(app, 'select_trigger_var') and app.select_trigger_var.get():
                    try:
                        dist = math.sqrt((release_pos[0]-config.drag_start_pos[0])**2 + (release_pos[1]-config.drag_start_pos[1])**2)
                        if dist > config.MOUSE_DRAG_THRESHOLD:
                            if app: print(app._("debug_selection_detected"))
                            threading.Thread(target=simulate_copy_after_selection, daemon=True).start()
                    except Exception as e:
                         if app: print(app._("debug_mouse_release_error", e))
                         else: print(f"Error in mouse release logic: {e}")

def listen_mouse():
    # ... (函数内容保持不变) ...
    app = _app_ref
    config.mouse_listener = mouse.Listener(on_click=on_mouse_click)
    config.mouse_listener.start()
    config.mouse_listener.join()
    if app: print(app._("debug_mouse_listener_thread_stop"))
    else: print("DEBUG: Mouse listener thread stopped.")

def simulate_copy_after_selection():
    # ... (函数内容保持不变) ...
    app = _app_ref
    try:
        time.sleep(0.05)
        if app: print(app._("debug_simulate_copy"))
        else: print("DEBUG: Simulating Ctrl+C...")
        controller = keyboard.Controller()
        with controller.pressed(keyboard.Key.ctrl): controller.press('c'); controller.release('c')
        if app: print(app._("debug_simulate_copy_complete"))
        else: print("DEBUG: Ctrl+C Simulation complete.")
    except Exception as e:
        if app: print(app._("debug_simulate_copy_error", e))
        else: print(f"ERROR: Failed to simulate Ctrl+C: {e}")

# --- Monitor Control ---
def start_monitoring(app_ref=None, trigger_callback=None):
    # ... (函数内容保持不变) ...
    global _trigger_callback_ref, _app_ref # Store refs globally within this module
    if config.clipboard_monitor_active: print("Monitor already running"); return
    _app_ref = app_ref; _trigger_callback_ref = trigger_callback
    if not _trigger_callback_ref: print("ERROR: Monitor started without trigger callback!")
    if not _app_ref: print("WARNING: Monitor started without app reference.")
    config.clipboard_monitor_active = True # Set global flag
    if app_ref: print(app_ref._("debug_monitor_start")); app_ref.update_status("status_monitor_enabled", duration=5)
    else: print("Starting monitor...")
    try: config.previous_clipboard_poll_content = pyperclip.paste()
    except Exception as e:
        if app_ref: print(app_ref._("debug_initial_paste_error", e))
        else: print(f"DEBUG: Error getting initial paste: {e}")
        config.previous_clipboard_poll_content = ""
    config.clipboard_polling_thread = threading.Thread(target=poll_clipboard, daemon=True)
    config.clipboard_polling_thread.start()
    config.is_dragging = False
    config.mouse_listener_thread = threading.Thread(target=listen_mouse, daemon=True)
    config.mouse_listener_thread.start()

def stop_monitoring():
    # ... (函数内容保持不变) ...
    global _trigger_callback_ref, _app_ref # Clear refs
    app = _app_ref # Get local copy before clearing
    if not config.clipboard_monitor_active: print("Monitor not running"); return
    if app: print(app._("debug_monitor_stop"))
    else: print("Stopping monitor...")
    config.clipboard_monitor_active = False # Signal threads to stop
    if config.mouse_listener:
        try: config.mouse_listener.stop()
        except Exception as e:
            if app: print(app._("debug_mouse_listener_stop_error", e))
            else: print(f"Error stopping mouse listener: {e}")
    config.mouse_listener = None; config.mouse_listener_thread = None
    config.clipboard_polling_thread = None # Allow thread to finish its loop
    _trigger_callback_ref = None; _app_ref = None # Clear refs
    if app and app.root.winfo_exists():
        app.root.after(0, app.destroy_float_window)
        app.root.after(0, app.destroy_generating_window)
        app.root.after(0, app.destroy_ok_window)
        app.update_status("status_monitor_disabled", duration=3)