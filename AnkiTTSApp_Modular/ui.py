# ui.py - FINAL VERSION WITH CORRECTIONS

import tkinter as tk
from tkinter import messagebox, colorchooser
import customtkinter as ctk
import pygame
import re
import os
import time
import threading
import json # <<<<<<< 添加: 导入 json 模块 >>>>>>>>>

# Import from our modules
import config
import utils
import tts_utils
import monitor

# ==============================================================================
# Main Application Class
# ==============================================================================
class EdgeTTSApp:
    def __init__(self, root):
        self.root = root; self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        settings = self.load_settings(); self.current_language = settings.get("language", "zh")
        self.root.title(self._("window_title"))
        try: pygame.init(); pygame.mixer.init(); print(self._("debug_init_pygame_ok"))
        except Exception as e: print(self._("debug_init_pygame_fail", e)); messagebox.showerror(self._("error_mixer_init_title"), self._("error_mixer_init_message").format(e))
        self.voice_display_to_full_map = {}; self.hierarchical_voice_data = {}
        self.current_full_voice_name = None; self.current_custom_color = settings.get("custom_theme_color", config.DEFAULT_CUSTOM_COLOR)
        appearance = settings.get("appearance_mode", config.DEFAULT_APPEARANCE_MODE); ctk.set_appearance_mode(appearance)
        self._language_widgets = {}
        self._build_ui(settings)
        self.float_window = None; self.ok_window = None; self.generating_window = None
        self.generating_animation_job = None; self.generating_window_label = None
        self.last_mouse_pos = (0, 0); self._text_for_float_trigger = None
        self._float_window_close_job = None; self._ok_window_close_job = None
        self._apply_custom_color(save=False); self.refresh_voices_ui()
        if self.select_to_audio_var.get(): self.start_clipboard_monitor()

    # --- UI Building Helpers ---
    def _build_ui(self, settings):
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent"); self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1); self.main_frame.grid_rowconfigure(1, weight=1)
        self._build_text_input(); self._build_tab_view(); self._build_voice_tab(settings)
        self._build_settings_tab(settings); self._build_appearance_tab(settings); self._build_bottom_frame()

    def _build_text_input(self):
        frame=ctk.CTkFrame(self.main_frame,fg_color="transparent"); frame.grid(row=0,column=0,sticky="ew",pady=(0,15)); frame.grid_columnconfigure(0,weight=1)
        self.text_input_label=ctk.CTkLabel(frame,text=self._("input_text_label"),font=ctk.CTkFont(size=14,weight="bold")); self.text_input_label.grid(row=0,column=0,sticky="w",pady=(0,5))
        self._language_widgets['input_text_label']=self.text_input_label
        self.text_input=ctk.CTkTextbox(frame,height=100,wrap="word",corner_radius=8,border_width=1); self.text_input.grid(row=1,column=0,sticky="nsew")

    def _build_tab_view(self):
        self.tab_view=ctk.CTkTabview(self.main_frame,corner_radius=8); self.tab_view.grid(row=1,column=0,sticky="nsew",pady=0)
        self._language_widgets['tab_voices']="tab_voices"; self._language_widgets['tab_settings']="tab_settings"; self._language_widgets['tab_appearance']="tab_appearance"
        self.tab_view.add(self._("tab_voices")); self.tab_view.add(self._("tab_settings")); self.tab_view.add(self._("tab_appearance"))

    def _build_voice_tab(self, settings):
        tab=self.tab_view.tab(self._("tab_voices")); tab.grid_columnconfigure((0,1),weight=1); tab.grid_rowconfigure(1,weight=1)
        left=ctk.CTkFrame(tab,fg_color="transparent"); left.grid(row=0,column=0,rowspan=2,padx=(0,5),pady=5,sticky="nsew"); left.grid_rowconfigure(1,weight=1)
        self.language_filter_entry_left=ctk.CTkEntry(left,placeholder_text=self._("filter_language_placeholder")); self.language_filter_entry_left.grid(row=0,column=0,padx=0,pady=(0,5),sticky="ew"); self.language_filter_entry_left.bind("<KeyRelease>",lambda e: self._filter_voices_inline('left'))
        self._language_widgets['filter_language_placeholder_left']=self.language_filter_entry_left
        self.inline_voice_list_frame_left=ctk.CTkScrollableFrame(left,label_text=self._("voice_list_label_1"),height=150); self.inline_voice_list_frame_left.grid(row=1,column=0,padx=0,pady=0,sticky="nsew"); self.inline_voice_list_frame_left.grid_columnconfigure(0,weight=1)
        self._language_widgets['voice_list_label_1']=self.inline_voice_list_frame_left
        right=ctk.CTkFrame(tab,fg_color="transparent"); right.grid(row=0,column=1,rowspan=2,padx=(5,0),pady=5,sticky="nsew"); right.grid_rowconfigure(1,weight=1)
        self.language_filter_entry_right=ctk.CTkEntry(right,placeholder_text=self._("filter_language_placeholder")); self.language_filter_entry_right.grid(row=0,column=0,padx=0,pady=(0,5),sticky="ew"); self.language_filter_entry_right.bind("<KeyRelease>",lambda e: self._filter_voices_inline('right'))
        self._language_widgets['filter_language_placeholder_right']=self.language_filter_entry_right
        self.inline_voice_list_frame_right=ctk.CTkScrollableFrame(right,label_text=self._("voice_list_label_2"),height=150); self.inline_voice_list_frame_right.grid(row=1,column=0,padx=0,pady=0,sticky="nsew"); self.inline_voice_list_frame_right.grid_columnconfigure(0,weight=1)
        self._language_widgets['voice_list_label_2']=self.inline_voice_list_frame_right
        sfl=settings.get("language_filter_left","zh"); sfr=settings.get("language_filter_right","en")
        self.language_filter_entry_left.insert(0,sfl); self.language_filter_entry_right.insert(0,sfr)
        ctrl=ctk.CTkFrame(tab,fg_color="transparent"); ctrl.grid(row=2,column=0,columnspan=2,pady=(10,0),sticky="ew"); ctrl.grid_columnconfigure(1,weight=1)
        self.refresh_button=ctk.CTkButton(ctrl,text=self._("refresh_voices_button"),command=self.refresh_voices_ui,font=ctk.CTkFont(size=12)); self.refresh_button.grid(row=0,column=0,columnspan=3,padx=0,pady=(0,10),sticky="ew")
        self._language_widgets['refresh_voices_button']=self.refresh_button
        self.rate_label=ctk.CTkLabel(ctrl,text=self._("rate_label")); self.rate_label.grid(row=1,column=0,padx=(0,5),pady=5,sticky="w")
        self._language_widgets['rate_label']=self.rate_label
        self.rate_slider_var=ctk.IntVar(value=settings.get("rate",0)); self.rate_slider=ctk.CTkSlider(ctrl,from_=-100,to=100,number_of_steps=40,variable=self.rate_slider_var,command=self.update_rate_label); self.rate_slider.grid(row=1,column=1,padx=5,pady=5,sticky="ew")
        self.rate_value_label=ctk.CTkLabel(ctrl,text=f"{self.rate_slider_var.get():+}%",width=45); self.rate_value_label.grid(row=1,column=2,padx=(5,0),pady=5,sticky="w")
        self.volume_label=ctk.CTkLabel(ctrl,text=self._("volume_label")); self.volume_label.grid(row=2,column=0,padx=(0,5),pady=5,sticky="w")
        self._language_widgets['volume_label']=self.volume_label
        self.volume_slider_var=ctk.IntVar(value=settings.get("volume",0)); self.volume_slider=ctk.CTkSlider(ctrl,from_=-100,to=100,number_of_steps=40,variable=self.volume_slider_var,command=self.update_volume_label); self.volume_slider.grid(row=2,column=1,padx=5,pady=5,sticky="ew")
        self.volume_value_label=ctk.CTkLabel(ctrl,text=f"{self.volume_slider_var.get():+}%",width=45); self.volume_value_label.grid(row=2,column=2,padx=(5,0),pady=5,sticky="w")

    def _build_settings_tab(self, settings):
        tab=self.tab_view.tab(self._("tab_settings")); tab.grid_columnconfigure(0,weight=1)
        oc_frame=ctk.CTkFrame(tab); oc_frame.pack(fill="x",padx=10,pady=10); oc_frame.grid_columnconfigure(1,weight=1)
        self.settings_output_cache_label_widget=ctk.CTkLabel(oc_frame,text=self._("settings_output_cache_label"),font=ctk.CTkFont(weight="bold")); self.settings_output_cache_label_widget.grid(row=0,column=0,columnspan=3,pady=(5,10),padx=10,sticky="w")
        self._language_widgets['settings_output_cache_label']=self.settings_output_cache_label_widget
        self.copy_to_clipboard_var=ctk.BooleanVar(value=settings.get("copy_path_enabled",True)); self.copy_to_clipboard_switch=ctk.CTkSwitch(oc_frame,text=self._("settings_copy_label"),variable=self.copy_to_clipboard_var,onvalue=True,offvalue=False); self.copy_to_clipboard_switch.grid(row=1,column=0,padx=10,pady=5,sticky="w")
        self._language_widgets['settings_copy_label']=self.copy_to_clipboard_switch
        self.play_audio_var=ctk.BooleanVar(value=settings.get("autoplay_enabled",False)); self.play_audio_switch=ctk.CTkSwitch(oc_frame,text=self._("settings_autoplay_label"),variable=self.play_audio_var,onvalue=True,offvalue=False); self.play_audio_switch.grid(row=1,column=1,padx=10,pady=5,sticky="w")
        self._language_widgets['settings_autoplay_label']=self.play_audio_switch
        self.settings_max_files_label_widget=ctk.CTkLabel(oc_frame,text=self._("settings_max_files_label")); self.settings_max_files_label_widget.grid(row=2,column=0,padx=(10,5),pady=(5,10),sticky="w")
        self._language_widgets['settings_max_files_label']=self.settings_max_files_label_widget
        self.max_files_entry=ctk.CTkEntry(oc_frame,width=60); self.max_files_entry.insert(0,str(settings.get("max_audio_files",config.DEFAULT_MAX_AUDIO_FILES))); self.max_files_entry.grid(row=2,column=1,padx=5,pady=(5,10),sticky="w")
        clip_frame=ctk.CTkFrame(tab); clip_frame.pack(fill="x",padx=10,pady=(0,10)); clip_frame.grid_columnconfigure(0,weight=1)
        self.settings_clipboard_label_widget=ctk.CTkLabel(clip_frame,text=self._("settings_clipboard_label"),font=ctk.CTkFont(weight="bold")); self.settings_clipboard_label_widget.grid(row=0,column=0,columnspan=2,pady=(5,10),padx=10,sticky="w")
        self._language_widgets['settings_clipboard_label']=self.settings_clipboard_label_widget
        self.select_to_audio_var=ctk.BooleanVar(value=settings.get("monitor_enabled",False)); self.select_to_audio_switch=ctk.CTkSwitch(clip_frame,text=self._("settings_enable_ctrl_c_label"),variable=self.select_to_audio_var,command=self.toggle_select_to_audio,onvalue=True,offvalue=False); self.select_to_audio_switch.grid(row=1,column=0,columnspan=2,padx=10,pady=5,sticky="w")
        self._language_widgets['settings_enable_ctrl_c_label']=self.select_to_audio_switch
        self.select_trigger_var=ctk.BooleanVar(value=settings.get("select_trigger_enabled",False)); self.select_trigger_switch=ctk.CTkSwitch(clip_frame,text=self._("settings_enable_selection_label"),variable=self.select_trigger_var,command=self.save_settings,onvalue=True,offvalue=False); self.select_trigger_switch.grid(row=2,column=0,columnspan=2,padx=10,pady=(0,10),sticky="w")
        self._language_widgets['settings_enable_selection_label']=self.select_trigger_switch

    def _build_appearance_tab(self, settings):
        tab=self.tab_view.tab(self._("tab_appearance")); tab.grid_columnconfigure(1,weight=1)
        self.appearance_theme_label_widget=ctk.CTkLabel(tab,text=self._("appearance_theme_label")); self.appearance_theme_label_widget.grid(row=0,column=0,padx=(15,5),pady=15,sticky="w")
        self._language_widgets['appearance_theme_label']=self.appearance_theme_label_widget
        self.appearance_mode_segmented_button=ctk.CTkSegmentedButton(tab,values=[self._("appearance_mode_light"),self._("appearance_mode_dark")],command=self._change_appearance_mode); self.appearance_mode_segmented_button.grid(row=0,column=1,columnspan=3,padx=5,pady=15,sticky="ew")
        app_mode=settings.get("appearance_mode",config.DEFAULT_APPEARANCE_MODE)
        init_mode_txt=self._("appearance_mode_light") if app_mode=='light' else self._("appearance_mode_dark"); self.appearance_mode_segmented_button.set(init_mode_txt)
        self._language_widgets['appearance_mode_light']=self.appearance_mode_segmented_button
        self._language_widgets['appearance_mode_dark']=self.appearance_mode_segmented_button
        self.appearance_color_label_widget=ctk.CTkLabel(tab,text=self._("appearance_color_label")); self.appearance_color_label_widget.grid(row=1,column=0,padx=(15,5),pady=(5,15),sticky="w")
        self._language_widgets['appearance_color_label']=self.appearance_color_label_widget
        self.custom_color_entry=ctk.CTkEntry(tab,placeholder_text="#1F6AA5"); self.custom_color_entry.grid(row=1,column=1,padx=5,pady=(5,15),sticky="ew"); self.custom_color_entry.insert(0,self.current_custom_color or "")
        self.pick_color_button=ctk.CTkButton(tab,text=self._("appearance_pick_color_button"),width=30,command=self._pick_custom_color); self.pick_color_button.grid(row=1,column=2,padx=(0,5),pady=(5,15),sticky="w")
        self.apply_color_button=ctk.CTkButton(tab,text=self._("appearance_apply_color_button"),command=self._apply_custom_color); self.apply_color_button.grid(row=1,column=3,padx=(0,15),pady=(5,15),sticky="e")
        self._language_widgets['appearance_apply_color_button']=self.apply_color_button

    def _build_bottom_frame(self):
        frame=ctk.CTkFrame(self.main_frame,fg_color="transparent"); frame.grid(row=2,column=0,sticky="ew",pady=(15,5)); frame.grid_columnconfigure(0,weight=1)
        self.generate_button=ctk.CTkButton(frame,text=self._("generate_button"),command=self.generate_audio_manual,height=40,font=ctk.CTkFont(size=16,weight="bold"),corner_radius=10); self.generate_button.grid(row=0,column=0,pady=(0,15),sticky="")
        self._language_widgets['generate_button']=self.generate_button
        self.status_bar_frame=ctk.CTkFrame(self.main_frame,height=25,corner_radius=0); self.status_bar_frame.grid(row=3,column=0,sticky="ew"); self.status_bar_frame.grid_columnconfigure(0,weight=1); self.status_bar_frame.grid_columnconfigure(1,weight=0); self.status_bar_frame.grid_columnconfigure(2,weight=0)
        self.status_label=ctk.CTkLabel(self.status_bar_frame,text=self._("status_ready"),anchor="w",font=ctk.CTkFont(size=12)); self.status_label.grid(row=0,column=0,sticky="ew",padx=(10,5))
        self.progress_bar=ctk.CTkProgressBar(self.status_bar_frame,height=10,width=100,corner_radius=5); self.progress_bar.set(0); self.progress_bar.grid_remove()
        self.language_button=ctk.CTkButton(self.status_bar_frame,text=self._("lang_button_text"),width=50,height=20,font=ctk.CTkFont(size=10),command=self.toggle_language); self.language_button.grid(row=0,column=2,padx=(5,10),sticky="e")

    # --------------------------------------------------------------------------
    # Language Handling
    # --------------------------------------------------------------------------
    def _(self, key, *args):
        lang_map = config.TRANSLATIONS.get(self.current_language, config.TRANSLATIONS.get('zh', {}))
        text = lang_map.get(key, key)
        try: return text.format(*args) if args else text
        except: return text

    def toggle_language(self):
        self.current_language = 'en' if self.current_language == 'zh' else 'zh'
        print(f"Switching language to: {self.current_language}")
        self._update_ui_language()
        self.save_settings()
        lang_name_key = f"lang_name_{self.current_language}"
        self.update_status("status_lang_changed", duration=3, args_tuple=(self._(lang_name_key),))

    def _update_ui_language(self):
        self.root.title(self._("window_title"))
        for key, widget in self._language_widgets.items():
            if key.startswith("tab_") or key.startswith("appearance_mode_"): continue
            if widget and widget.winfo_exists():
                try:
                    if isinstance(widget,(ctk.CTkLabel,ctk.CTkButton,ctk.CTkSwitch)): widget.configure(text=self._(key))
                    elif isinstance(widget,ctk.CTkEntry): widget.configure(placeholder_text=self._(key))
                    elif isinstance(widget,ctk.CTkScrollableFrame): widget.configure(label_text=self._(key))
                except Exception as e: print(f"Warn: Update widget '{key}' failed: {e}")
        tab_map = {"tab_voices":self._("tab_voices"), "tab_settings":self._("tab_settings"), "tab_appearance":self._("tab_appearance")}
        current_tab = self.tab_view.get(); new_selected = None
        for key, new_name in tab_map.items():
            old_lang = 'en' if self.current_language == 'zh' else 'zh'
            old_name = config.TRANSLATIONS.get(old_lang, {}).get(key, new_name)
            try:
                if old_name in self.tab_view._name_list: self.tab_view.rename(old_name, new_name)
                if current_tab == old_name: new_selected = new_name
                elif current_tab == new_name: new_selected = new_name
            except Exception as e: print(f"Warn: Rename tab '{old_name}'->'{new_name}' failed: {e}")
        if new_selected:
            try: self.tab_view.set(new_selected)
            except Exception as e: print(f"Warn: Set tab failed '{new_selected}': {e}")
        try:
            seg_btn = self._language_widgets.get('appearance_mode_light')
            if seg_btn and seg_btn.winfo_exists():
                vals = [self._("appearance_mode_light"), self._("appearance_mode_dark")]; mode = ctk.get_appearance_mode()
                sel_text = self._("appearance_mode_light") if mode == 'light' else self._("appearance_mode_dark")
                seg_btn.configure(values=vals); seg_btn.set(sel_text)
        except Exception as e: print(f"Warn: Update segmented button failed: {e}")
        if hasattr(self,'status_label') and self.status_label.winfo_exists():
             current = self.status_label.cget("text")
             ready_zh = config.TRANSLATIONS.get('zh',{}).get('status_ready','?')
             ready_en = config.TRANSLATIONS.get('en',{}).get('status_ready','?')
             if current.endswith(ready_zh) or current.endswith(ready_en): self.status_label.configure(text=self._("status_ready"))
        self._populate_inline_voice_list('left'); self._populate_inline_voice_list('right')

    # --------------------------------------------------------------------------
    # UI 更新与状态管理方法 (使用翻译 key)
    # --------------------------------------------------------------------------
    def update_status(self, message_key_or_literal, duration=0, error=False, permanent=False, show_progress=False, args_tuple=None):
        """Updates status bar. Accepts a translation key or literal string."""
        # <<<<<<< 修改: 使用 config.status_update_job >>>>>>>>>
        def _update():
            # <<<<<<< 修改: 使用 config.status_update_job >>>>>>>>>
            if config.status_update_job:
                try:
                    if hasattr(self,'status_label') and self.status_label.winfo_exists(): self.status_label.after_cancel(config.status_update_job)
                except: pass
                config.status_update_job = None # Reset job ID in config

            args = args_tuple or ()
            is_key = isinstance(message_key_or_literal, str) and message_key_or_literal in config.TRANSLATIONS.get(self.current_language, {})
            message = self._(message_key_or_literal, *args) if is_key else message_key_or_literal.format(*args)
            status_text = message
            try: label_fg=ctk.ThemeManager.theme["CTkLabel"]["text_color"]; text_color=label_fg[ctk.get_appearance_mode()=='dark'] if isinstance(label_fg,(list,tuple)) else label_fg
            except: text_color=("#000000","#FFFFFF")
            check="✅"; cross="❌"; hour="⏳"
            if error: status_text = f"{cross} {message}"; text_color=("#D81B60","#FF8A80")
            elif (is_key and any(k in message_key_or_literal for k in ["success","copied","updated","saved","ready","enabled","changed"])) or check in status_text:
                if not status_text.startswith(check): status_text = f"{check} {message}"
                text_color=("#00796B","#80CBC4")
            elif (is_key and any(k in message_key_or_literal for k in ["generating","getting"])) or hour in status_text:
                 if not status_text.startswith(hour): status_text = f"{hour} {message}"
            if hasattr(self,'status_label') and self.status_label.winfo_exists(): self.status_label.configure(text=status_text, text_color=text_color)
            if hasattr(self, 'progress_bar'):
                if show_progress:
                    self.progress_bar.grid(row=0, column=1, padx=(0, 10), sticky="e")
                    try: t_color=ctk.ThemeManager.theme["CTkProgressBar"]["progress_color"]; d_color=t_color[ctk.get_appearance_mode()=='dark'] if isinstance(t_color,(list,tuple)) else t_color; p_color=self.current_custom_color or d_color
                    except: p_color=self.current_custom_color or "#1F6AA5"
                    self.progress_bar.configure(mode="indeterminate", progress_color=p_color)
                    if hasattr(self.progress_bar,'start'): self.progress_bar.start()
                else:
                    if hasattr(self.progress_bar,'stop'): self.progress_bar.stop()
                    self.progress_bar.grid_remove()
            if not permanent and duration > 0:
                 if hasattr(self,'status_label') and self.status_label.winfo_exists():
                     # <<<<<<< 修改: 使用 config.status_update_job >>>>>>>>>
                     config.status_update_job = self.status_label.after(duration*1000, lambda: self.update_status("status_ready"))

        if threading.current_thread() is not threading.main_thread():
            if hasattr(self,'root') and self.root.winfo_exists(): self.root.after(0, _update)
        else: _update()


    def update_rate_label(self, value): val=int(value); self.rate_value_label.configure(text=f"{val:+}%")
    def update_volume_label(self, value): val=int(value); self.volume_value_label.configure(text=f"{val:+}%")

    def refresh_voices_ui(self):
        self.update_status("status_getting_voices", permanent=True)
        if hasattr(self, 'refresh_button'): self.refresh_button.configure(state="disabled")
        for frame in [self.inline_voice_list_frame_left, self.inline_voice_list_frame_right]:
             if frame and frame.winfo_exists():
                 for widget in frame.winfo_children(): widget.destroy()
                 ctk.CTkLabel(frame, text=self._("status_getting_voices"), text_color="gray").pack(pady=20)
        tts_utils.refresh_voices_list(app_instance=self)

    def update_voice_ui(self, hierarchical_voice_data):
        if hasattr(self, 'refresh_button'): self.refresh_button.configure(state="normal")
        self.hierarchical_voice_data = hierarchical_voice_data; self.voice_display_to_full_map.clear()
        if not hierarchical_voice_data:
            print(self._("debug_voice_ui_no_data"))
            for frame in [self.inline_voice_list_frame_left, self.inline_voice_list_frame_right]:
                if frame and frame.winfo_exists():
                    for widget in frame.winfo_children(): widget.destroy()
                    ctk.CTkLabel(frame, text=self._("debug_voice_load_failed_ui"), text_color="red").pack(pady=20)
            self.update_status("status_generate_error", error=True); return
        pattern = re.compile(r", (.*Neural)\)$")
        for lang_data in hierarchical_voice_data.values():
            for voices in lang_data.values():
                for name in voices:
                    match=pattern.search(name); display=match.group(1) if match else name
                    orig=display; count=1
                    while display in self.voice_display_to_full_map: display=f"{orig}_{count}"; count+=1
                    self.voice_display_to_full_map[display] = name
        settings = self.load_settings(); selected=settings.get("selected_voice", config.DEFAULT_VOICE)
        if selected in self.voice_display_to_full_map.values(): self.current_full_voice_name = selected
        elif config.DEFAULT_VOICE in self.voice_display_to_full_map.values(): self.current_full_voice_name = config.DEFAULT_VOICE
        else: available = list(self.voice_display_to_full_map.values()); self.current_full_voice_name = available[0] if available else None
        self._populate_inline_voice_list('left'); self._populate_inline_voice_list('right')
        print(self._("debug_voice_ui_updated", self.current_full_voice_name))
        self.update_status("status_voices_updated", duration=3)

    # --------------------------------------------------------------------------
    # 内联声音选择器方法 (使用翻译)
    # --------------------------------------------------------------------------
    def _populate_inline_voice_list(self, side):
        frame=self.inline_voice_list_frame_left if side=='left' else self.inline_voice_list_frame_right
        filter_entry=self.language_filter_entry_left if side=='left' else self.language_filter_entry_right
        if not frame: return
        filter_term = filter_entry.get() if hasattr(self, f'language_filter_entry_{side}') else ""
        for widget in frame.winfo_children(): widget.destroy()
        row=0; codes=[c.strip().lower() for c in re.split(r'[,\s]+', filter_term) if c.strip()]
        if not self.voice_display_to_full_map: ctk.CTkLabel(frame, text=self._("debug_no_matching_voices"), text_color="gray").grid(row=0, column=0, pady=20); return
        sorted_voices=sorted(self.voice_display_to_full_map.items()); found=False
        for name, full_name in sorted_voices:
            apply_f=len(codes)>0; match_f=False
            if apply_f: match=re.search(r'\(([a-z]{2,3})-', full_name); code=match.group(1).lower() if match else ""; match_f=(code in codes)
            if apply_f and not match_f: continue
            found=True; selected=(full_name==self.current_full_voice_name)
            try: fg=ctk.ThemeManager.theme["CTkButton"]["fg_color"]; fg_mode=fg[ctk.get_appearance_mode()=='dark'] if isinstance(fg,(list,tuple)) else fg
            except: fg_mode="#1F6AA5"
            btn_fg=self.current_custom_color or fg_mode; btn_hover=self._calculate_hover_color(btn_fg)
            try: txt=ctk.ThemeManager.theme["CTkLabel"]["text_color"]; txt_n=txt[ctk.get_appearance_mode()=='dark'] if isinstance(txt,(list,tuple)) else txt
            except: txt_n="#000000"
            txt_s = self._get_contrasting_text_color(btn_fg)
            btn=ctk.CTkButton(frame,text=name,anchor="w",fg_color=btn_fg if selected else "transparent",hover_color=btn_hover,text_color=txt_s if selected else txt_n,command=lambda fn=full_name:self._select_voice_inline(fn))
            btn.grid(row=row, column=0, padx=5, pady=2, sticky="ew"); row+=1
        if not found: ctk.CTkLabel(frame, text=self._("debug_no_matching_voices"), text_color="gray").grid(row=0, column=0, pady=20)

    def _filter_voices_inline(self, side): self._populate_inline_voice_list(side); self.save_settings()
    def _select_voice_inline(self, full_name):
        if self.current_full_voice_name != full_name:
            self.current_full_voice_name=full_name; print(self._("debug_voice_selected", full_name))
            self._populate_inline_voice_list('left'); self._populate_inline_voice_list('right'); self.save_settings()

    # --------------------------------------------------------------------------
    # 主题与颜色切换方法 (使用翻译)
    # --------------------------------------------------------------------------
    def _change_appearance_mode(self, selected_value):
        mode = 'light' if selected_value == self._("appearance_mode_light") else 'dark'
        print(f"Switching appearance mode to: {mode}"); ctk.set_appearance_mode(mode); self._apply_custom_color(save=True)
    def _pick_custom_color(self):
        initial = self.custom_color_entry.get() or self.current_custom_color or config.DEFAULT_CUSTOM_COLOR
        chosen = colorchooser.askcolor(title=self._("appearance_color_label"), initialcolor=initial)
        if chosen and chosen[1]: hex_color = chosen[1]; self.custom_color_entry.delete(0, tk.END); self.custom_color_entry.insert(0, hex_color); self._apply_custom_color()
    def _apply_custom_color(self, save=True):
        new_color = self.custom_color_entry.get().strip()
        if not re.match(r"^#[0-9a-fA-F]{6}$", new_color):
            if new_color: messagebox.showerror(self._("error_invalid_color_title"), self._("error_invalid_color_message", new_color))
            self.current_custom_color = config.DEFAULT_CUSTOM_COLOR; self.custom_color_entry.delete(0, tk.END); self.custom_color_entry.insert(0, self.current_custom_color)
            new_color = self.current_custom_color; save = False
        else: self.current_custom_color = new_color
        print(self._("debug_apply_color", self.current_custom_color)); hover = self._calculate_hover_color(self.current_custom_color)
        # Apply colors...
        buttons=[getattr(self,n,None) for n in ['generate_button','refresh_button','apply_color_button','pick_color_button']]
        for b in buttons:
             if b: b.configure(fg_color=self.current_custom_color, hover_color=hover)
        switches=[getattr(self,n,None) for n in ['copy_to_clipboard_switch','play_audio_switch','select_to_audio_switch','select_trigger_switch']]
        for s in switches:
             if s: s.configure(progress_color=self.current_custom_color)
        sliders=[getattr(self,n,None) for n in ['rate_slider','volume_slider']]
        for s in sliders:
             if s: s.configure(button_color=self.current_custom_color, progress_color=self.current_custom_color, button_hover_color=hover)
        if hasattr(self,'progress_bar'):
             try: t_color=ctk.ThemeManager.theme["CTkProgressBar"]["progress_color"]; d_color=t_color[ctk.get_appearance_mode()=='dark'] if isinstance(t_color,(list,tuple)) else t_color; color=self.current_custom_color or d_color
             except: color=self.current_custom_color or "#1F6AA5"
             self.progress_bar.configure(progress_color=color)
        if hasattr(self,'tab_view'): self.tab_view.configure(segmented_button_selected_color=self.current_custom_color, segmented_button_selected_hover_color=hover)
        if hasattr(self,'appearance_mode_segmented_button'): self.appearance_mode_segmented_button.configure(selected_color=self.current_custom_color, selected_hover_color=hover)
        self._populate_inline_voice_list('left'); self._populate_inline_voice_list('right')
        if save: self.save_settings()

    def _calculate_hover_color(self, hex_color): # No change
        try: h=hex_color.lstrip('#'); r,g,b=tuple(int(h[i:i+2],16) for i in (0,2,4)); hr,hg,hb=max(0,r-20),max(0,g-20),max(0,b-20); return f"#{hr:02x}{hg:02x}{hb:02x}"
        except:
            try: d=ctk.ThemeManager.theme["CTkButton"]["hover_color"]; return d[ctk.get_appearance_mode()=='dark'] if isinstance(d,(list,tuple)) else d
            except: return "#A0A0A0"
    def _get_contrasting_text_color(self, bg_hex_color): # No change
        try: h=bg_hex_color.lstrip('#'); r,g,b=tuple(int(h[i:i+2],16) for i in (0,2,4)); br=(r*299+g*587+b*114)/1000; return "#000000" if br>128 else "#FFFFFF"
        except:
            try: d=ctk.ThemeManager.theme["CTkLabel"]["text_color"]; return d[ctk.get_appearance_mode()=='dark'] if isinstance(d,(list,tuple)) else d
            except: return "#000000"

    # --------------------------------------------------------------------------
    # 设置加载与保存 (使用 config defaults)
    # --------------------------------------------------------------------------
    def load_settings(self):
        defaults = {"language":"zh", "copy_path_enabled": True, "autoplay_enabled": False, "monitor_enabled": False, "select_trigger_enabled": False, "max_audio_files": config.DEFAULT_MAX_AUDIO_FILES, "selected_voice": config.DEFAULT_VOICE, "rate": 0, "volume": 0, "appearance_mode": config.DEFAULT_APPEARANCE_MODE, "language_filter_left": "zh", "language_filter_right": "en", "custom_theme_color": config.DEFAULT_CUSTOM_COLOR}
        try:
            if os.path.exists(config.SETTINGS_FILE):
                with open(config.SETTINGS_FILE, "r", encoding="utf-8") as f: settings_loaded = json.load(f)
                merged = defaults.copy(); merged.update(settings_loaded)
                loaded_color = merged.get("custom_theme_color")
                lang_for_print = merged.get("language", "zh")
                # Use loaded translations if available for printing error, else use default
                trans = config.TRANSLATIONS.get(lang_for_print, config.TRANSLATIONS.get('zh', {}))
                if not re.match(r"^#[0-9a-fA-F]{6}$", loaded_color):
                    print(trans.get('debug_invalid_color_loaded',"Warn: Invalid color").format(loaded_color)); merged["custom_theme_color"] = config.DEFAULT_CUSTOM_COLOR
                if merged.get("language") not in ["zh", "en"]: print(f"Warn: Invalid lang '{merged.get('language')}', using zh."); merged["language"] = "zh"
                return merged
        except Exception as e: print(f"Load settings failed: {e}")
        return defaults

    def save_settings(self):
        try: max_f = int(self.max_files_entry.get()); max_f = max_f if 1 <= max_f <= 50 else config.DEFAULT_MAX_AUDIO_FILES
        except: max_f = config.DEFAULT_MAX_AUDIO_FILES
        filter_l = getattr(self,'language_filter_entry_left',None); filter_r = getattr(self,'language_filter_entry_right',None)
        settings = { "language": self.current_language, "selected_voice": self.current_full_voice_name or config.DEFAULT_VOICE, "copy_path_enabled": self.copy_to_clipboard_var.get(), "autoplay_enabled": self.play_audio_var.get(), "monitor_enabled": self.select_to_audio_var.get(), "select_trigger_enabled": self.select_trigger_var.get(), "max_audio_files": max_f, "rate": self.rate_slider_var.get(), "volume": self.volume_slider_var.get(), "appearance_mode": ctk.get_appearance_mode().lower(), "language_filter_left": filter_l.get() if filter_l else "zh", "language_filter_right": filter_r.get() if filter_r else "en", "custom_theme_color": self.current_custom_color or config.DEFAULT_CUSTOM_COLOR }
        try:
            with open(config.SETTINGS_FILE, "w", encoding="utf-8") as f: json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception as e: print(self._("debug_settings_save_failed", e)); self.update_status("status_settings_save_failed", error=True)

    # --------------------------------------------------------------------------
    # 音频生成与处理方法 (使用 utils/tts_utils)
    # --------------------------------------------------------------------------
    def generate_audio_manual(self):
        text = self.text_input.get("1.0", "end").strip()
        if not text: self.update_status("status_empty_text_error", error=True, duration=5); return
        voice = self.current_full_voice_name
        if not voice: self.update_status("status_no_voice_error", error=True, duration=5); return
        rate=f"{self.rate_slider_var.get():+}%"; volume=f"{self.volume_slider_var.get():+}%"; pitch="+0Hz"
        def on_complete(path, error=None):
            if self.root.winfo_exists(): self.generate_button.configure(state="normal")
            if path:
                base = os.path.basename(path); self.update_status(f"{self._('status_success')}: {base}", duration=10); print(self._("debug_audio_complete", path))
                play = self.play_audio_var.get(); print(self._("debug_autoplay_manual", play))
                if play: self.play_audio_pygame(path)
                if self.copy_to_clipboard_var.get(): utils.copy_file_to_clipboard(path, app_instance=self)
            else: err=f"{self._('status_generate_error')}: {error or '??'}"; print(err); self.update_status(err, error=True)
            utils.manage_audio_files(app_instance=self)
        self.generate_button.configure(state="disabled"); name = self._get_display_voice_name(voice)
        self.update_status(f"{self._('status_generating')} ({name})...", permanent=True, show_progress=True)
        tts_utils.generate_audio(text, voice, rate, volume, pitch, on_complete, app_instance=self)

    def play_audio_pygame(self, path): # Remains internal to UI
        print(self._("debug_pygame_play_call", path))
        if not pygame.mixer.get_init(): print("ERROR: Pygame mixer not init."); self.update_status("status_mixer_init_error", error=True); return
        if not os.path.exists(path): print(f"ERROR: File not found: {path}"); self.update_status("status_file_not_found", error=True); return
        try:
            if pygame.mixer.music.get_busy(): print(self._("debug_pygame_stop_current")); pygame.mixer.music.stop(); pygame.mixer.music.unload(); time.sleep(0.05)
            print(self._("debug_pygame_load_play", path)); pygame.mixer.music.load(path); pygame.mixer.music.play(); print(self._("debug_pygame_play_start"))
        except pygame.error as e: print(self._("debug_pygame_play_error", e)); self.update_status(f"{self._('status_play_error')}: {e}", error=True)
        except Exception as e: print(self._("debug_play_unknown_error", e)); self.update_status(f"{self._('status_play_error')}: {e}", error=True)

    def _get_display_voice_name(self, name): # Remains internal to UI
        if not name: return "Unknown"
        for dn, fn in self.voice_display_to_full_map.items():
            if fn == name: return dn
        match = re.search(r", (.*Neural)\)$", name); return match.group(1) if match else name

    # --------------------------------------------------------------------------
    # 浮窗相关方法 (SyntaxError 修复 + 使用 utils/tts_utils)
    # --------------------------------------------------------------------------
    def show_float_window(self, text): # Internal UI method (corrected)
        if self.float_window:
            try: self.float_window.destroy()
            except: pass
            self.float_window=None
        self.destroy_generating_window(); self.destroy_ok_window()
        self._text_for_float_trigger = text
        self.float_window = tk.Toplevel(self.root); self.float_window.overrideredirect(True)
        x, y = self.last_mouse_pos; self.float_window.geometry(f"50x50+{x+10}+{y+10}"); self.float_window.attributes("-topmost", True)
        btn = ctk.CTkButton( self.float_window, text="音", width=50, height=50, corner_radius=25, font=ctk.CTkFont(size=20, weight="bold"), fg_color="#1E90FF", hover_color="#1C86EE", text_color="white", command=self.trigger_generate_from_float )
        btn.pack(fill="both", expand=True)
        if hasattr(self, '_float_window_close_job') and self._float_window_close_job:
            try: self.root.after_cancel(self._float_window_close_job)
            except: pass
            self._float_window_close_job = None
        def auto_close():
            if self.float_window:
                try: self.float_window.destroy()
                except: pass
            self.float_window = None; self._float_window_close_job = None
        self._float_window_close_job = self.float_window.after(config.FLOAT_WINDOW_TIMEOUT * 1000, auto_close)

    def show_generating_window(self, position): # Internal UI method
        self.destroy_float_window(); self.destroy_ok_window(); self.destroy_generating_window()
        self.generating_window = tk.Toplevel(self.root); self.generating_window.overrideredirect(True)
        x, y = position; self.generating_window.geometry(f"50x50+{x+10}+{y+10}"); self.generating_window.attributes("-topmost", True)
        self.generating_window_label = ctk.CTkButton( self.generating_window, text="/", width=50, height=50, corner_radius=25, font=ctk.CTkFont(size=20, weight="bold"), fg_color="#4CAF50", hover_color="#45a049", text_color="white", state="disabled" )
        self.generating_window_label.pack(fill="both", expand=True); self._animate_green_dot()
    def _animate_green_dot(self, char_index=0): # Internal UI method
        if self.generating_window and self.generating_window.winfo_exists():
            chars=["/","-","\\","|"]; char=chars[char_index % len(chars)]
            if self.generating_window_label: self.generating_window_label.configure(text=char)
            self.generating_animation_job = self.root.after(150, lambda: self._animate_green_dot(char_index + 1))
        else: self.generating_animation_job = None

    def destroy_generating_window(self): # Internal UI method (corrected)
        if self.generating_animation_job:
            try:
                if hasattr(self, 'root') and self.root.winfo_exists(): self.root.after_cancel(self.generating_animation_job)
            except: pass
            self.generating_animation_job=None
        if self.generating_window:
            try: self.generating_window.destroy()
            except: pass
            self.generating_window=None; self.generating_window_label=None

    def destroy_float_window(self): # Internal UI method (corrected)
        if hasattr(self, '_float_window_close_job') and self._float_window_close_job:
            try:
                if hasattr(self, 'root') and self.root.winfo_exists(): self.root.after_cancel(self._float_window_close_job)
            except: pass
            self._float_window_close_job=None
        if self.float_window:
            try: self.float_window.destroy()
            except: pass
            self.float_window=None

    def destroy_ok_window(self): # Internal UI method (corrected)
        if hasattr(self, '_ok_window_close_job') and self._ok_window_close_job:
            try:
                if hasattr(self, 'root') and self.root.winfo_exists(): self.root.after_cancel(self._ok_window_close_job)
            except: pass
            self._ok_window_close_job=None
        if self.ok_window:
            try: self.ok_window.destroy()
            except: pass
            self.ok_window=None

    def show_ok_window(self, position=None): # Internal UI method (corrected)
        self.destroy_ok_window(); self.destroy_generating_window()
        self.ok_window = tk.Toplevel(self.root); self.ok_window.overrideredirect(True)
        pos = position or self.last_mouse_pos; x, y = pos
        self.ok_window.geometry(f"50x50+{x+10}+{y+10}"); self.ok_window.attributes("-topmost", True)
        btn = ctk.CTkButton( self.ok_window, text="OK", width=50, height=50, corner_radius=25, font=ctk.CTkFont(size=20, weight="bold"), fg_color="#DC143C", hover_color="#B22222", text_color="white", command=self.destroy_ok_window )
        btn.pack(fill="both", expand=True)
        if hasattr(self, '_ok_window_close_job') and self._ok_window_close_job:
            try:
                 if hasattr(self, 'root') and self.root.winfo_exists(): self.root.after_cancel(self._ok_window_close_job)
            except: pass
            self._ok_window_close_job = None
        def auto_close():
            if self.ok_window: self.destroy_ok_window()
            self._ok_window_close_job = None
        self._ok_window_close_job = self.ok_window.after(config.MOUSE_TIP_TIMEOUT * 1000, auto_close)

    def trigger_generate_from_float(self):
        text = getattr(self, '_text_for_float_trigger', None)
        if not text: print(self._("debug_no_float_text")); self.destroy_float_window(); return
        print(self._("debug_float_trigger_text", text[:50]))
        voice = self.current_full_voice_name
        if not voice: self.update_status("status_no_voice_error", error=True, duration=5); self.destroy_float_window(); return
        rate=f"{self.rate_slider_var.get():+}%"; volume=f"{self.volume_slider_var.get():+}%"; pitch="+0Hz"
        pos = self.last_mouse_pos; self.destroy_float_window(); self.show_generating_window(pos)
        def on_complete(path, error=None):
            self.destroy_generating_window()
            copy=self.copy_to_clipboard_var.get(); play=self.play_audio_var.get()
            if path:
                print(self._("debug_audio_complete", path)); print(self._("debug_autoplay_float", play)); print(self._("debug_autocopy_float", copy))
                if play: self.play_audio_pygame(path)
                if copy: utils.copy_file_to_clipboard(path, app_instance=self); self.show_ok_window(pos)
            else: err = f"{self._('status_generate_error')}: {error or '??'}"; print(err); self.update_status(err, error=True)
            utils.manage_audio_files(app_instance=self)
        tts_utils.generate_audio(text, voice, rate, volume, pitch, on_complete, app_instance=self)

    # --------------------------------------------------------------------------
    # 剪贴板与鼠标监控方法 (Delegated to monitor module)
    # --------------------------------------------------------------------------
    def toggle_select_to_audio(self):
        """Toggles the master switch for clipboard/selection monitoring."""
        if self.select_to_audio_var.get():
             # Pass self (app instance) and the callback method
             monitor.start_monitoring(app_ref=self, trigger_callback=self._trigger_float_from_poll)
        else:
             monitor.stop_monitoring()
        self.save_settings()

    def start_clipboard_monitor(self):
        """Starts the monitoring services via the monitor module."""
        monitor.start_monitoring(app_ref=self, trigger_callback=self._trigger_float_from_poll)

    def stop_clipboard_monitor(self):
        """Stops the monitoring services via the monitor module."""
        monitor.stop_monitoring()

    def _trigger_float_from_poll(self, text_to_show):
        """Callback run in main thread by monitor to show float window."""
        # Check the flag from config module now
        if not config.clipboard_monitor_active or not self.root.winfo_exists(): return
        try:
            self.last_mouse_pos = (self.root.winfo_pointerx(), self.root.winfo_pointery())
            print(self._("debug_poll_mouse_pos", self.last_mouse_pos))
            self.show_float_window(text_to_show) # Show the blue dot
        except Exception as e:
            print(self._("debug_poll_trigger_error", e))

    # --------------------------------------------------------------------------
    # 窗口关闭处理 (使用 monitor 模块)
    # --------------------------------------------------------------------------
    def on_closing(self):
        """Handles window closing event."""
        print(self._("debug_closing"))
        monitor.stop_monitoring() # Use monitor module function
        self.save_settings()
        # Stop pygame
        try:
            if pygame.mixer.get_init(): print(self._("debug_pygame_stop_mixer")); pygame.mixer.music.stop(); pygame.mixer.quit()
            if pygame.get_init(): print(self._("debug_pygame_quit")); pygame.quit()
        except Exception as e: print(self._("debug_pygame_close_error", e))
        # Destroy Tkinter
        try:
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    try: widget.destroy()
                    except: pass # Ignore errors during cleanup
            self.root.destroy()
        except tk.TclError as e: print(self._("debug_destroy_error", e))
        except Exception as e: print(f"Unexpected error during closing: {e}")