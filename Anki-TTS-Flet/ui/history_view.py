import flet as ft
from utils.i18n import i18n
import os

class HistoryView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.expand = True
        self.padding = 20
        
        # Header
        self.header = ft.Row(
            [
                ft.Text(i18n.get("history_panel_title"), size=24, weight="bold"),
                ft.IconButton(
                    icon=ft.Icons.DELETE_SWEEP, 
                    icon_color=ft.Colors.RED_400,
                    tooltip=i18n.get("history_clear_all"),
                    on_click=self._on_clear_all
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        # Dialog
        self.confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(i18n.get("history_clear_confirm_title", "Confirm Clear")),
            content=ft.Text(i18n.get("history_clear_confirm_msg", "Delete all history?")),
            actions=[
                ft.TextButton("Cancel", on_click=self._close_dialog),
                ft.TextButton("Yes", on_click=self._confirm_clear),
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
            
            tile = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.AUDIO_FILE, color=ft.Colors.INDIGO),
                        ft.Column(
                            [
                                ft.Text(text_preview, weight="bold", size=14),
                                ft.Text(f"{rec.get('voice_key')} | {rec.get('time')}", size=12, color=ft.Colors.OUTLINE),
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
