import os
import sys
import re
import tkinter as tk
from tkinter import messagebox, colorchooser
import customtkinter as ctk
import pygame
import threading
import pyperclip

# Config & Utils
from config.constants import DEFAULT_VOICE, DEFAULT_APPEARANCE_MODE, DEFAULT_CUSTOM_COLOR, ICON_PATH
from config.settings import settings_manager
from utils.i18n import i18n
from utils.text import sanitize_text

# Core Logic
from core.voices import get_available_voices_async, get_display_voice_name
from core.voice_db import load_voice_cache
from core.audio_gen import generate_audio
from core.files import manage_audio_files, copy_file_to_clipboard
from core.history import history_manager
from core.clipboard import MonitorManager

# UI Components
from ui.tray_icon import TrayIconManager
from ui.float_window import FloatWindowManager

class MainWindow:
    def __init__(self, root):
        self.root = root
        
        # Load settings first
        self.settings = settings_manager
        i18n.set_language(self.settings.get("language", "zh"))
        
        # UI Setup
        self.root.title(i18n.get("window_title"))
        self.root.minsize(width=550, height=620)
        
        # Set Icon
        try:
            self.root.iconbitmap(ICON_PATH)
        except Exception as e:
            print(f"Set icon failed: {e}")
        
        # Initialize Sub-Managers
        self.tray_manager = TrayIconManager(on_show_hide=self._toggle_window_visibility, on_exit=self.quit_application)
        self.float_manager = FloatWindowManager(self.root, self._handle_float_generate)
        self.monitor_manager = MonitorManager(on_clipboard_change=self._on_clipboard_change, on_selection_trigger=self._on_selection_trigger)
        
        # State Variables
        self.is_pinned = False
        self.is_generating_from_float = False
        self.voice_display_to_full_map = {}
        self.hierarchical_voice_data = {}
        
        # Pygame Init
        try:
            pygame.init()
            pygame.mixer.init()
        except Exception as e:
            messagebox.showerror(i18n.get("error_mixer_init_title"), i18n.get("error_mixer_init_message", e))

        # Setup UI Elements
        self._setup_ui()
        self._bind_events()
        
        # Post-Init Actions
        self._apply_custom_color(save=False)
        
        # Load from cache first for speed
        cached_voices = load_voice_cache()
        if cached_voices:
            self._on_voices_loaded(cached_voices, from_cache=True)
            
        self.refresh_voices_ui()
        self._update_monitor_state() # Start monitors if enabled
        
        # Tray Setup (delayed)
        self.root.after(100, self.tray_manager.start)

    def _setup_ui(self):
        # Appearance
        ctk.set_appearance_mode(self.settings.get("appearance_mode"))
        self.current_custom_color = self.settings.get("custom_theme_color")
        
        # Main Frame
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=0)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # 1. Text Input & Pin
        self._setup_text_area()
        
        # 2. Tabs (Voices, Settings, Appearance)
        self._setup_tabs()
        
        # 3. Generate Buttons
        self._setup_generate_buttons()
        
        # 4. Status Bar
        self._setup_status_bar()

    def _setup_text_area(self):
        text_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        text_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(5, 15))
        text_frame.grid_columnconfigure(0, weight=1)
        
        self.text_input_label = ctk.CTkLabel(text_frame, text=i18n.get("input_text_label"), font=ctk.CTkFont(size=14, weight="bold"))
        self.text_input_label.grid(row=0, column=0, sticky="nw")
        
        self.pin_button = ctk.CTkButton(text_frame, text="📌", width=30, height=30, fg_color="transparent", hover=False, font=ctk.CTkFont(size=16), command=self.toggle_pin_window)
        self.pin_button.grid(row=0, column=1, sticky="ne")
        
        self.text_input = ctk.CTkTextbox(text_frame, height=100, wrap="word", corner_radius=8, border_width=1)
        self.text_input.grid(row=1, column=0, columnspan=2, sticky="nsew")

    def _setup_tabs(self):
        container = ctk.CTkFrame(self.main_frame, height=410, fg_color="transparent")
        container.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=0)
        container.grid_propagate(False)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        self.tab_view = ctk.CTkTabview(container, corner_radius=8)
        self.tab_view.grid(row=0, column=0, sticky="nsew")
        
        self.tab_view.add(i18n.get("tab_voices"))
        self.tab_view.add(i18n.get("tab_settings"))
        self.tab_view.add(i18n.get("tab_appearance"))
        
        self._setup_voice_tab()
        self._setup_settings_tab()
        self._setup_appearance_tab()

    def _setup_voice_tab(self):
        tab = self.tab_view.tab(i18n.get("tab_voices"))
        # Split into Voices (Left, 2/3) and History (Right, 1/3)
        tab.grid_columnconfigure(0, weight=2)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # --- Voices Container ---
        self.voices_container = ctk.CTkFrame(tab, fg_color="transparent")
        self.voices_container.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.voices_container.grid_columnconfigure((0, 1), weight=1)
        self.voices_container.grid_rowconfigure(1, weight=1)

        # Filters (Inside voices_container)
        self.filter_left = ctk.CTkEntry(self.voices_container, placeholder_text=i18n.get("filter_language_placeholder"))
        self.filter_left.grid(row=0, column=0, padx=(0, 5), pady=(0, 5), sticky="ew")
        self.filter_left.insert(0, self.settings.get("language_filter_left"))
        self.filter_left.bind("<KeyRelease>", lambda e: self._filter_voices('left'))
        
        self.filter_right = ctk.CTkEntry(self.voices_container, placeholder_text=i18n.get("filter_language_placeholder"))
        self.filter_right.grid(row=0, column=1, padx=(5, 0), pady=(0, 5), sticky="ew")
        self.filter_right.insert(0, self.settings.get("language_filter_right"))
        self.filter_right.bind("<KeyRelease>", lambda e: self._filter_voices('right'))

        # Lists (Inside voices_container)
        self.list_left = ctk.CTkScrollableFrame(self.voices_container, label_text=i18n.get("voice_list_label_1"), height=150)
        self.list_left.grid(row=1, column=0, padx=(0, 5), sticky="nsew")
        self.list_left.grid_columnconfigure(0, weight=1)
        
        self.list_right = ctk.CTkScrollableFrame(self.voices_container, label_text=i18n.get("voice_list_label_2"), height=150)
        self.list_right.grid(row=1, column=1, padx=(5, 0), sticky="nsew")
        self.list_right.grid_columnconfigure(0, weight=1)

        # Controls (Inside voices_container)
        controls = ctk.CTkFrame(self.voices_container, fg_color="transparent")
        controls.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        controls.grid_columnconfigure(1, weight=1)
        
        self.refresh_btn = ctk.CTkButton(controls, text=i18n.get("refresh_voices_button"), command=self.refresh_voices_ui, font=ctk.CTkFont(size=12))
        self.refresh_btn.grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky="ew")
        
        # Rate & Volume
        ctk.CTkLabel(controls, text=i18n.get("rate_label")).grid(row=1, column=0, padx=5, sticky="w")
        self.rate_var = ctk.IntVar(value=self.settings.get("rate"))
        self.rate_slider = ctk.CTkSlider(controls, from_=-100, to=100, variable=self.rate_var, command=lambda v: self.rate_val.configure(text=f"{int(v):+}%"))
        self.rate_slider.grid(row=1, column=1, padx=5, sticky="ew")
        self.rate_val = ctk.CTkLabel(controls, text=f"{self.rate_var.get():+}%", width=45)
        self.rate_val.grid(row=1, column=2, padx=5, sticky="w")
        
        ctk.CTkLabel(controls, text=i18n.get("volume_label")).grid(row=2, column=0, padx=5, sticky="w")
        self.vol_var = ctk.IntVar(value=self.settings.get("volume"))
        self.vol_slider = ctk.CTkSlider(controls, from_=-100, to=100, variable=self.vol_var, command=lambda v: self.vol_val.configure(text=f"{int(v):+}%"))
        self.vol_slider.grid(row=2, column=1, padx=5, sticky="ew")
        self.vol_val = ctk.CTkLabel(controls, text=f"{self.vol_var.get():+}%", width=45)
        self.vol_val.grid(row=2, column=2, padx=5, sticky="w")

        # --- History Container ---
        self.history_container = ctk.CTkFrame(tab, fg_color="transparent")
        self.history_container.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.history_container.grid_columnconfigure(0, weight=1)
        self.history_container.grid_rowconfigure(1, weight=1)

        # History Title
        ctk.CTkLabel(self.history_container, text=i18n.get("history_panel_title"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=(0, 5), sticky="w")

        # History List
        self.history_list = ctk.CTkScrollableFrame(self.history_container, label_text="")
        self.history_list.grid(row=1, column=0, sticky="nsew")
        self.history_list.grid_columnconfigure(0, weight=1)

        self._update_history_list()
    
    def _update_history_list(self):
        for w in self.history_list.winfo_children(): w.destroy()
        
        records = history_manager.get_records()
        if not records:
             ctk.CTkLabel(self.history_list, text=i18n.get("history_empty"), text_color="gray").pack(pady=10)
             return
             
        for i, rec in enumerate(records):
            frame = ctk.CTkFrame(self.history_list, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            
            # Shorten text
            txt = rec.get("text", "")
            if len(txt) > 20: txt = txt[:20] + "..."
            
            # Button (Text preview) -> Load text & Play
            btn = ctk.CTkButton(frame, text=txt, anchor="w", fg_color="transparent", border_width=1,
                                height=28,
                                text_color=self._get_text_color("transparent"),
                                command=lambda r=rec: self._on_history_click(r))
            btn.pack(side="left", fill="x", expand=True)
            
            # Play Icon (Small)
            play_btn = ctk.CTkButton(frame, text="▶", width=25, height=28, fg_color="transparent",
                                     command=lambda p=rec.get("path"): self._play_audio(p))
            play_btn.pack(side="right", padx=(2,0))

    def _on_history_click(self, record):
        self.text_input.delete("1.0", "end")
        self.text_input.insert("1.0", record.get("text", ""))

        path = record.get("path")
        if path and os.path.exists(path):
            self._play_audio(path)
            copy_file_to_clipboard(path)
            self.update_status("status_history_copied_played", duration=3)
        else:
            self.update_status("status_history_file_missing", error=True)

    def _setup_settings_tab(self):
        tab = self.tab_view.tab(i18n.get("tab_settings"))
        tab.grid_columnconfigure(0, weight=1)
        
        # Output Config
        f1 = ctk.CTkFrame(tab)
        f1.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(f1, text=i18n.get("settings_output_cache_label"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        self.copy_var = ctk.BooleanVar(value=self.settings.get("copy_path_enabled"))
        ctk.CTkSwitch(f1, text=i18n.get("settings_copy_label"), variable=self.copy_var, command=self.save_settings).pack(anchor="w", padx=10, pady=5)
        
        self.autoplay_var = ctk.BooleanVar(value=self.settings.get("autoplay_enabled"))
        ctk.CTkSwitch(f1, text=i18n.get("settings_autoplay_label"), variable=self.autoplay_var, command=self.save_settings).pack(anchor="w", padx=10, pady=5)
        
        f1_sub = ctk.CTkFrame(f1, fg_color="transparent")
        f1_sub.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f1_sub, text=i18n.get("settings_max_files_label")).pack(side="left")
        self.max_files_entry = ctk.CTkEntry(f1_sub, width=60)
        self.max_files_entry.insert(0, str(self.settings.get("max_audio_files")))
        self.max_files_entry.pack(side="left", padx=10)

        # Monitor Config
        f2 = ctk.CTkFrame(tab)
        f2.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        ctk.CTkLabel(f2, text=i18n.get("settings_clipboard_label"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        self.monitor_clip_var = ctk.BooleanVar(value=self.settings.get("monitor_clipboard_enabled"))
        self.sw_clip = ctk.CTkSwitch(f2, text=i18n.get("settings_enable_ctrl_c_label"), variable=self.monitor_clip_var, command=self._toggle_monitors)
        self.sw_clip.pack(anchor="w", padx=10, pady=5)
        
        self.monitor_sel_var = ctk.BooleanVar(value=self.settings.get("monitor_selection_enabled"))
        self.sw_sel = ctk.CTkSwitch(f2, text=i18n.get("settings_enable_selection_label"), variable=self.monitor_sel_var, command=self._toggle_monitors)
        self.sw_sel.pack(anchor="w", padx=10, pady=5)

        self.dual_dot_var = ctk.BooleanVar(value=self.settings.get("dual_blue_dot_enabled"))
        self.sw_dual = ctk.CTkSwitch(f2, text=i18n.get("settings_dual_blue_dot_label"), variable=self.dual_dot_var, command=self._toggle_dual_dot)
        self.sw_dual.pack(anchor="w", padx=10, pady=5)
        
        # Window Config
        f3 = ctk.CTkFrame(tab)
        f3.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        ctk.CTkLabel(f3, text=i18n.get("settings_window_label"), font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        self.tray_var = ctk.BooleanVar(value=self.settings.get("minimize_to_tray"))
        self.sw_tray = ctk.CTkSwitch(f3, text=i18n.get("settings_minimize_to_tray_label"), variable=self.tray_var, command=self.save_settings)
        self.sw_tray.pack(anchor="w", padx=10, pady=5)

    def _setup_appearance_tab(self):
        tab = self.tab_view.tab(i18n.get("tab_appearance"))
        
        ctk.CTkLabel(tab, text=i18n.get("appearance_theme_label")).grid(row=0, column=0, padx=15, pady=15, sticky="w")
        self.theme_seg = ctk.CTkSegmentedButton(tab, values=[i18n.get("appearance_mode_light"), i18n.get("appearance_mode_dark")], command=self._change_appearance_mode)
        self.theme_seg.grid(row=0, column=1, columnspan=3, padx=5, sticky="ew")
        self.theme_seg.set(i18n.get("appearance_mode_light") if self.settings.get("appearance_mode") == "light" else i18n.get("appearance_mode_dark"))
        
        ctk.CTkLabel(tab, text=i18n.get("appearance_color_label")).grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.color_entry = ctk.CTkEntry(tab, placeholder_text="#1F6AA5")
        self.color_entry.insert(0, self.current_custom_color)
        self.color_entry.grid(row=1, column=1, padx=5, sticky="ew")
        
        self.pick_btn = ctk.CTkButton(tab, text=i18n.get("appearance_pick_color_button"), width=30, command=self._pick_color)
        self.pick_btn.grid(row=1, column=2, padx=5)
        
        self.apply_btn = ctk.CTkButton(tab, text=i18n.get("appearance_apply_color_button"), command=self._apply_custom_color)
        self.apply_btn.grid(row=1, column=3, padx=15)

    def _setup_generate_buttons(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(15, 5))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        
        self.btn_left = ctk.CTkButton(frame, text=i18n.get("generate_button_previous"), command=lambda: self._generate_manual('previous'), height=40, font=ctk.CTkFont(size=16, weight="bold"))
        self.btn_right = ctk.CTkButton(frame, text=i18n.get("generate_button_latest"), command=lambda: self._generate_manual('latest'), height=40, font=ctk.CTkFont(size=16, weight="bold"))
        
        self._update_generate_buttons_visibility()

    def _setup_status_bar(self):
        bar = ctk.CTkFrame(self.main_frame, height=25, corner_radius=0)
        bar.grid(row=3, column=0, columnspan=2, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_columnconfigure(1, minsize=110) # Fixed width for progress bar area
        
        self.status_label = ctk.CTkLabel(bar, text=i18n.get("status_ready"), anchor="w", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=0, column=0, sticky="ew", padx=(10, 5))

        self.progress_bar = ctk.CTkProgressBar(bar, height=10, width=100)
        self.progress_bar.grid(row=0, column=1, padx=(0, 5))
        self.progress_bar.set(0)
        self.progress_bar.grid_remove() # Hide initially
        
        ctk.CTkButton(bar, text=i18n.get("lang_button_text"), width=50, height=20, font=ctk.CTkFont(size=10), command=self._toggle_language).grid(row=0, column=2, padx=(5, 10), pady=2)

    def _bind_events(self):
        self.root.bind("<Unmap>", self._handle_minimize)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- Logic Methods ---

    def save_settings(self):
        try:
            # Update settings from UI variables
            self.settings.set("copy_path_enabled", self.copy_var.get())
            self.settings.set("autoplay_enabled", self.autoplay_var.get())
            self.settings.set("minimize_to_tray", self.tray_var.get())
            
            # Handle max files
            try:
                max_f = int(self.max_files_entry.get())
                self.settings.set("max_audio_files", max(1, min(50, max_f)))
            except ValueError:
                self.settings.set("max_audio_files", 20)
                
            # Rate & Volume
            self.settings.set("rate", self.rate_var.get())
            self.settings.set("volume", self.vol_var.get())
            
            self.settings.save_settings()
            # self.update_status("Settings saved") # Optional: usually too verbose
        except Exception as e:
            print(f"Error saving settings: {e}")
            self.update_status("status_settings_save_failed", error=True)

    def refresh_voices_ui(self):
        self.update_status("status_getting_voices", permanent=True)
        self.refresh_btn.configure(state="disabled")
        
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            data = loop.run_until_complete(get_available_voices_async())
            loop.close()
            self.root.after(0, self._on_voices_loaded, data)
            
        import asyncio
        threading.Thread(target=run_async, daemon=True).start()

    def _on_voices_loaded(self, data, from_cache=False):
        self.hierarchical_voice_data = data
        self.refresh_btn.configure(state="normal")
        
        # Build Map
        self.voice_display_to_full_map.clear()
        pattern = re.compile(r", (.*Neural)\)$")
        for lang_data in data.values():
            for voices in lang_data.values():
                for name in voices:
                    match = pattern.search(name)
                    display = match.group(1) if match else name
                    orig = display; count = 1
                    while display in self.voice_display_to_full_map:
                        display = f"{orig}_{count}"
                        count += 1
                    self.voice_display_to_full_map[display] = name

        self._populate_voice_lists()
        if not from_cache:
            self.update_status("status_voices_updated", duration=3)

    def _populate_voice_lists(self):
        self._populate_list('left')
        self._populate_list('right')

    def _populate_list(self, side):
        frame = self.list_left if side == 'left' else self.list_right
        flt = self.filter_left.get() if side == 'left' else self.filter_right.get()
        
        for w in frame.winfo_children(): w.destroy()
        
        if not self.voice_display_to_full_map:
            ctk.CTkLabel(frame, text=i18n.get("debug_no_matching_voices")).pack(pady=20)
            return

        filter_codes = [c.strip().lower() for c in re.split(r'[,\s]+', flt) if c.strip()]
        
        row = 0
        latest = self.settings.get("selected_voice_latest")
        previous = self.settings.get("selected_voice_previous")
        is_dual = self.settings.get("dual_blue_dot_enabled")
        
        for display, full in sorted(self.voice_display_to_full_map.items()):
            if filter_codes:
                match = re.search(r'\(([a-z]{2,3})-', full)
                code = match.group(1).lower() if match else ""
                if code not in filter_codes: continue

            is_l = (full == latest)
            is_p = (is_dual and full == previous and previous != latest)
            
            txt = display
            fg = "transparent"
            text_col = self._get_text_color("transparent")
            
            if is_l:
                txt += " (B)" if is_dual and previous != latest else ""
                fg = self.current_custom_color
                text_col = self._get_contrast_color(fg)
            elif is_p:
                txt += " (A)"
                fg = self._calc_hover_color(self.current_custom_color)
                text_col = self._get_contrast_color(fg)
                
            btn = ctk.CTkButton(frame, text=txt, anchor="w", fg_color=fg, text_color=text_col,
                                hover_color=self._calc_hover_color(fg if fg != "transparent" else self.current_custom_color),
                                command=lambda f=full: self._select_voice(f))
            btn.voice_full_name = full
            btn.voice_display_name = display
            btn.grid(row=row, column=0, padx=5, pady=2, sticky="ew")
            row += 1

    def _select_voice(self, full_name):
        is_dual = self.settings.get("dual_blue_dot_enabled")
        latest = self.settings.get("selected_voice_latest")
        
        if is_dual:
            if full_name == latest: return
            self.settings.set("selected_voice_previous", latest)
            self.settings.set("selected_voice_latest", full_name)
        else:
            if full_name == latest: return
            self.settings.set("selected_voice_latest", full_name)
            self.settings.set("selected_voice_previous", full_name)
            
        self.settings.save_settings()
        self._update_voice_list_styles()
        self._update_generate_buttons_visibility()

    def _update_voice_list_styles(self):
        latest = self.settings.get("selected_voice_latest")
        previous = self.settings.get("selected_voice_previous")
        is_dual = self.settings.get("dual_blue_dot_enabled")
        
        for frame in [self.list_left, self.list_right]:
            for btn in frame.winfo_children():
                if not hasattr(btn, 'voice_full_name'): continue
                
                full = btn.voice_full_name
                display = btn.voice_display_name
                
                is_l = (full == latest)
                is_p = (is_dual and full == previous and previous != latest)
                
                txt = display
                fg = "transparent"
                text_col = self._get_text_color("transparent")
                
                if is_l:
                    txt += " (B)" if is_dual and previous != latest else ""
                    fg = self.current_custom_color
                    text_col = self._get_contrast_color(fg)
                elif is_p:
                    txt += " (A)"
                    fg = self._calc_hover_color(self.current_custom_color)
                    text_col = self._get_contrast_color(fg)
                
                btn.configure(text=txt, fg_color=fg, text_color=text_col,
                              hover_color=self._calc_hover_color(fg if fg != "transparent" else self.current_custom_color))

    def _generate_manual(self, v_type):
        text = self.text_input.get("1.0", "end").strip()
        if not text:
            self.update_status("status_empty_text_error", error=True)
            return
            
        voice = self._get_voice_by_type(v_type)
        if not voice:
             self.update_status("status_no_voice_error", error=True)
             return

        # Disable buttons
        self.btn_left.configure(state="disabled")
        self.btn_right.configure(state="disabled")
        
        self._start_generation(text, voice, v_type, lambda p, e: self._on_manual_complete(p, e, text, voice))

    def _on_manual_complete(self, path, error, text, voice):
        self.btn_left.configure(state="normal")
        self.btn_right.configure(state="normal")
        
        if path:
            base = os.path.basename(path)
            self.update_status(f"{i18n.get('status_success')}: {base}", duration=5)
            
            # Add to history
            history_manager.add_record(text, voice, path)
            self._update_history_list()
            
            if self.settings.get("autoplay_enabled"):
                self._play_audio(path)
            if self.settings.get("copy_path_enabled"):
                copy_file_to_clipboard(path)
        else:
            self.update_status(f"{i18n.get('status_generate_error')}: {error}", error=True)
            
        manage_audio_files(self.settings.get("max_audio_files"))

    def _start_generation(self, text, voice, v_type_display, callback):
        rate = f"{self.rate_var.get():+}%"
        vol = f"{self.vol_var.get():+}%"
        
        disp_name = get_display_voice_name(voice, self.voice_display_to_full_map)
        msg = i18n.get("status_generating_specific", voice_type=v_type_display, name=disp_name)
        self.update_status(msg, permanent=True, progress=True)
        
        generate_audio(text, voice, rate, vol, "+0Hz", callback)

    def _get_voice_by_type(self, v_type):
        l = self.settings.get("selected_voice_latest")
        p = self.settings.get("selected_voice_previous")
        if v_type == 'latest': return l
        if v_type == 'previous':
            return p if p and p != l else l
        return l

    # --- Float & Monitor Logic ---

    def _toggle_monitors(self):
        self.settings.set("monitor_clipboard_enabled", self.monitor_clip_var.get())
        self.settings.set("monitor_selection_enabled", self.monitor_sel_var.get())
        self.settings.save_settings()
        self._update_monitor_state()

    def _update_monitor_state(self):
        self.monitor_manager.start_monitors()
        # Monitor manager handles its own internal adjustment logic
        
        msgs = []
        if self.monitor_clip_var.get(): msgs.append(i18n.get("settings_enable_ctrl_c_label"))
        if self.monitor_sel_var.get(): msgs.append(i18n.get("settings_enable_selection_label"))
        
        if msgs:
            prefix = i18n.get("status_monitor_enabled_prefix", "Monitoring")
            self.update_status(f"{prefix}: {', '.join(msgs)}", duration=3)
        else:
            self.monitor_manager.stop_monitors()
            self.update_status("status_monitor_disabled", duration=3)

    def _on_clipboard_change(self, text):
        # Dispatch to main thread to safely access UI and mouse position
        self.root.after(0, self._handle_clipboard_ui, text)

    def _handle_clipboard_ui(self, text):
        if self.is_generating_from_float: return
        try:
            pos = self.root.winfo_pointerxy()
            self._trigger_float(pos, text)
        except Exception as e:
            print(f"Error getting pointer position: {e}")

    def _on_selection_trigger(self, pos):
        # Dispatch UI update to main thread
        self.root.after(0, self._trigger_float, pos, None)

    def _trigger_float(self, pos, text):
        is_dual = self.settings.get("dual_blue_dot_enabled")
        if is_dual:
            self.float_manager.show_dual_float(pos, text)
        else:
            self.float_manager.show_single_float(pos, text)

    def _handle_float_generate(self, v_type, text_data):
        self.is_generating_from_float = True
        pos = self.root.winfo_pointerxy()
        
        if text_data is None:
            # Selection trigger case
            self.float_manager.show_generating(pos)
            self.monitor_manager.simulate_copy()
            self.root.after(200, lambda: self._continue_float_gen(v_type, pos))
        else:
            # Clipboard trigger case
            self.float_manager.show_generating(pos)
            self._process_float_gen(text_data, v_type, pos)

    def _continue_float_gen(self, v_type, pos):
        try:
            text = sanitize_text(pyperclip.paste())
            if text:
                self._process_float_gen(text, v_type, pos)
            else:
                self.float_manager.destroy_generating_window()
                self.is_generating_from_float = False
        except:
             self.float_manager.destroy_generating_window()
             self.is_generating_from_float = False

    def _process_float_gen(self, text, v_type, pos):
        voice = self._get_voice_by_type(v_type)
        if not voice:
            self.float_manager.destroy_generating_window()
            self.is_generating_from_float = False
            return

        def on_done(path, err):
            self.float_manager.destroy_generating_window()
            if path:
                # Add to history
                history_manager.add_record(text, voice, path)
                self.root.after(0, self._update_history_list)

                if self.settings.get("autoplay_enabled"): self._play_audio(path)
                if self.settings.get("copy_path_enabled"):
                    copy_file_to_clipboard(path)
                    self.float_manager.show_ok(pos)
            self.is_generating_from_float = False
            manage_audio_files(self.settings.get("max_audio_files"))

        # Silent generation (no status bar updates for float to avoid spam/conflict)
        rate = f"{self.rate_var.get():+}%"
        vol = f"{self.vol_var.get():+}%"
        generate_audio(text, voice, rate, vol, "+0Hz", on_done)


    # --- Misc Helpers ---

    def _play_audio(self, path):
        if not os.path.exists(path): return
        try:
            if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Play error: {e}")

    def update_status(self, key_or_text, duration=0, error=False, permanent=False, progress=False):
        # Determine text
        text = i18n.get(key_or_text) if key_or_text else ""
        if error:
            text = f"❌ {text}"
            col = ("#D81B60", "#FF8A80")
        elif "success" in str(key_or_text) or "ready" in str(key_or_text):
            text = f"✅ {text}" if "ready" not in str(key_or_text) else text
            col = ("#00796B", "#80CBC4")
        else:
            col = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
            
        self.status_label.configure(text=text, text_color=col)
        
        if progress:
            self.progress_bar.grid()
            self.progress_bar.configure(progress_color=self.current_custom_color)
            self.progress_bar.start()
        else:
            self.progress_bar.stop()
            self.progress_bar.grid_remove()
            
        if duration > 0 and not permanent:
            self.root.after(duration * 1000, lambda: self.update_status("status_ready"))

    def _toggle_window_visibility(self):
        if self.root.state() == "normal":
            self.root.withdraw()
        else:
            self.root.deiconify()
            self.root.lift()

    def _handle_minimize(self, event):
        if self.root.state() == 'iconic' and self.tray_var.get():
             self.root.withdraw()

    def _toggle_language(self):
        curr = self.settings.get("language")
        new = 'en' if curr == 'zh' else 'zh'
        self.settings.set("language", new)
        self.settings.save_settings()
        i18n.set_language(new)
        # Full restart UI usually best for lang switch, but here we can just update texts
        # For simplicity in this refactor, we prompt restart or just update title
        self.root.title(i18n.get("window_title"))
        self.update_status("status_lang_changed", duration=3)
        # Note: A full dynamic UI text update method is complex, 
        # normally I'd recommend a restart for clean switch.
        messagebox.showinfo("Info", "Please restart app to apply language fully.")

    def _apply_custom_color(self, save=True):
        col = self.color_entry.get().strip()
        import re
        if not re.match(r"^#[0-9a-fA-F]{6}$", col):
            col = DEFAULT_CUSTOM_COLOR
            self.color_entry.delete(0, "end"); self.color_entry.insert(0, col)
            
        self.current_custom_color = col
        if save:
            self.settings.set("custom_theme_color", col)
            self.settings.save_settings()
            
        # Apply to buttons
        hover = self._calc_hover_color(col)
        for btn in [self.refresh_btn, self.pick_btn, self.apply_btn, self.btn_left, self.btn_right]:
             btn.configure(fg_color=col, hover_color=hover)
             
        self._populate_voice_lists() # Refresh lists to apply colors

    def _calc_hover_color(self, hex_color):
        try:
            h=hex_color.lstrip('#')
            r,g,b=tuple(int(h[i:i+2],16) for i in (0,2,4))
            return f"#{max(0,r-20):02x}{max(0,g-20):02x}{max(0,b-20):02x}"
        except: return "#A0A0A0"

    def _get_text_color(self, bg_color):
        if bg_color == "transparent":
            return ctk.ThemeManager.theme["CTkLabel"]["text_color"]
        return self._get_contrast_color(bg_color)

    def _get_contrast_color(self, bg_hex):
         try:
            h=bg_hex.lstrip('#')
            r,g,b=tuple(int(h[i:i+2],16) for i in (0,2,4))
            return "#000000" if (r*0.299 + g*0.587 + b*0.114) > 128 else "#FFFFFF"
         except: return "#000000"

    def _pick_color(self):
        c = colorchooser.askcolor(initialcolor=self.current_custom_color)
        if c and c[1]:
            self.color_entry.delete(0, "end"); self.color_entry.insert(0, c[1])
            self._apply_custom_color()

    def _change_appearance_mode(self, mode_text):
        mode = "light" if "Light" in mode_text or "浅" in mode_text else "dark"
        ctk.set_appearance_mode(mode)
        self.settings.set("appearance_mode", mode)
        self.settings.save_settings()
        self._apply_custom_color()

    def _update_generate_buttons_visibility(self):
        is_dual = self.settings.get("dual_blue_dot_enabled")
        if is_dual:
            self.btn_left.grid(row=0, column=0, padx=(10, 5), sticky="ew")
            self.btn_right.grid(row=0, column=1, padx=(5, 10), sticky="ew")
            self.btn_right.configure(text=i18n.get("generate_button_latest"))
        else:
            self.btn_left.grid_forget()
            self.btn_right.grid(row=0, column=0, columnspan=2, padx=10, sticky="")
            self.btn_right.configure(text=i18n.get("generate_button"))

    def _toggle_dual_dot(self):
        val = self.dual_dot_var.get()
        self.settings.set("dual_blue_dot_enabled", val)
        if not val:
            self.settings.set("selected_voice_previous", self.settings.get("selected_voice_latest"))
        self.settings.save_settings()
        self._update_generate_buttons_visibility()
        self._populate_voice_lists()
        self.update_status("status_dual_dot_enabled" if val else "status_dual_dot_disabled", duration=3)

    def toggle_pin_window(self):
        self.is_pinned = not self.is_pinned
        self.root.attributes('-topmost', self.is_pinned)
        col = self.current_custom_color if self.is_pinned else "transparent"
        self.pin_button.configure(fg_color=col, text_color=self._get_text_color(col))

    def _filter_voices(self, side):
        if side == 'left': self.settings.set("language_filter_left", self.filter_left.get())
        else: self.settings.set("language_filter_right", self.filter_right.get())
        self.settings.save_settings()
        self._populate_list(side)

    def on_closing(self):
        if self.tray_var.get():
            self.root.withdraw()
        else:
            self.quit_application()

    def quit_application(self):
        self.monitor_manager.stop_monitors()
        self.tray_manager.stop()
        self.float_manager.destroy_all()
        try: pygame.mixer.quit()
        except: pass
        try: pygame.quit()
        except: pass
        self.root.quit()
        os._exit(0)