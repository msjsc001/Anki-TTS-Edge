import flet as ft
from utils.i18n import i18n
from config.constants import APP_VERSION, GITHUB_URL, DATA_DIR
import webbrowser
import os

class SettingsView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.expand = True
        self.padding = 20
        
        # Header
        self.header = ft.Text(i18n.get("tab_settings"), size=24, weight="bold")
        
        # Components
        # 1. Appearance
        self.theme_switch = ft.Switch(
            label=i18n.get("theme_label", "Dark Mode"),
            value=False,
            on_change=self._on_theme_changed
        )
        
        self.language_dropdown = ft.Dropdown(
            value=i18n.current_language,
            options=[
                ft.dropdown.Option("zh", "中文"),
                ft.dropdown.Option("en", "English"),
            ],
            width=120,
            on_change=self._on_language_change,
        )
        
        # 2. Behavior
        self.autoplay_switch = ft.Switch(
            label=i18n.get("settings_autoplay_label"),
            value=True,
            on_change=self._save_settings
        )

        self.ctrl_c_switch = ft.Switch(
            label=i18n.get("settings_enable_clipboard_monitor_label", i18n.get("settings_enable_ctrl_c_label")),
            value=True,
            on_change=self._save_settings
        )

        self.selection_switch = ft.Switch(
            label=i18n.get("settings_enable_selection_label"),
            value=False,
            on_change=self._on_selection_change
        )
        
        self.dual_mode_switch = ft.Switch(
            label=i18n.get("settings_dual_blue_dot_label"),
            value=False,
            disabled=True, # Disabled by default until selection enabled
            on_change=self._save_settings
        )

        self.copy_file_switch = ft.Switch(
            label=i18n.get("copy_audio_to_clipboard"), 
            value=True,
            on_change=self._save_settings
        )

        self.tray_switch = ft.Switch(
             label=i18n.get("settings_minimize_to_tray_label", "Minimize to Tray"),
             value=False,
             on_change=self._save_settings
        )
        
        # Window Size Controls
        self.window_width_input = ft.TextField(
            label="",
            hint_text="750",
            value="750",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=100,
            on_blur=self._on_window_size_changed
        )
        
        self.window_height_input = ft.TextField(
            label="",
            hint_text="850",
            value="850",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=100,
            on_blur=self._on_window_size_changed
        )
        
        self.reset_size_button = ft.OutlinedButton(
            text=i18n.get("reset_button"),
            icon=ft.Icons.RESTORE,
            on_click=self._reset_window_size
        )
        
        self.max_files_input = ft.TextField(
            label=i18n.get("settings_max_files_label"),
            value="20",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=200,
            on_blur=self._save_settings
        )
        
        self.open_data_dir_button = ft.OutlinedButton(
            text=i18n.get("open_data_dir", "Open Data Directory"),
            icon=ft.Icons.FOLDER_OPEN,
            on_click=lambda _: os.startfile(DATA_DIR) if os.name == 'nt' else None
        )
        
        # Section headers as instance variables for dynamic language update
        self.section_appearance_text = ft.Text(i18n.get("section_appearance"), weight="bold", size=16)
        self.language_label_text = ft.Text(i18n.get("language_label"), size=14)
        self.section_behavior_text = ft.Text(i18n.get("section_behavior"), weight="bold", size=16)
        self.clipboard_label_text = ft.Text(i18n.get("settings_clipboard_label"), size=14, color="grey")
        self.section_window_text = ft.Text(i18n.get("section_window"), weight="bold", size=16)
        self.window_size_label_text = ft.Text(i18n.get("window_size_label"), size=14, color="grey")
        self.section_storage_text = ft.Text(i18n.get("section_storage"), weight="bold", size=16)
        self.check_updates_button = ft.OutlinedButton(
            text=i18n.get("check_for_updates"),
            icon=ft.Icons.OPEN_IN_NEW,
            on_click=lambda _: webbrowser.open(GITHUB_URL)
        )
        
        self.content = ft.Column(
            [
                self.header,
                ft.Divider(),
                
                self.section_appearance_text,
                self.theme_switch,
                ft.Row([
                    self.language_label_text,
                    self.language_dropdown
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=10, color="transparent"),
                
                self.section_behavior_text,
                self.autoplay_switch,
                self.clipboard_label_text,
                ft.Row(
                    [
                        self.selection_switch,
                        self.ctrl_c_switch,
                        self.dual_mode_switch
                    ],
                    spacing=20
                ),
                self.copy_file_switch,
                ft.Divider(height=10, color="transparent"),
                
                self.section_window_text,
                self.tray_switch,
                self.window_size_label_text,
                ft.Row(
                    [
                        self.window_width_input,
                        ft.Text("×", size=20),
                        self.window_height_input,
                        self.reset_size_button
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10
                ),
                ft.Divider(height=10, color="transparent"),
                
                self.section_storage_text,
                ft.Row([
                    self.max_files_input,
                    self.open_data_dir_button
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                
                ft.Divider(),
                self.check_updates_button,
                ft.Text(f"Version {APP_VERSION}", size=12, color="grey", text_align=ft.TextAlign.CENTER)
            ],
            scroll=ft.ScrollMode.AUTO
        )

    def _on_theme_changed(self, e):
        self.page.theme_mode = ft.ThemeMode.DARK if e.control.value else ft.ThemeMode.LIGHT
        self._save_settings(e)
        self.page.update()
    
    def _on_language_change(self, e):
        """Apply language change immediately and persist it."""
        new_lang = e.control.value
        print(f"DEBUG: _on_language_change triggered with: {new_lang}")
        
        i18n.set_language(new_lang)
        print(f"DEBUG: i18n language set to: {i18n.current_language}")
        
        # Save to settings
        if hasattr(self, 'on_save_settings'):
            self.on_save_settings({
                "language": new_lang
            })
            print("DEBUG: Settings saved")

        self.refresh_texts()
        if hasattr(self, "on_language_changed") and self.on_language_changed:
            self.on_language_changed(new_lang)
        self.page.update()

    def _on_selection_change(self, e):
        # Master switch controls slave switches
        is_enabled = e.control.value
        
        # Dual Mode depends on Selection
        self.dual_mode_switch.disabled = not is_enabled
        if not is_enabled:
             self.dual_mode_switch.value = False
              
        self.dual_mode_switch.update()
        # Auto-save to apply changes immediately
        self._save_settings(e)

    def _save_settings(self, e):
        if hasattr(self, 'on_save_settings'):
            # Collect current values
            settings = {
                "max_audio_files": self.max_files_input.value,
                "autoplay_enabled": self.autoplay_switch.value,
                "dual_blue_dot_enabled": self.dual_mode_switch.value,
                "monitor_clipboard_enabled": self.ctrl_c_switch.value,
                "monitor_selection_enabled": self.selection_switch.value,
                "copy_path_enabled": self.copy_file_switch.value,
                "minimize_to_tray": self.tray_switch.value,
                "appearance_mode": "dark" if self.theme_switch.value else "light"
            }
            self.on_save_settings(settings)

    def set_values(self, settings_dict):
        self.max_files_input.value = str(settings_dict.get("max_audio_files", 20))
        self.autoplay_switch.value = settings_dict.get("autoplay_enabled", True)
        
        sel_enabled = settings_dict.get("monitor_selection_enabled", False)
        self.selection_switch.value = sel_enabled
        
        self.dual_mode_switch.value = settings_dict.get("dual_blue_dot_enabled", False)
        self.dual_mode_switch.disabled = not sel_enabled
        
        self.ctrl_c_switch.value = settings_dict.get("monitor_clipboard_enabled", False)
        
        self.copy_file_switch.value = settings_dict.get("copy_path_enabled", True)
        self.tray_switch.value = settings_dict.get("minimize_to_tray", False)
        self.theme_switch.value = settings_dict.get("appearance_mode", "light") == "dark"
        
        # Window size
        self.window_width_input.value = str(settings_dict.get("window_width", 750))
        self.window_height_input.value = str(settings_dict.get("window_height", 850))
        self.update()

    def update_window_size_display(self, width, height):
        """Called from main.py when window is resized to sync the UI"""
        self.window_width_input.value = str(int(width))
        self.window_height_input.value = str(int(height))
        self.window_width_input.update()
        self.window_height_input.update()

    def _on_window_size_changed(self, e):
        """When user changes the size input fields"""
        try:
            new_width = int(self.window_width_input.value)
            new_height = int(self.window_height_input.value)
            
            # Validate minimum size
            new_width = max(400, new_width)
            new_height = max(500, new_height)
            
            if hasattr(self, 'on_window_size_change'):
                self.on_window_size_change(new_width, new_height)
        except ValueError:
            pass  # Ignore invalid input

    def _reset_window_size(self, e):
        """Reset to default 750x850"""
        self.window_width_input.value = "750"
        self.window_height_input.value = "850"
        self.window_width_input.update()
        self.window_height_input.update()
        
        if hasattr(self, 'on_window_size_change'):
            self.on_window_size_change(750, 850)

    def refresh_texts(self):
        self.header.value = i18n.get("tab_settings")
        self.theme_switch.label = i18n.get("theme_label", "Dark Mode")
        self.autoplay_switch.label = i18n.get("settings_autoplay_label")
        self.ctrl_c_switch.label = i18n.get("settings_enable_clipboard_monitor_label", i18n.get("settings_enable_ctrl_c_label"))
        self.selection_switch.label = i18n.get("settings_enable_selection_label")
        self.dual_mode_switch.label = i18n.get("settings_dual_blue_dot_label")
        self.copy_file_switch.label = i18n.get("copy_audio_to_clipboard")
        self.tray_switch.label = i18n.get("settings_minimize_to_tray_label", "Minimize to Tray")
        self.max_files_input.label = i18n.get("settings_max_files_label")
        self.reset_size_button.text = i18n.get("reset_button")
        self.open_data_dir_button.text = i18n.get("open_data_dir", "Open Data Directory")
        self.check_updates_button.text = i18n.get("check_for_updates")
        self.section_appearance_text.value = i18n.get("section_appearance")
        self.language_label_text.value = i18n.get("language_label")
        self.section_behavior_text.value = i18n.get("section_behavior")
        self.clipboard_label_text.value = i18n.get("settings_clipboard_label")
        self.section_window_text.value = i18n.get("section_window")
        self.window_size_label_text.value = i18n.get("window_size_label")
        self.section_storage_text.value = i18n.get("section_storage")
