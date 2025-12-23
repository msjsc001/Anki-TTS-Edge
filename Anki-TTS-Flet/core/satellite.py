import tkinter as tk
import multiprocessing
import queue
import time
import sys
import ctypes

# Fix High DPI on Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

class SatelliteWindow:
    def __init__(self, input_queue: multiprocessing.Queue, output_queue: multiprocessing.Queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
        
        self.root = tk.Tk()
        
        # Window Configuration
        self.root.overrideredirect(True) # Frameless
        self.root.attributes('-topmost', True) # Always on top
        self.root.attributes('-transparentcolor', 'black') # Transparency Key
        self.root.config(bg='black') # Background to be transparent
        
        # Initial Dimensions (Single Mode)
        self.width = 80
        self.height = 80
        
        # Canvas
        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height, bg='black', highlightthickness=0)
        self.canvas.pack()
        
        # Items (Created dynamically or toggled)
        self.is_dual = False
        
        # Single Dot (Center)
        self.circle_main = self.canvas.create_oval(10, 10, 70, 70, fill='#2196F3', outline='', tags="single") 
        self.text_main = self.canvas.create_text(40, 40, text="Go", fill="white", font=("Arial", 12, "bold"), tags="single")
        
        # Dual Dots (Left A, Right B) - Initially Hidden
        self.circle_a = self.canvas.create_oval(5, 10, 65, 70, fill='#3F51B5', outline='', state='hidden', tags="dual") # Indigo (History)
        self.text_a = self.canvas.create_text(35, 40, text="A", fill="white", font=("Arial", 12, "bold"), state='hidden', tags="dual")
        
        self.circle_b = self.canvas.create_oval(75, 10, 135, 70, fill='#009688', outline='', state='hidden', tags="dual") # Teal (Latest)
        self.text_b = self.canvas.create_text(105, 40, text="B", fill="white", font=("Arial", 12, "bold"), state='hidden', tags="dual")
        
        # Drag Logic
        self.canvas.bind('<ButtonPress-1>', self.start_move)
        self.canvas.bind('<B1-Motion>', self.do_move)
        
        # Click Logic
        self.canvas.bind('<ButtonRelease-1>', self.on_click)
        self.canvas.bind('<Double-Button-1>', self.on_double_click)
        
        # Timers
        self.idle_timer = None
        
        # Initial Hide
        self.root.withdraw()
        
        # Polling Loop
        self.current_text = ""
        self.root.after(50, self.check_queue)
        
    def start_move(self, event):
        self.x = event.x
        self.y = event.y
        self._cancel_idle_timer()

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def on_click(self, event):
        if hasattr(self, 'x') and abs(event.x - self.x) < 5 and abs(event.y - self.y) < 5:
            self._cancel_idle_timer()
            
            mode = "B" # Default (Single/Main)
            
            if self.is_dual:
                # Determine click side
                if event.x < 70:
                    mode = "A"
                    self.canvas.itemconfig(self.circle_a, fill='#4CAF50') # Green
                else:
                    mode = "B"
                    self.canvas.itemconfig(self.circle_b, fill='#4CAF50') # Green
            else:
                self.canvas.itemconfig(self.circle_main, fill='#4CAF50') # Green
                
            print(f"Satellite: Clicked Mode {mode}! Sending ACTION")
            self.output_queue.put(("ACTION", self.current_text, mode))

    def on_double_click(self, event):
        self.output_queue.put(("RESTORE",))

    def _start_idle_timer(self):
        self._cancel_idle_timer()
        self.idle_timer = self.root.after(3000, self._auto_hide)

    def _cancel_idle_timer(self):
        if self.idle_timer:
            self.root.after_cancel(self.idle_timer)
            self.idle_timer = None

    def _auto_hide(self):
        print("Satellite: Auto-hiding due to inactivity")
        self.root.withdraw()

    def set_mode(self, is_dual):
        if self.is_dual == is_dual:
            return
            
        self.is_dual = is_dual
        if is_dual:
            self.width = 140
            self.canvas.config(width=140)
            self.canvas.itemconfigure("single", state='hidden')
            self.canvas.itemconfigure("dual", state='normal')
        else:
            self.width = 80
            self.canvas.config(width=80)
            self.canvas.itemconfigure("single", state='normal')
            self.canvas.itemconfigure("dual", state='hidden')

    def check_queue(self):
        try:
            while True:
                cmd, *args = self.input_queue.get_nowait()
                if cmd == "SHOW":
                    # args: text, x, y, [is_dual]
                    if len(args) == 4:
                        text, x, y, is_dual = args
                    else:
                        text, x, y = args
                        is_dual = False
                        
                    self.current_text = text
                    
                    self.set_mode(is_dual)
                    self.root.geometry(f"{self.width}x{self.height}+{int(x)}+{int(y)}")
                    self.root.deiconify()
                    
                    # Reset Colors
                    self.canvas.itemconfig(self.circle_main, fill='#2196F3')
                    self.canvas.itemconfig(self.circle_a, fill='#3F51B5')
                    self.canvas.itemconfig(self.circle_b, fill='#009688')
                    
                    self._start_idle_timer()
                    
                elif cmd == "HIDE":
                    self.root.withdraw()
                
                elif cmd == "UPDATE_TEXT":
                    # Update current_text without changing position/visibility
                    if args:
                        self.current_text = args[0]
                    
                elif cmd == "STATE":
                    state_type = args[0]
                    # Since Main doesn't know WHICH dot caused generating (yet), we might need to handle this.
                    # Or Main sends ("STATE", "generating", "A")?
                    # For now, let's assume Main sends global state, we update BOTH or based on last click?
                    # Simpler: visual feedback update handled by Main?
                    # Or just greenify active?
                    
                    # Actually, we handled 'Generating' (Green) in on_click instantly for responsiveness.
                    # Main sends 'success' or 'error'.
                    
                    if state_type == "success":
                        # Turn everything Red? Or just active?
                        # Since we don't track active here easily without adding state,
                        # Let's flash all visible RED.
                        color = '#F44336' # Red
                        if self.is_dual:
                            self.canvas.itemconfig(self.circle_a, fill=color)
                            self.canvas.itemconfig(self.circle_b, fill=color)
                        else:
                            self.canvas.itemconfig(self.circle_main, fill=color)
                        
                        self.root.after(1000, self._reset_state)
                        
                    elif state_type == "error":
                        color = '#FF9800' # Orange
                        if self.is_dual:
                            self.canvas.itemconfig(self.circle_a, fill=color)
                            self.canvas.itemconfig(self.circle_b, fill=color)
                        else:
                            self.canvas.itemconfig(self.circle_main, fill=color)
                        self.root.after(2000, lambda: self.root.withdraw())
                        
                elif cmd == "EXIT":
                    self.root.destroy()
                    return
        except queue.Empty:
            pass
        self.root.after(50, self.check_queue)
        
    def _reset_state(self):
        self.canvas.itemconfig(self.circle_main, fill='#2196F3')
        self.canvas.itemconfig(self.circle_a, fill='#3F51B5')
        self.canvas.itemconfig(self.circle_b, fill='#009688')
        self._start_idle_timer()
    
    def run(self):
        self.root.mainloop()

def run_satellite(input_q, output_q):
    app = SatelliteWindow(input_q, output_q)
    app.run()

if __name__ == "__main__":
    # Test mode
    iq = multiprocessing.Queue()
    oq = multiprocessing.Queue()
    p = multiprocessing.Process(target=run_satellite, args=(iq, oq))
    p.start()
    time.sleep(2)
    iq.put(("SHOW", "Hello World", 500, 500))
    # Test Auto Hide
    # time.sleep(2) 
    # iq.put(("SHOW", "Again", 600, 600))
    # iq.put(("STATE", "generating"))
    # time.sleep(1)
    # iq.put(("STATE", "success"))
    time.sleep(5)
    iq.put(("EXIT",))
