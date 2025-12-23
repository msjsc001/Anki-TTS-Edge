import flet as ft
from utils.i18n import i18n
import threading
import ctypes
import asyncio
from config.constants import CUSTOM_WINDOW_TITLE, ICON_PATH, APP_VERSION
from ui.home_view import HomeView
from core.voices import get_available_voices_async
from ui.history_view import HistoryView
from ui.settings_view import SettingsView
from core.audio_gen import generate_audio_task, load_timestamps
from core.history import history_manager
from config.settings import settings_manager
from datetime import datetime
import os
import pygame
from core.files import copy_file_to_clipboard
from core.clipboard import MonitorManager
from core.tray import TrayIconManager
import logging
import multiprocessing

# Load saved language setting before UI initialization
saved_language = settings_manager.get("language", "zh")
i18n.set_language(saved_language)

async def main(page: ft.Page):
    # 1. Page Configuration
    page.title = f"{CUSTOM_WINDOW_TITLE} v{APP_VERSION}"
    
    # Load Window Dimensions (Default: 750x850)
    saved_width = settings_manager.get("window_width", 750)
    saved_height = settings_manager.get("window_height", 850)
    
    # Ensure integer conversion (settings might store as string)
    try:
        saved_width = int(saved_width) if saved_width else 750
        saved_height = int(saved_height) if saved_height else 850
    except (ValueError, TypeError):
        saved_width, saved_height = 750, 850
    
    print(f"DEBUG: Loading window size: {saved_width}x{saved_height}")
    
    # Set window size BEFORE showing (prevents flash)
    page.window.width = saved_width
    page.window.height = saved_height
    page.window.min_width = 400
    page.window.min_height = 500
    page.padding = 0
    page.spacing = 0
    
    # Set window icon (same as tray icon)
    page.window.icon = ICON_PATH
    
    # Center window on screen
    page.window.center()
    
    # Note: handle_resize will be defined and bound later after settings_view is created
    
    # Theme configuration (will be refined later)
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed="indigo")
    
    
    # Helper for Snackbar (Flet 0.21+ compatibility)
    def show_message(msg, is_error=False):
        color = ft.Colors.RED if is_error else ft.Colors.GREEN
        page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
        page.snack_bar.open = True
        page.snack_bar.open = True
        page.update()

    # Helper functions removed


    # 2. Tab Navigation - Top tabs for compact layout
    # Create views first so we can put them in tabs
    home_view = HomeView(page)
    history_view = HistoryView(page)
    settings_view = SettingsView(page)
    
    views = [home_view, history_view, settings_view]
    
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        expand=True,
        tabs=[
            ft.Tab(
                text=i18n.get("tab_voices", "合成"),
                icon=ft.Icons.RECORD_VOICE_OVER,
                content=home_view,
            ),
            ft.Tab(
                text=i18n.get("history_panel_title", "历史"),
                icon=ft.Icons.HISTORY,
                content=history_view,
            ),
            ft.Tab(
                text=i18n.get("tab_settings", "设置"),
                icon=ft.Icons.SETTINGS,
                content=settings_view,
            ),
        ],
    )

    # Language change handler - refresh UI text
    def handle_language_change(new_lang):
        """Refresh UI elements when language changes"""
        print(f"DEBUG: Language changed to {new_lang}, refreshing UI...")
        
        # Update tab labels
        tabs.tabs[0].text = i18n.get("tab_voices")
        tabs.tabs[1].text = i18n.get("history_panel_title")
        tabs.tabs[2].text = i18n.get("tab_settings")
        
        # Update page title
        page.title = i18n.get("window_title", CUSTOM_WINDOW_TITLE)
        
        # Update home view labels
        home_view.header_left.value = i18n.get("voice_list_label_1")
        home_view.header_right.value = i18n.get("voice_list_label_2")
        home_view.btn_gen_a.text = i18n.get("generate_button_previous")
        home_view.btn_gen_b.text = i18n.get("generate_button_latest")
        
        # Update history view
        history_view.header.value = i18n.get("history_panel_title")
        
        # Update settings view - switch labels
        settings_view.header.value = i18n.get("tab_settings")
        settings_view.theme_switch.label = i18n.get("theme_label")
        settings_view.autoplay_switch.label = i18n.get("settings_autoplay_label")
        settings_view.ctrl_c_switch.label = i18n.get("settings_enable_ctrl_c_label")
        settings_view.selection_switch.label = i18n.get("settings_enable_selection_label")
        settings_view.dual_mode_switch.label = i18n.get("settings_dual_blue_dot_label")
        settings_view.copy_file_switch.label = i18n.get("copy_audio_to_clipboard")
        settings_view.tray_switch.label = i18n.get("settings_minimize_to_tray_label")
        settings_view.max_files_input.label = i18n.get("settings_max_files_label")
        settings_view.reset_size_button.text = i18n.get("reset_button")
        
        # Update settings view - section headers
        settings_view.section_appearance_text.value = i18n.get("section_appearance")
        settings_view.language_label_text.value = i18n.get("language_label")
        settings_view.section_behavior_text.value = i18n.get("section_behavior")
        settings_view.clipboard_label_text.value = i18n.get("settings_clipboard_label")
        settings_view.section_window_text.value = i18n.get("section_window")
        settings_view.window_size_label_text.value = i18n.get("window_size_label")
        settings_view.section_storage_text.value = i18n.get("section_storage")
        settings_view.save_button.text = i18n.get("save_settings")
        
        page.update()
    
    settings_view.on_language_changed = handle_language_change
    
    # Restart cleanup handler - stop tray and monitors before restart
    def handle_app_restart():
        print("DEBUG: Cleanup before restart...")
        monitor_manager.stop()
        tray_manager.stop()
    
    settings_view.on_app_restart = handle_app_restart
    
    # Window resize handler - bidirectional sync with settings UI
    def handle_resize(e):
        new_width = int(page.window.width) if page.window.width else 750
        new_height = int(page.window.height) if page.window.height else 850
        print(f"DEBUG: Window resized to {new_width}x{new_height}")
        settings_manager.set("window_width", new_width)
        settings_manager.set("window_height", new_height)
        settings_manager.save_settings()
        # Sync settings UI display
        settings_view.update_window_size_display(new_width, new_height)
        
    page.on_resized = handle_resize
    
    # Handle when user changes size in settings UI
    def handle_window_size_from_settings(width, height):
        print(f"DEBUG: User set window size to {width}x{height} in settings")
        page.window.width = width
        page.window.height = height
        settings_manager.set("window_width", width)
        settings_manager.set("window_height", height)
        settings_manager.save_settings()
        page.update()
        
    settings_view.on_window_size_change = handle_window_size_from_settings

    # 4. Main Layout - Just the tabs (content is inside each tab)
    page.add(tabs)
    
    # Initialize Pygame Mixer early (fast operation)
    pygame.mixer.init()
    
    # Show UI immediately
    page.update()
    
    # Load voices from cache (instant) or network (slow)
    voices = await get_available_voices_async()
    home_view.populate_voices(voices)
    page.update()
    
    # Background refresh: check network for updates
    async def background_voice_refresh():
        from core.voices import fetch_voices_from_network, get_cached_voices
        try:
            # Wait a bit to not slow down startup
            await asyncio.sleep(3)
            
            # Fetch fresh data
            fresh_voices = await fetch_voices_from_network()
            
            # Compare with current (cache was already shown)
            if fresh_voices and len(fresh_voices) != len(voices):
                print(f"DEBUG: Voice list updated in background ({len(voices)} -> {len(fresh_voices)})")
                home_view.populate_voices(fresh_voices)
                page.update()
        except Exception as e:
            print(f"DEBUG: Background voice refresh failed: {e}")
    
    # Start background refresh (non-blocking)
    asyncio.create_task(background_voice_refresh())
    
    page.splash = None
    page.update()

    
    # Mini Mode Removed - Replaced by Satellite Process logic
    # (See satellite_loop below)
        # Satellite Poll Loop
    import queue
    
    async def handle_satellite_action(text, mode="B"):
        if not text: return
        print(f"Main: Received ACTION for '{text[:10]}', mode='{mode}'")
        
        # Update input text field with the text being generated
        home_view.set_input_text(text, mark_as_generated=True)
        
        voice_key = "selected_voice_latest" if mode == "B" else "selected_voice_previous"
        voice = settings_manager.get(voice_key)
        
        print(f"DEBUG: Handle Action - Voice Key: {voice_key}, Voice: '{voice}'")
        
        # Fallback if voice is missing (e.g. first run)
        if not voice:
             from config.constants import DEFAULT_VOICE
             print(f"DEBUG: Voice missing for {mode}, using default: {DEFAULT_VOICE}")
             voice = DEFAULT_VOICE
             # Optionally save it back?
             if mode == "B": settings_manager.set("selected_voice_latest", voice)
             
        if not voice:
             show_message(i18n.get("status_no_voice_error") + f" (Mode {mode})", True)
             return
             
        # Call Generate Task (Wait for result? Or separate task?)
        # Since on_done is callback, we wrapping it.
        # But generate_audio_task is async.
        
        # Send Generating State
        try:
             monitor_manager.sat_input_q.put(("STATE", "generating"))
        except: pass

        def on_done(path, error, timestamps=None):
            print(f"DEBUG: on_done called. Path={path}, Error={error}")
            if path:
                try:
                     monitor_manager.sat_input_q.put(("STATE", "success"))
                except: pass
                
                # Update playback state
                current_audio_state["path"] = path
                current_audio_state["timestamps"] = timestamps
                current_audio_state["text"] = text
                current_audio_state["text_dirty"] = False
                
                enabled = settings_manager.get("autoplay_enabled", True)
                print(f"DEBUG: Autoplay Check (Satellite): {enabled}")
                if enabled:
                    handle_play_audio({"path": path, "timestamps": timestamps})
                if settings_manager.get("copy_path_enabled", True):
                     try:
                        copy_file_to_clipboard(path)
                     except: pass
                
                # Add to history
                history_manager.add_record(text, voice, path)
                history_view.populate_history(history_manager.get_records())
            else:
                try:
                     monitor_manager.sat_input_q.put(("STATE", "error"))
                except: pass
                home_view.set_status(f"生成失败: {error}", ft.Icons.ERROR_OUTLINE, ft.Colors.RED_100)
                show_message(f"Error: {error}", True)

        print(f"DEBUG: Calling generate_audio_task with text='{text[:10]}...', voice='{voice}'")
        timestamps = None
        try:
            path, error, timestamps = await asyncio.wait_for(
                generate_audio_task(text, voice, 
                    f"{int(home_view.rate_slider.value):+d}%", 
                    f"{int(home_view.volume_slider.value):+d}%",
                    "+0Hz"
                ),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            path = None
            error = i18n.get("status_timeout_error", "Generation timed out")
        except Exception as e:
            path = None
            error = str(e)
            
        on_done(path, error, timestamps)

    async def satellite_loop():
        # print("DEBUG: Satellite Loop Started")
        while True:
            try:
                # We need access to monitor_manager which is defined later.
                # But this loop runs as async task, it will be running when variable is available
                if 'monitor_manager' in locals() and monitor_manager.sat_output_q:
                    try:
                        cmd, *args = monitor_manager.sat_output_q.get_nowait()
                        if cmd == "ACTION":
                            text = args[0]
                            mode = args[1] if len(args) > 1 else "B"
                            await handle_satellite_action(text, mode=mode)
                        elif cmd == "RESTORE":
                            print("Main: Restoring Window")
                            page.window_minimized = False
                            page.window_visible = True
                            page.window_to_front()
                            page.update()
                    except queue.Empty:
                        pass
            except Exception as e:
                print(f"DEBUG: Error in Satellite Loop: {e}")
            
            await asyncio.sleep(0.1)

    page.run_task(satellite_loop)

    # 7. Interaction Handlers
    # Playback state management
    current_audio_state = {
        "path": None,
        "timestamps": None,
        "text": None,
        "is_playing": False,
        "is_paused": False,  # Distinguish between pause and stop
        "current_sentence_index": 0,
        "current_word_index": 0,
        "text_dirty": False,  # True if user edited text after last generation
        "current_playback_start_ms": 0, # Offset to add to pygame.get_pos()
        "stop_playback_at_ms": None # If set, stop when this pos is reached
    }

    async def handle_generate(e, voice):
        # Auto-clean HTML tags before processing
        home_view.clean_text_input()
        
        text = home_view.get_input_text()
        if not text:
             show_message(i18n.get("status_no_text_error"), True)
             home_view.set_status("请输入文本", ft.Icons.WARNING_AMBER, ft.Colors.ORANGE_100)
             return
        
        # Show generating status
        home_view.set_status("正在生成音频...", ft.Icons.HOURGLASS_EMPTY, ft.Colors.BLUE_100)
        
        # Mark text as generated (for edit detection)
        home_view.set_input_text(text, mark_as_generated=True)

        path, error, timestamps = await generate_audio_task(text, voice, 
            f"{int(home_view.rate_slider.value):+d}%", 
            f"{int(home_view.volume_slider.value):+d}%",
            "+0Hz"
        )
        
        if path:
            home_view.set_status("音频生成成功", ft.Icons.CHECK_CIRCLE_OUTLINE, ft.Colors.GREEN_100)
            
            # Update playback state
            current_audio_state["path"] = path
            current_audio_state["timestamps"] = timestamps
            current_audio_state["text"] = text
            current_audio_state["text_dirty"] = False
            current_audio_state["current_sentence_index"] = 0
            
            enabled = settings_manager.get("autoplay_enabled", True)
            print(f"DEBUG: Autoplay Check (Button): {enabled}")
            if enabled:
                handle_play_audio({"path": path, "timestamps": timestamps})
            if settings_manager.get("copy_path_enabled", True):
                 try:
                    copy_file_to_clipboard(path)
                 except: pass
            
            # Add to history
            history_manager.add_record(text, voice, path)
            history_view.populate_history(history_manager.get_records())
        else:
            home_view.set_status(f"生成失败: {error}", ft.Icons.ERROR_OUTLINE, ft.Colors.RED_100)
            show_message(f"Error: {error}", True)

    async def handle_generate_b(e):
        # Latest Voice (B)
        v = settings_manager.get("selected_voice_latest")
        if not v:
            show_message(i18n.get("status_no_voice_error"), True)
            return
        await handle_generate(e, v)

    async def handle_generate_a(e):
        # Previous Voice (A)
        v = settings_manager.get("selected_voice_previous")
        if not v:
             show_message(i18n.get("status_no_voice_error"), True)
    async def handle_generate_a(e):
        # Previous Voice (A)
        v = settings_manager.get("selected_voice_previous")
        if not v:
             show_message(i18n.get("status_no_voice_error"), True)
             return
        await handle_generate(e, v)

    # Audio Handlers
    def handle_play_audio(e):
        path = None
        timestamps = None
        if isinstance(e, dict):
             path = e.get("path")
             timestamps = e.get("timestamps")
        
        if path and os.path.exists(path):
            print(f"DEBUG: Playing Audio: {path}")
            try:
                # Update status
                home_view.set_status("正在播放...", ft.Icons.PLAY_CIRCLE_OUTLINE, ft.Colors.GREEN_100)
                
                # Update state
                current_audio_state["path"] = path
                current_audio_state["is_playing"] = True
                current_audio_state["is_paused"] = False
                current_audio_state["current_word_index"] = 0
                current_audio_state["current_playback_start_ms"] = 0 # Reset offset
                current_audio_state["stop_playback_at_ms"] = None # Reset stop constraint
                
                if timestamps:
                    current_audio_state["timestamps"] = timestamps
                elif not current_audio_state["timestamps"]:
                    # Try to load timestamps from file
                    current_audio_state["timestamps"] = load_timestamps(path)
                
                # Set text input to read-only during playback
                home_view.text_input.read_only = True
                
                # Show highlighted text if we have word timings
                ts = current_audio_state["timestamps"]
                if ts and ts.get("words"):
                    home_view.show_highlighted_text(
                        current_audio_state.get("text", ""),
                        ts["words"]
                    )
                
                home_view.text_input.update()
                
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
                home_view.btn_play_pause.selected = True
                home_view.btn_play_pause.update()
                
                # Start playback monitoring
                page.run_task(playback_monitor_loop)
            except Exception as ex:
                print(f"Error playing: {ex}")
                home_view.set_status(f"播放失败: {ex}", ft.Icons.ERROR_OUTLINE, ft.Colors.RED_100)
                current_audio_state["is_playing"] = False
    
    def handle_stop_audio(e):
        pygame.mixer.music.stop()
        current_audio_state["is_playing"] = False
        current_audio_state["is_paused"] = False
        current_audio_state["current_sentence_index"] = 0
        current_audio_state["current_word_index"] = 0
        home_view.btn_play_pause.selected = False
        home_view.text_input.read_only = False
        home_view.hide_highlighted_text()  # Hide highlighting
        home_view.set_status("已停止", ft.Icons.STOP_CIRCLE_OUTLINED, ft.Colors.GREY_200)
        home_view.btn_play_pause.update()
        home_view.text_input.update()
    
    async def handle_pause_resume(e):
        """Toggle play/pause state, or generate if no audio exists"""
        # Case 1: Currently playing -> pause
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            current_audio_state["is_paused"] = True
            home_view.btn_play_pause.selected = False
            home_view.set_status("已暂停", ft.Icons.PAUSE_CIRCLE_OUTLINE, ft.Colors.AMBER_100)
            home_view.btn_play_pause.update()
            return
        
        # Case 2: Paused -> resume
        if current_audio_state["is_paused"]:
            pygame.mixer.music.unpause()
            current_audio_state["is_paused"] = False
            current_audio_state["is_playing"] = True
            # Resume means continue to end, so clear any existing stop constraint
            current_audio_state["stop_playback_at_ms"] = None
            
            home_view.btn_play_pause.selected = True
            home_view.set_status("正在播放...", ft.Icons.PLAY_CIRCLE_OUTLINE, ft.Colors.GREEN_100)
            # Restart monitoring loop if it stopped
            page.run_task(playback_monitor_loop)
            home_view.btn_play_pause.update()
            return
        
        # Case 3: No audio or text changed -> need to generate first
        text = home_view.get_input_text()
        if not text:
            home_view.set_status("请输入文本", ft.Icons.WARNING_AMBER, ft.Colors.ORANGE_100)
            return
        
        # Check if we have valid cached audio
        has_valid_cache = (
            current_audio_state["path"] and 
            os.path.exists(current_audio_state["path"]) and
            not home_view.is_text_dirty()
        )
        
        if has_valid_cache:
            # Play from cache
            home_view.set_status("从缓存播放...", ft.Icons.PLAY_CIRCLE_OUTLINE, ft.Colors.GREEN_100)
            handle_play_audio({
                "path": current_audio_state["path"], 
                "timestamps": current_audio_state["timestamps"]
            })
        else:
            # Need to generate first
            home_view.set_status("正在生成音频...", ft.Icons.HOURGLASS_EMPTY, ft.Colors.BLUE_100)
            
            # Get voice
            voice = settings_manager.get("selected_voice_latest")
            if not voice:
                from config.constants import DEFAULT_VOICE
                voice = DEFAULT_VOICE
            
            if not voice:
                home_view.set_status("请选择声音", ft.Icons.WARNING_AMBER, ft.Colors.ORANGE_100)
                return
            
            # Generate audio
            path, error, timestamps = await generate_audio_task(
                text, voice, 
                f"{int(home_view.rate_slider.value):+d}%", 
                f"{int(home_view.volume_slider.value):+d}%",
                "+0Hz"
            )
            
            if path:
                home_view.set_input_text(text, mark_as_generated=True)
                current_audio_state["path"] = path
                current_audio_state["timestamps"] = timestamps
                current_audio_state["text"] = text
                current_audio_state["text_dirty"] = False
                
                home_view.set_status("正在播放...", ft.Icons.PLAY_CIRCLE_OUTLINE, ft.Colors.GREEN_100)
                handle_play_audio({"path": path, "timestamps": timestamps})
                
                # Add to history
                history_manager.add_record(text, voice, path)
                history_view.populate_history(history_manager.get_records())
            else:
                home_view.set_status(f"生成失败: {error}", ft.Icons.ERROR_OUTLINE, ft.Colors.RED_100)
    
    def handle_replay(e):
        """Replay from beginning"""
        if current_audio_state["path"] and os.path.exists(current_audio_state["path"]):
            current_audio_state["current_sentence_index"] = 0
            handle_play_audio({"path": current_audio_state["path"], "timestamps": current_audio_state["timestamps"]})
    
    async def ensure_audio_ready(e):
        """Helper to generate audio if missing before navigation"""
        if not current_audio_state.get("timestamps"):
             # Need to generate
             v = settings_manager.get("selected_voice_latest")
             if not v:
                 home_view.set_status("请选择声音", ft.Icons.WARNING_AMBER, ft.Colors.ORANGE_100)
                 return False
                 
             await handle_generate(e, v)
             
             # After generation, handle_generate starts playback from 0. 
             # We might intercept or just let it be, but we need timestamps now.
             if not current_audio_state.get("timestamps"):
                 return False
        return True

    async def handle_prev_sentence(e):
        """Jump to previous sentence"""
        if not await ensure_audio_ready(e): return

        timestamps = current_audio_state.get("timestamps")
        if not timestamps or not timestamps.get("sentences"):
            return
        
        sentences = timestamps["sentences"]
        current_idx = current_audio_state["current_sentence_index"]
        
        # User constraint: "只播放上一句" (Only play this sentence)
        target_idx = max(0, current_idx - 1)
        sent = sentences[target_idx]
        target_ms = sent["start_ms"]
        stop_ms = sent["end_ms"]
        
        current_audio_state["current_sentence_index"] = target_idx
        current_audio_state["current_playback_start_ms"] = target_ms 
        current_audio_state["stop_playback_at_ms"] = stop_ms 
            
        try:
            # FIX: Always use play(start=) to reset get_pos() for consistent timing offset
            pygame.mixer.music.play(start=target_ms / 1000.0)
            
            home_view.btn_play_pause.selected = True
            home_view.btn_play_pause.update()
            
            # FIX: Immediate Highlight Update
            first_word_idx = -1
            if timestamps.get("words"):
                 for i, w in enumerate(timestamps["words"]):
                     if w["start_ms"] >= target_ms:
                         first_word_idx = i
                         break
            if first_word_idx != -1:
                current_audio_state["current_word_index"] = first_word_idx
                home_view.update_highlight_position(first_word_idx)
            
            # Ensure loop running
            if not current_audio_state["is_playing"]:
                current_audio_state["is_playing"] = True
                page.run_task(playback_monitor_loop)
                
        except Exception as ex:
            print(f"DEBUG: prev failed: {ex}")
    
    async def handle_next_sentence(e):
        """Jump to next sentence"""
        if not await ensure_audio_ready(e): return
        
        timestamps = current_audio_state.get("timestamps")
        if not timestamps or not timestamps.get("sentences"):
            return
        
        sentences = timestamps["sentences"]
        current_idx = current_audio_state["current_sentence_index"]
        
        if current_idx < len(sentences) - 1:
            target_idx = current_idx + 1
            sent = sentences[target_idx]
            
            target_ms = sent["start_ms"]
            stop_ms = sent["end_ms"]
            
            current_audio_state["current_sentence_index"] = target_idx
            current_audio_state["current_playback_start_ms"] = target_ms
            current_audio_state["stop_playback_at_ms"] = stop_ms 
            
            try:
                # FIX: Always use play(start=) to reset get_pos()
                pygame.mixer.music.play(start=target_ms / 1000.0)

                home_view.btn_play_pause.selected = True
                home_view.btn_play_pause.update()
                
                # FIX: Immediate Highlight Update
                first_word_idx = -1
                if timestamps.get("words"):
                     for i, w in enumerate(timestamps["words"]):
                         if w["start_ms"] >= target_ms:
                             first_word_idx = i
                             break
                if first_word_idx != -1:
                    current_audio_state["current_word_index"] = first_word_idx
                    home_view.update_highlight_position(first_word_idx)
                
                if not current_audio_state["is_playing"]:
                    current_audio_state["is_playing"] = True
                    page.run_task(playback_monitor_loop)

            except Exception as ex:
                print(f"DEBUG: next failed: {ex}")

    def handle_word_jump(word_index):
        """Click to Play: Jump to sentence containing this word"""
        timestamps = current_audio_state.get("timestamps")
        if not timestamps or not timestamps.get("words"): return
        
        # Get word start time
        if word_index < 0 or word_index >= len(timestamps["words"]): return
        target_word = timestamps["words"][word_index]
        word_ms = target_word["start_ms"]
        
        # Find sentence containing this word
        sentences = timestamps.get("sentences", [])
        target_sent_idx = 0
        target_sent_start_ms = 0
        
        found = False
        for i, sent in enumerate(sentences):
            if sent["start_ms"] <= word_ms < sent["end_ms"]:
                target_sent_idx = i
                target_sent_start_ms = sent["start_ms"]
                found = True
                break
        
        if not found:
            # Fallback to word start
            target_sent_start_ms = word_ms
        
        # Update state (Continuous playback logic as requested)
        current_audio_state["current_sentence_index"] = target_sent_idx
        current_audio_state["current_playback_start_ms"] = target_sent_start_ms
        current_audio_state["stop_playback_at_ms"] = None # Continuous play
        
        try:
            # FIX: Always use play(start=)
            pygame.mixer.music.play(start=target_sent_start_ms / 1000.0)
            
            # If paused, unpause state
            current_audio_state["is_paused"] = False
            home_view.btn_play_pause.selected = True
            home_view.btn_play_pause.update()
            
            # FIX: Immediate Highlight (First word of Sentence, NOT clicked word)
            first_word_idx = word_index # Default fallback
            # Try to find exactly first word of sentence
            if found:
                 for i, w in enumerate(timestamps["words"]):
                     if w["start_ms"] >= target_sent_start_ms:
                         first_word_idx = i
                         break
            
            current_audio_state["current_word_index"] = first_word_idx
            home_view.update_highlight_position(first_word_idx)
            
            if not current_audio_state["is_playing"]:
                current_audio_state["is_playing"] = True
                page.run_task(playback_monitor_loop)
                
        except Exception as ex:
            print(f"DEBUG: jump failed: {ex}")

    home_view.on_word_click = handle_word_jump
    
    async def playback_monitor_loop():
        """Monitor playback progress and update highlighting"""
        last_word_idx = -1
        
        while True:
            try:
                # Check if we should exit the loop
                if not current_audio_state["is_playing"] and not current_audio_state["is_paused"]:
                    break
                
                # If paused, just wait
                if current_audio_state["is_paused"]:
                    await asyncio.sleep(0.1)
                    continue
                
                # Check if playback finished (not busy and not paused)
                if not pygame.mixer.music.get_busy() and not current_audio_state["is_paused"]:
                    # Playback finished
                    current_audio_state["is_playing"] = False
                    home_view.btn_play_pause.selected = False
                    home_view.text_input.read_only = False
                    home_view.hide_highlighted_text()  # Hide highlighting when done
                    home_view.set_status("播放完成", ft.Icons.CHECK_CIRCLE_OUTLINE, ft.Colors.GREEN_100)
                    home_view.btn_play_pause.update()
                    home_view.text_input.update()
                    break
                
                # Get current position in ms
                # FIX: Add Start Offset because get_pos() returns time since play() started
                rel_ms = pygame.mixer.music.get_pos()
                if rel_ms == -1: rel_ms = 0
                pos_ms = current_audio_state.get("current_playback_start_ms", 0) + rel_ms
                
                # Check for Sentence Stop Condition
                stop_at = current_audio_state.get("stop_playback_at_ms")
                if stop_at and pos_ms >= stop_at:
                    # Pause playback as if user clicked pause
                    pygame.mixer.music.pause()
                    current_audio_state["is_paused"] = True
                    current_audio_state["stop_playback_at_ms"] = None # Clear constraint so Resume works
                    home_view.btn_play_pause.selected = False
                    home_view.set_status("已暂停 (句末)", ft.Icons.PAUSE_CIRCLE_OUTLINE, ft.Colors.AMBER_100)
                    home_view.btn_play_pause.update()
                    continue
                
                timestamps = current_audio_state.get("timestamps")
                if timestamps:
                    # Update current word index for highlighting
                    if timestamps.get("words"):
                        for i, word in enumerate(timestamps["words"]):
                            if word["start_ms"] <= pos_ms < word["end_ms"]:
                                if i != last_word_idx:
                                    current_audio_state["current_word_index"] = i
                                    home_view.update_highlight_position(i)
                                    last_word_idx = i
                                break
                    
                    # Update current sentence index
                    if timestamps.get("sentences"):
                        for i, sent in enumerate(timestamps["sentences"]):
                            if sent["start_ms"] <= pos_ms < sent["end_ms"]:
                                current_audio_state["current_sentence_index"] = i
                                break
                
            except Exception as ex:
                print(f"DEBUG: Playback monitor error: {ex}")
            
            await asyncio.sleep(0.05)  # 50ms update interval

    # Bindings
    home_view.btn_gen_a.on_click = handle_generate_a
    home_view.btn_gen_b.on_click = handle_generate_b
    home_view.btn_stop.on_click = handle_stop_audio
    home_view.btn_replay.on_click = handle_replay
    home_view.btn_play_pause.on_click = handle_pause_resume
    home_view.btn_prev_sentence.on_click = handle_prev_sentence
    home_view.btn_next_sentence.on_click = handle_next_sentence
    
    # Voice Selection Handler
    # Voice Selection Handler
    def handle_voice_selected(e):
        new_voice = e.control.data
        current_latest = settings_manager.get("selected_voice_latest")
        
        # Avoid rotation if clicking the same voice? 
        # User says "First selected (current) -> B, Previous -> A".
        # If I click the SAME voice, do I rotate? Probably not.
        if new_voice == current_latest:
            print("Selected same voice, no rotation.")
            return

        # Rotate: Current Latest -> Previous (A)
        # New Voice -> Latest (B)
        settings_manager.set("selected_voice_previous", current_latest)
        settings_manager.set("selected_voice_latest", new_voice)
        settings_manager.save_settings()
        
        print(f"Voice Selection Rotated: B(Latest)='{new_voice}', A(Prev)='{current_latest}'")
        
        # Update UI (Optional: Highlight logic in HomeView might need 'previous' awareness?)
        # For now, just refresh the list visual if it relies on this.
        # Check if home_view.set_selections exists or uses 'previous'
        if hasattr(home_view, 'set_selections'):
            home_view.set_selections(
                new_voice,
                current_latest
            )
        else:
             # Fallback to update logic if Method missing
             # (See HomeView implementation)
             pass 
        page.update()

    home_view.on_voice_selected = handle_voice_selected

    # Pin Toggle Handler (Always on Top) with persistence
    def handle_pin_toggle(is_pinned):
        print(f"DEBUG: Pin Toggle Requested -> {is_pinned}")
        
        # Use new Flet API
        page.window.always_on_top = is_pinned
        
        # Save state to settings
        settings_manager.set("pin_enabled", is_pinned)
        settings_manager.save_settings()
        
        page.update()
        print(f"DEBUG: Pin Status Now -> {page.window.always_on_top}")
    
    home_view.on_pin_toggle = handle_pin_toggle
    
    # Restore pin state from settings
    saved_pin = settings_manager.get("pin_enabled", False)
    if saved_pin:
        page.window.always_on_top = True
        home_view.btn_pin.selected = True
        page.update()

    # History Handlers
    def handle_history_play(record):
        if record and "path" in record:
            handle_play_audio({"path": record["path"]})

    def handle_history_delete(record):
        # Unload audio to release file lock (Windows specific)
        try:
             pygame.mixer.music.unload() 
        except: 
             pygame.mixer.music.stop()
             
        history_manager.remove_record(record)
        history_view.populate_history(history_manager.get_records())

    def handle_history_clear():
        print("DEBUG: handle_history_clear TRIGGERED")
        try:
             # Stop playback first
             try: pygame.mixer.music.unload()
             except: pass
             try: pygame.mixer.music.stop()
             except: pass
             
             history_manager.clear_records() # Deletes files and clears list
             print("DEBUG: Manager cleared.")
             
             # Force UI Refresh
             new_records = history_manager.get_records()
             print(f"DEBUG: Repopulating with {len(new_records)} records")
             history_view.populate_history(new_records)
             page.update()
             
        except Exception as ex:
             print(f"ERROR in handle_history_clear: {ex}")

    history_view.on_play_audio = handle_history_play
    history_view.on_delete_item = handle_history_delete
    history_view.on_clear_all = handle_history_clear

    monitor_manager = MonitorManager(
        on_clipboard_change=lambda t: home_view.set_input_text(t) if t else None,
        on_selection_trigger=lambda pos: threading.Thread(target=monitor_manager.simulate_copy, args=(pos,)).start()
    )
    monitor_manager.start_monitors() 

    # Tray Logic
    def on_tray_show_hide():
        page.window.visible = not page.window.visible
        page.update()
        
    def on_tray_exit():
        monitor_manager.stop_monitors()
        tray_manager.stop()
        page.window.destroy()

    tray_manager = TrayIconManager(on_show_hide=on_tray_show_hide, on_exit=on_tray_exit)
    tray_manager.start() # Start tray icon immediately



    # Window Events
    page.window.prevent_close = True # Handle close manually

    def window_event(e):
        if e.data == "close":
            if settings_manager.get("minimize_to_tray", False):
                print("DEBUG: Window Close -> Hiding to Tray")
                page.window.visible = False
                page.update()
            else:
                on_tray_exit()
        elif e.data == "minimize":
             if settings_manager.get("minimize_to_tray", False):
                 print("DEBUG: Window Minimized -> Hiding to Tray")
                 page.window.visible = False
                 page.update()
             else:
                 print("DEBUG: Window Minimized -> Taskbar (Normal)")
                 pass

    page.window.on_event = window_event
    
    # Settings Handler
    def handle_save_settings(settings_dict):
        print("DEBUG: Saving Settings:", settings_dict)
        for k, v in settings_dict.items():
            settings_manager.set(k, v)
        settings_manager.save_settings()
        
        # Apply immediate effects checks
        monitor_manager.start_monitors() # Will adjust/stop based on new flags
        
        # Update dual mode
        is_dual = settings_manager.get("dual_blue_dot_enabled", False)
        home_view.set_dual_mode(is_dual)
        
        page.update()

    settings_view.on_save_settings = handle_save_settings

    page.update()

    page.on_window_event = window_event

    # Load Initial History
    history_view.populate_history(history_manager.get_records())
    
    # Init Views state
    is_dual = settings_manager.get("dual_blue_dot_enabled", False)
    home_view.set_dual_mode(is_dual)
    home_view.set_selections(
        settings_manager.get("selected_voice_latest"),
        settings_manager.get("selected_voice_previous")
    )
    settings_view.set_values(settings_manager.settings)
    
    page.update()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    ft.app(target=main)
