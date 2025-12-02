import json
import os
import time
from config.constants import HISTORY_FILE
from config.settings import settings_manager

class HistoryManager:
    def __init__(self):
        self.history_file = HISTORY_FILE
        self.records = []
        self.load_records()

    def load_records(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
            except Exception as e:
                print(f"Failed to load history: {e}")
                self.records = []
        else:
            self.records = []

    def save_records(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Failed to save history: {e}")

    def add_record(self, text, voice, path):
        """
        Add a new record to the history.
        Removes oldest records if count exceeds max_audio_files.
        """
        record = {
            "text": text,
            "voice": voice,
            "path": path,
            "timestamp": time.time()
        }
        
        # Insert at the beginning (newest first)
        self.records.insert(0, record)
        
        # Enforce limit
        max_files = settings_manager.get("max_audio_files", 20)
        if len(self.records) > max_files:
            self.records = self.records[:max_files]
            
        self.save_records()

    def get_records(self):
        return self.records

    def clear_records(self):
        self.records = []
        self.save_records()

history_manager = HistoryManager()