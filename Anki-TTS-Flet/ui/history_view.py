import flet as ft
from datetime import datetime
from utils.i18n import i18n
from core.voices import get_display_voice_name

class HistoryView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.expand = True
        self.padding = 20

        self.header_text = ft.Text(i18n.get("history_panel_title"), size=24, weight="bold")
        self.clear_all_button = ft.IconButton(
            icon=ft.Icons.DELETE_SWEEP,
            icon_color=ft.Colors.RED_400,
            tooltip=i18n.get("history_clear_all"),
            on_click=self._on_clear_all
        )
        
        # Header
        self.header = ft.Row(
            [
                self.header_text,
                self.clear_all_button,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        # Dialog
        self.confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(i18n.get("history_clear_confirm_title", "Confirm Clear")),
            content=ft.Text(i18n.get("history_clear_confirm_msg", "Delete all history?")),
            actions=[
                ft.TextButton(i18n.get("dialog_cancel", "Cancel"), on_click=self._close_dialog),
                ft.TextButton(i18n.get("dialog_confirm", "Yes"), on_click=self._confirm_clear),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # List
        self.history_list = ft.ListView(expand=True, spacing=10)
        
        self.content = ft.Column(
            expand=True,
            alignment=ft.MainAxisAlignment.START,
            controls=[
                self.header,
                ft.Divider(),
                self.history_list
            ]
        )
        
    def populate_history(self, records):
        self.history_list.controls.clear()
        
        if not records:
            self.history_list.controls.append(ft.Text(i18n.get("history_empty"), italic=True))
            self.update()
            return

        for rec in records:
            # Create dismissible (swipe to delete) or just list tile with action
            # Flet's Dismissible is great for mobile, but for desktop explicit button is better.
            
            text_preview = rec.get("text", "")
            if len(text_preview) > 50: text_preview = text_preview[:50] + "..."
            
            voice_text = get_display_voice_name(rec.get("voice") or rec.get("voice_key"))
            timestamp_text = self._format_timestamp(rec.get("timestamp") or rec.get("time"))
            meta_parts = [part for part in [voice_text, timestamp_text] if part]
            meta_text = " | ".join(meta_parts) if meta_parts else "-"

            tile = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.AUDIO_FILE, color=ft.Colors.INDIGO),
                        ft.Column(
                            [
                                ft.Text(text_preview, weight="bold", size=14),
                                ft.Text(meta_text, size=12, color=ft.Colors.OUTLINE),
                            ],
                            expand=True,
                            spacing=2
                        ),
                        ft.IconButton(ft.Icons.PLAY_ARROW, on_click=lambda e, r=rec: self._play_audio(r)),
                        ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=lambda e, r=rec: self._delete_item(r)),
                    ],
                ),
                padding=10,
                bgcolor="surfaceVariant",
                border_radius=10,
                on_click=lambda e, r=rec: self._on_item_click(r),
                ink=True, # Ripple effect
            )
            self.history_list.controls.append(tile)
            
        self.update()

    def _play_audio(self, record):
        if hasattr(self, 'on_play_audio'):
            self.on_play_audio(record)

    def _delete_item(self, record):
        if hasattr(self, 'on_delete_item'):
            self.on_delete_item(record)

    def _on_clear_all(self, e):
        print("DEBUG: Opening Clear All Dialog (Overlay Mode)")
        self.page.overlay.append(self.confirm_dialog)
        self.confirm_dialog.open = True
        self.page.update()

    def _close_dialog(self, e):
        self.confirm_dialog.open = False
        self.page.update()
        # Cleanup (Optional, but good practice)
        # self.page.overlay.remove(self.confirm_dialog)

    def _confirm_clear(self, e):
        print("DEBUG: User confirmed Clear All")
        self._close_dialog(e)
        if hasattr(self, 'on_clear_all'):
            print("DEBUG: Calling on_clear_all callback")
            self.on_clear_all()
        else:
            print("ERROR: No on_clear_all callback bound")

    def _on_item_click(self, record):
        if hasattr(self, 'on_click_record'):
            self.on_click_record(record)

    def refresh_texts(self):
        self.header_text.value = i18n.get("history_panel_title")
        self.clear_all_button.tooltip = i18n.get("history_clear_all")
        self.confirm_dialog.title.value = i18n.get("history_clear_confirm_title", "Confirm Clear")
        self.confirm_dialog.content.value = i18n.get("history_clear_confirm_msg", "Delete all history?")
        self.confirm_dialog.actions[0].text = i18n.get("dialog_cancel", "Cancel")
        self.confirm_dialog.actions[1].text = i18n.get("dialog_confirm", "Yes")
        self.update()

    def _format_timestamp(self, value):
        if not value:
            return ""

        try:
            return datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError, OSError):
            return str(value)
