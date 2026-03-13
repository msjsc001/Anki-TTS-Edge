import flet as ft
from datetime import datetime
from utils.i18n import i18n
from core.voices import get_display_voice_name

class HistoryView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self._host_page = page
        self.expand = True
        self.padding = 20

        self.header_text = ft.Text(i18n.get("history_panel_title"), size=24, weight="bold")
        self.clear_all_button = ft.TextButton(
            text=i18n.get("history_clear_all"),
            icon=ft.Icons.DELETE_SWEEP,
            style=ft.ButtonStyle(color=ft.Colors.RED_400),
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
                ft.TextButton(text=i18n.get("dialog_cancel", "Cancel"), on_click=self._close_dialog),
                ft.TextButton(text=i18n.get("dialog_confirm", "Yes"), on_click=self._confirm_clear),
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

    def _is_mounted(self):
        return getattr(self, "page", None) is not None

    def _safe_update(self):
        if self._is_mounted():
            try:
                self.update()
            except Exception as ex:
                print(f"DEBUG: HistoryView safe update skipped: {ex}")
        
    def populate_history(self, records):
        self.history_list.controls.clear()
        
        if not records:
            self.history_list.controls.append(ft.Text(i18n.get("history_empty"), italic=True))
            self._safe_update()
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

            action_buttons = ft.Row(
                [
                    ft.TextButton(
                        text=i18n.get("control_play_pause", "播放"),
                        icon=ft.Icons.PLAY_ARROW,
                        on_click=lambda e, r=rec: self._play_audio(r),
                    ),
                    ft.TextButton(
                        text=i18n.get("history_rec_delete", "删除"),
                        icon=ft.Icons.DELETE,
                        style=ft.ButtonStyle(color=ft.Colors.RED_400),
                        on_click=lambda e, r=rec: self._delete_item(r),
                    ),
                ],
                spacing=0,
                tight=True,
            )

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
                        action_buttons,
                    ],
                ),
                padding=10,
                bgcolor="surfaceVariant",
                border_radius=10,
            )
            self.history_list.controls.append(tile)
            
        self._safe_update()

    def _play_audio(self, record):
        print(f"DEBUG: History play clicked -> {record.get('path') if isinstance(record, dict) else record}")
        if hasattr(self, 'on_play_audio'):
            self.on_play_audio(record)

    def _delete_item(self, record):
        print(f"DEBUG: History delete clicked -> {record.get('path') if isinstance(record, dict) else record}")
        if hasattr(self, 'on_delete_item'):
            self.on_delete_item(record)

    def _open_dialog(self, dialog):
        if hasattr(self._host_page, "open"):
            self._host_page.open(dialog)
            return
        self._host_page.dialog = dialog
        dialog.open = True
        self._host_page.update()

    def _close_host_dialog(self, dialog):
        if hasattr(self._host_page, "close"):
            self._host_page.close(dialog)
            return
        dialog.open = False
        self._host_page.update()
        if getattr(self._host_page, "dialog", None) is dialog:
            self._host_page.dialog = None

    def _on_clear_all(self, e):
        print("DEBUG: Opening Clear All Dialog")
        self._open_dialog(self.confirm_dialog)

    def _close_dialog(self, e):
        self._close_host_dialog(self.confirm_dialog)

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
        self.clear_all_button.text = i18n.get("history_clear_all")
        self.confirm_dialog.title.value = i18n.get("history_clear_confirm_title", "Confirm Clear")
        self.confirm_dialog.content.value = i18n.get("history_clear_confirm_msg", "Delete all history?")
        self.confirm_dialog.actions[0].text = i18n.get("dialog_cancel", "Cancel")
        self.confirm_dialog.actions[1].text = i18n.get("dialog_confirm", "Yes")
        self._safe_update()

    def _format_timestamp(self, value):
        if not value:
            return ""

        try:
            return datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError, OSError):
            return str(value)
