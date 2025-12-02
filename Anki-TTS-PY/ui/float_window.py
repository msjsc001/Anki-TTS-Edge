import tkinter as tk
import customtkinter as ctk
from config.constants import FLOAT_WINDOW_TIMEOUT, MOUSE_TIP_TIMEOUT

class FloatWindowManager:
    def __init__(self, root, on_generate_callback):
        self.root = root
        self.on_generate = on_generate_callback
        
        self.float_window = None
        self.ok_window = None
        self.generating_window = None
        self.generating_window_label = None
        self.generating_animation_job = None
        
        self._float_close_job = None
        self._ok_close_job = None

    def destroy_all(self):
        self.destroy_float_window()
        self.destroy_generating_window()
        self.destroy_ok_window()

    def destroy_float_window(self):
        if self._float_close_job:
            try: self.root.after_cancel(self._float_close_job)
            except: pass
            self._float_close_job = None
            
        if self.float_window:
            try: 
                if self.float_window.winfo_exists():
                    self.float_window.destroy()
            except: pass
            self.float_window = None

    def destroy_generating_window(self):
        if self.generating_animation_job:
            try: self.root.after_cancel(self.generating_animation_job)
            except: pass
            self.generating_animation_job = None
            
        if self.generating_window:
            try: self.generating_window.destroy()
            except: pass
            self.generating_window = None
            self.generating_window_label = None

    def destroy_ok_window(self):
        if self._ok_close_job:
            try: self.root.after_cancel(self._ok_close_job)
            except: pass
            self._ok_close_job = None
            
        if self.ok_window:
            try: self.ok_window.destroy()
            except: pass
            self.ok_window = None

    def show_single_float(self, pos, text_data=None):
        self.destroy_all()
        x, y = pos
        size = 50
        
        self.float_window = tk.Toplevel(self.root)
        self.float_window.overrideredirect(True)
        self.float_window.geometry(f"{size}x{size}+{x+10}+{y+10}")
        self.float_window.attributes("-topmost", True)
        
        btn = ctk.CTkButton(
            self.float_window, text="音", width=size, height=size, 
            corner_radius=size//2, font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="#1E90FF", hover_color="#1C86EE", text_color="white",
            command=lambda: self._on_click('latest', text_data)
        )
        btn.pack(fill="both", expand=True)
        
        self._schedule_close(FLOAT_WINDOW_TIMEOUT)

    def show_dual_float(self, pos, text_data=None):
        self.destroy_all()
        x, y = pos
        size = 50
        gap = 4
        width = size * 2 + gap
        
        self.float_window = tk.Toplevel(self.root)
        self.float_window.overrideredirect(True)
        self.float_window.geometry(f"{width}x{size}+{x+10}+{y+10}")
        self.float_window.attributes("-topmost", True)
        
        try:
            self.float_window.configure(fg_color="transparent")
        except: pass
        
        # Grid config
        self.float_window.grid_columnconfigure(0, weight=1)
        self.float_window.grid_columnconfigure(1, weight=1)
        self.float_window.grid_rowconfigure(0, weight=1)

        # Left (A)
        self._create_dual_btn(0, "A", lambda: self._on_click('previous', text_data), size, gap)
        # Right (B)
        self._create_dual_btn(1, "B", lambda: self._on_click('latest', text_data), size, gap)
        
        self._schedule_close(FLOAT_WINDOW_TIMEOUT)

    def _create_dual_btn(self, col, text, command, size, gap):
        frame = ctk.CTkFrame(
            self.float_window, width=size, height=size, corner_radius=size//2,
            fg_color="#1E90FF", border_width=0
        )
        padx = (0, gap//2) if col == 0 else (gap//2, 0)
        frame.grid(row=0, column=col, padx=padx, pady=0, sticky="ns")
        frame.grid_propagate(False)
        
        label = ctk.CTkLabel(
            frame, text=text, text_color="white",
            font=ctk.CTkFont(size=16, weight="bold"), fg_color="transparent"
        )
        label.place(relx=0.5, rely=0.5, anchor="center")
        
        frame.bind("<Button-1>", lambda e: command())
        label.bind("<Button-1>", lambda e: command())

    def show_generating(self, pos):
        self.destroy_all()
        x, y = pos
        
        self.generating_window = tk.Toplevel(self.root)
        self.generating_window.overrideredirect(True)
        self.generating_window.geometry(f"50x50+{x+10}+{y+10}")
        self.generating_window.attributes("-topmost", True)
        
        self.generating_window_label = ctk.CTkButton(
            self.generating_window, text="/", width=50, height=50,
            corner_radius=25, font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="#4CAF50", text_color="white", state="disabled"
        )
        self.generating_window_label.pack(fill="both", expand=True)
        self._animate_green_dot()

    def show_ok(self, pos):
        self.destroy_all()
        x, y = pos
        
        self.ok_window = tk.Toplevel(self.root)
        self.ok_window.overrideredirect(True)
        self.ok_window.geometry(f"50x50+{x+10}+{y+10}")
        self.ok_window.attributes("-topmost", True)
        
        btn = ctk.CTkButton(
            self.ok_window, text="OK", width=50, height=50,
            corner_radius=25, font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="#DC143C", hover_color="#B22222", text_color="white",
            command=self.destroy_ok_window
        )
        btn.pack(fill="both", expand=True)
        
        self._ok_close_job = self.ok_window.after(int(MOUSE_TIP_TIMEOUT * 1000), self.destroy_ok_window)

    def _on_click(self, voice_type, text_data):
        self.destroy_float_window()
        if self.on_generate:
            self.on_generate(voice_type, text_data)

    def _schedule_close(self, timeout):
        if self.float_window:
            self._float_close_job = self.float_window.after(
                int(timeout * 1000), self.destroy_float_window
            )

    def _animate_green_dot(self, char_index=0):
        if self.generating_window and self.generating_window.winfo_exists():
            chars = ["/", "-", "\\", "|"]
            char = chars[char_index % len(chars)]
            if self.generating_window_label:
                self.generating_window_label.configure(text=char)
            self.generating_animation_job = self.root.after(
                150, lambda: self._animate_green_dot(char_index + 1)
            )