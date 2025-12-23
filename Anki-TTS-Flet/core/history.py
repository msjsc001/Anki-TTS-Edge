import json
import os
import time
from config.constants import HISTORY_FILE, AUDIO_DIR
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
        try:
             max_files = int(settings_manager.get("max_audio_files", 20))
        except:
             max_files = 20
             
        if len(self.records) > max_files:
            self.records = self.records[:max_files]
            
        self.save_records()

    def remove_record(self, record):
        if record in self.records:
            # Delete physical file
            path = record.get("path")
            self._delete_associated_files(path)
                
            self.records.remove(record)
            self.save_records()

    def get_records(self):
        return self.records

    def clear_records(self):
        print(f"DEBUG: Clearing {len(self.records)} records...")
        count = 0
        for record in self.records:
            path = record.get("path")
            if self._delete_associated_files(path):
                count += 1
                
        print(f"DEBUG: Cleared {count} tracked audio files.")
        self.records = []
        self.save_records()
        
        # New Feature: Deep Clean Orphans
        self._deep_clean_audio_dir()

    def _deep_clean_audio_dir(self):
        """Scan AUDIO_DIR and remove all app-generated files"""
        if not os.path.exists(AUDIO_DIR): return
        
        print(f"DEBUG: Deep cleaning {AUDIO_DIR}")
        orphan_count = 0
        try:
            for filename in os.listdir(AUDIO_DIR):
                file_path = os.path.join(AUDIO_DIR, filename)
                
                # Check for files that belong to this app
                # Pattern: Anki-TTS-Edge_*.mp3
                # Pattern: *.json (careful check)
                
                is_app_file = False
                if filename.startswith("Anki-TTS-Edge_"):
                    if filename.endswith(".mp3") or filename.endswith(".json"):
                        is_app_file = True
                
                # Also clean generic timestamp files if they follow the pattern
                # [basename].timestamps.json from Anki-TTS-Edge_...
                if filename.endswith(".timestamps.json") and "Anki-TTS-Edge_" in filename:
                     is_app_file = True

                if is_app_file:
                    try:
                        os.remove(file_path)
                        orphan_count += 1
                        print(f"DEBUG: Removed orphan: {filename}")
                    except Exception as e:
                        print(f"Error removing orphan {filename}: {e}")
            
            print(f"DEBUG: Removed {orphan_count} orphaned files.")
            
        except Exception as e:
            print(f"Error during deep clean: {e}")

    def _delete_associated_files(self, path):
        """Helper to delete audio file and its metadata (timestamps)"""
        if not path: return False
        
        success = False
        # Delete Audio
        if os.path.exists(path):
            try:
                os.remove(path)
                success = True
            except Exception as e:
                print(f"Error removing audio file {path}: {e}")
        
        # Delete Timestamps if exists 
        # Pattern 1: [filename].json (Old/Standard)
        # Pattern 2: [filename].timestamps.json (New/Observed)
        
        base_path = os.path.splitext(path)[0]
        potential_json_paths = [
            base_path + ".json",
            base_path + ".timestamps.json"
        ]
        
        for json_path in potential_json_paths:
            if os.path.exists(json_path):
                 try:
                     os.remove(json_path)
                     print(f"DEBUG: Removed metadata: {json_path}")
                 except Exception as e:
                     print(f"Error removing metadata {json_path}: {e}")
                 
        return success

history_manager = HistoryManager()
