# Anki-TTS-Edge

**[中文文档](https://github.com/msjsc001/Anki-TTS-Edge/blob/master/README.md)**

<div align="center">

Anki-TTS-Edge is a free, high-quality voice generation tool powered by Microsoft Edge TTS. It **quickly generates audio from selected text**, supports dual-voice mode for generating audio with two different voices, and automatically copies the generated audio to clipboard for fast pasting into apps like Anki. It also serves as a **convenient reading tool for language learning and article reading**.
**Completely rebuilt with Flet (Flutter) in v2.0**, featuring a modern UI, smooth animations, and enhanced functionality.

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/msjsc001/Anki-TTS-Edge)](https://github.com/msjsc001/Anki-TTS-Edge/releases/latest) [![GitHub last commit](https://img.shields.io/github/last-commit/msjsc001/Anki-TTS-Edge)](https://github.com/msjsc001/Anki-TTS-Edge/commits/master) [![GitHub All Releases Downloads](https://img.shields.io/github/downloads/msjsc001/Anki-TTS-Edge/total?label=Downloads&color=brightgreen)](https://github.com/msjsc001/Anki-TTS-Edge/releases)

</div>

## ✨ Key Features

- **Modern UI**: Rebuilt from scratch using Flet (Flutter) for a sleek, responsive, and material design experience.
- **Top-tier Voices**: Access 300+ free Microsoft Edge Neural voices across multiple languages and regions.
- **Dual Voice Mode**: "Dual Blue Dot" system allows quick switching or sequential generation of two different voices (e.g., Male/Female, US/UK accents).
- **History Management**: Automatically saves generation history. Re-listen, copy, or delete audio records easily.
- **Smart Monitoring**: 
  - **Clipboard Monitor**: Automatically captures copied text and pops up for instant generation.
  - **Selection Monitor**: (Windows only) Genereate audio instantly by selecting text.
- **System Integration**:
  - **Tray Support**: Minimize to system tray to keep your workspace clean.
  - **Pin to Top**: Keep the window always on top for easy access while studying.
- **Internationalization**: Full support for English and Chinese (Simplified) interfaces with real-time switching.

## 📸 Screenshots

<div align="center">
  <img src="https://github.com/user-attachments/assets/placeholder-home" alt="Home View" width="300" />
  <img src="https://github.com/user-attachments/assets/placeholder-setting" alt="Settings View" width="300" />
</div>

> *Note: New Flet interface, clean and intuitive.*

## 🚀 Installation & Running

### Requirements
- Python 3.8+
- Windows (Recommended for full feature support like Selection Monitor)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/msjsc001/Anki-TTS-Edge.git
   cd Anki-TTS-Edge
   ```

2. **Install Dependencies**
   ```bash
   pip install -r Anki-TTS-Flet/requirements.txt
   ```
   *Note: If `requirements.txt` is missing, manually install:*
   ```bash
   pip install flet edge-tts pygame pyperclip pystray pillow
   ```

3. **Run Application**
   ```bash
   python Anki-TTS-Flet/main.py
   ```

### Build EXE (Optional)

To build a standalone executable:

```bash
# Install PyInstaller in virtual environment
pip install pyinstaller

# Build command
.\.venv\Scripts\python.exe -m PyInstaller Anki-TTS-Flet/main.py --name "Anki-TTS-Edge" --icon "Anki-TTS-Flet/assets/icon.ico" --add-data "Anki-TTS-Flet/assets;assets" --collect-all edge_tts --hidden-import=pystray --hidden-import=PIL --hidden-import=pygame --noconsole --onefile --clean --noconfirm
```

The generated `Anki-TTS-Edge.exe` will be in the `dist/` directory.

## 📂 Project Structure

```text
Anki-TTS-Edge/
├── Anki-TTS-Flet/       # Main compiled source code
│   ├── assets/          # Icons and translation files
│   ├── config/          # Configuration and settings
│   ├── core/            # Business logic (TTS, Clipboard, History)
│   ├── ui/              # Flet UI Views (Home, History, Settings)
│   ├── utils/           # Helpers
│   └── main.py          # Entry point
├── .gitignore           # Git ignore rules
└── README.md            # Documentation
```

## 🛠️ Usage Guide

1. **Select Voice**: Use the dropdown menus to filter by Language and Region.
2. **Generate**: Type or paste text, then click the **Blue Dot** to generate audio.
   - **Left Dot**: Uses "Language (Left)" settings.
   - **Right Dot**: Uses "Language (Right)" settings.
3. **Copy File**: After generation (Green -> Red dot), click the Red dot or use **Ctrl+C** to copy the audio file path (for pasting into Anki).
4. **History**: Switch to the **History** tab to view and manage past generations.
5. **Settings**: Customize theme (Dark/Light), behavior (Autoplay, Tray), and more in the **Settings** tab.

---
<div align="center">
Made with ❤️ for Language Learners
</div>