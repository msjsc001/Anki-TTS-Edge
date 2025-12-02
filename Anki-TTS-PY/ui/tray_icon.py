import threading
from config.constants import ICON_PATH
from utils.i18n import i18n
import pystray
from PIL import Image

class TrayIconManager:
    def __init__(self, on_show_hide=None, on_exit=None):
        self.icon_instance = None
        self.tray_thread = None
        self.on_show_hide = on_show_hide
        self.on_exit = on_exit
        self.image = None
        self._setup_complete = False

    def setup(self):
        if self._setup_complete:
            return

        try:
            self.image = Image.open(ICON_PATH)
        except Exception as e:
            print(f"Error loading tray icon: {e}")
            return

        menu = (
            pystray.MenuItem(i18n.get("tray_show_hide"), self._on_show_hide_click),
            pystray.MenuItem(i18n.get("tray_exit"), self._on_exit_click)
        )

        self.icon_instance = pystray.Icon(
            "AnkiTTS",
            self.image,
            i18n.get("window_title"),
            menu=menu
        )
        self._setup_complete = True

    def start(self):
        if not self._setup_complete:
            self.setup()
        
        if self.tray_thread and self.tray_thread.is_alive():
            return

        def run_icon():
            try:
                print("Starting tray icon...")
                self.icon_instance.run()
                print("Tray icon stopped.")
            except Exception as e:
                print(f"Error running tray icon: {e}")

        self.tray_thread = threading.Thread(target=run_icon, daemon=True)
        self.tray_thread.start()

    def stop(self):
        if self.icon_instance:
            self.icon_instance.stop()

    def update_menu(self):
        if self.icon_instance:
            new_menu = (
                pystray.MenuItem(i18n.get("tray_show_hide"), self._on_show_hide_click),
                pystray.MenuItem(i18n.get("tray_exit"), self._on_exit_click)
            )
            self.icon_instance.menu = new_menu
            self.icon_instance.update_menu()
            print("托盘菜单已更新语言。")

    def _on_show_hide_click(self, icon, item):
        if self.on_show_hide:
            self.on_show_hide()

    def _on_exit_click(self, icon, item):
        if self.on_exit:
            self.on_exit()