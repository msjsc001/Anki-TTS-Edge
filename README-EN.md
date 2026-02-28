# Anki-TTS-Edge

**[中文文档](https://github.com/msjsc001/Anki-TTS-Edge/blob/master/README.md)**

<div align="center">

Anki-TTS-Edge is a free, high-quality voice generation tool powered by Microsoft Edge TTS. It **quickly generates audio from selected text**, supports dual-voice mode for generating audio with two different voices, and automatically copies the generated audio to clipboard for fast pasting into apps like Anki. It also serves as a **convenient reading tool for language learning and article reading**.
**Completely rebuilt with Flet (Flutter) in v2.0**, featuring a modern UI, smooth animations, and enhanced functionality.

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/msjsc001/Anki-TTS-Edge)](https://github.com/msjsc001/Anki-TTS-Edge/releases/latest) [![GitHub last commit](https://img.shields.io/github/last-commit/msjsc001/Anki-TTS-Edge)](https://github.com/msjsc001/Anki-TTS-Edge/commits/master) [![GitHub All Releases Downloads](https://img.shields.io/github/downloads/msjsc001/Anki-TTS-Edge/total?label=Downloads&color=brightgreen)](https://github.com/msjsc001/Anki-TTS-Edge/releases)

</div>

## ✨ Key Features

- **Deep History Cleanup (v2.2)**:
  - **Smart Garbage Collection**: The "Clear All" function in History now performs a deep scan of the audio directory.
  - **Complete Storage Release**: Automatically identifies and removes all orphaned audio files (.mp3) and metadata (.json) to reclaim disk space.
- **Enhanced Reading Experience (v2.1)**:
  - **Real-time Highlight**: Words are highlighted in sync with audio playback, handling complex text mappings (e.g. "1" -> "one") perfectly.
  - **Click-to-Play**: Click on any word during playback to instantly jump to the start of that sentence.
  - **Smart Navigation**: "Previous/Next Sentence" controls allow for easy sentence-by-sentence review and navigation.
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
<img  alt="image" src="https://github.com/user-attachments/assets/c9fade87-7a3f-4ccf-858c-07c2acb6f2e2" />

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

## 👨‍💻 Developer Guide

Welcome developers to contribute and customize Anki-TTS-Edge! Below are the core architecture details and guidelines for the project.

### Technology Stack
* **UI Framework**: Flet (Python UI framework based on Flutter), providing responsive design and fluid animations.
* **Core TTS Engine**: `edge-tts` (Unofficial implementation of Microsoft Edge neural voice API).
* **Audio & Media**: `pygame` (Provides stable, low-latency multi-threaded audio playback capabilities).
* **System Integration**: `pyperclip` (Clipboard monitoring), `pystray` / `pillow` (System tray integration).
* **Asynchronous Concurrency**: Heavy usage of Python's `asyncio` for non-blocking I/O operations, ensuring the UI thread remains smooth during network requests or playback.

### Core Technical Highlights
1. **Subtitle-Level Alignment (Text-to-Speech Alignment)**
   Leverages `edge-tts` word boundaries and timestamps to dynamically update Flet's `TextSpan` and `TextStyle` within the audio playback callback, achieving "Karaoke-style" exact word synchronization.
2. **Global Input & Clipboard Monitor**
   A dedicated background thread continuously polls the system clipboard (or detects selected text). Upon detecting a change, it immediately brings the application window to the forefront (Bring to Front), eliminating cumbersome manual copy-paste steps during flashcard creation.
3. **Audio State & Garbage Collection**
   Implemented an aggressive cleanup mechanism in the history management module. It uses hashing and path tracking for audio and metadata (`.json`), and automatically iterates through local file lists during deletion to confidently discard "orphaned" files.
4. **Componentization & State Management**
   The UI is divided into independent routed views (Home, History, Settings) that communicate with low coupling via a global state manager or dependency injection.

### 📂 Project Structure

```text
Anki-TTS-Edge/
├── Anki-TTS-Flet/       # Main compiled source code
│   ├── assets/          # Static resources like icons and localization files
│   ├── config/          # Default configurations and settings I/O
│   ├── core/            # Business logic brain (TTS engine, Alignment, Monitors, History IO)
│   ├── ui/              # Flet UI Views (Modular pages and custom UI components)
│   ├── utils/           # General helper functions (File ops, text formatting, etc.)
│   └── main.py          # Application entry point and initialization
├── .gitignore           # Git ignore rules
└── README.md            # Documentation
```

### 🔨 Building an Executable (EXE)

To bundle the application into a standalone Windows executable (`.exe`), we use PyInstaller with specific arguments to prevent resource path loss:

```bash
# Ensure PyInstaller is installed in your virtual environment
pip install pyinstaller

# Run the build command from the project root
.\.venv\Scripts\python.exe -m PyInstaller Anki-TTS-Flet/main.py --name "Anki-TTS-Edge" --icon "Anki-TTS-Flet/assets/icon.ico" --add-data "Anki-TTS-Flet/assets;assets" --collect-all edge_tts --hidden-import=pystray --hidden-import=PIL --hidden-import=pygame --noconsole --onefile --clean --noconfirm
```

Upon successful build, the standalone `Anki-TTS-Edge.exe` will be located in the `dist/` directory.

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

---

## ⚠️ Disclaimer

This project (Anki-TTS-Edge) is for personal learning, research, and academic exchange purposes only.

1.  **Non-Commercial Use**: This software is not an official Microsoft product and is based on open-source community code. Any audio files generated using this software are for personal use only and are strictly prohibited for any commercial use or public distribution.
2.  **No Liability**:
    *   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
    *   **IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.**
    *   Users assume all risks associated with downloading, installing, and using this software.
3.  **Compliance**: Users must comply with local laws and regulations and Microsoft's relevant terms of service when using this software. Any legal liability arising from violation of laws or terms of service shall be borne solely by the user.

**By downloading or using this software, you agree to all the terms above. If you do not agree, please stop using and delete this software immediately.**
