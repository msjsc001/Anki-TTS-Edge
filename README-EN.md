# Anki-TTS-Edge

**[中文文档](https://github.com/msjsc001/Anki-TTS-Edge/blob/master/README.md)**

<div align="center">

Anki-TTS-Edge is a free, high-quality voice generation tool based on Microsoft Edge TTS technology. Designed specifically for Anki learners, it can quickly convert text into natural, fluent audio files for insertion into ANKI. It can also be used for reading aloud in any language and generating audio files to assist with language learning.

<img src="https://github.com/user-attachments/assets/d0a3d252-7240-4739-9854-77f16cc2d257" alt="Header Image">

   [![GitHub release (latest by date)](https://img.shields.io/github/v/release/msjsc001/Anki-TTS-Edge)](https://github.com/msjsc001/Anki-TTS-Edge/releases/latest) [![GitHub last commit](https://img.shields.io/github/last-commit/msjsc001/Anki-TTS-Edge)](https://github.com/msjsc001/Anki-TTS-Edge/commits/master) [![GitHub All Releases Downloads](https://img.shields.io/github/downloads/msjsc001/Anki-TTS-Edge/total?label=Downloads&color=brightgreen)](https://github.com/msjsc001/Anki-TTS-Edge/releases)

</div>

## ✨ Key Features

- **Microsoft Edge Neural Network Voice Support**: Utilizes the Edge TTS interface to provide a free, natural, and realistic multi-language pronunciation experience.
- **Dual Blue Dot Mode**: Supports "Dual Blue Dot" interaction, allowing quick switching or sequential selection of two different voices (e.g., one male and one female, or different accents) for generation. (v1.7.3)
- **Generation History**: Built-in history panel automatically saves generation records, facilitating easy backtracking and management of generated audio files at any time. (v1.8.0)
- **Clipboard/Selection Monitoring**: Intelligently monitors the system clipboard or mouse selection actions, automatically capturing text and popping up a floating window, greatly improving card-making efficiency.
- **Floating Window & Tray**: Provides desktop floating window and system tray functions, seamlessly integrating into your desktop workflow without occupying extra screen space.


## 📸 Screenshots & Demos

### Interface Overview

<div align="center">
  <img src="https://github.com/user-attachments/assets/1971ed73-c1b8-4784-b3d0-e1ad892b5004" alt="Light Mode Screenshot 1" >
  <img src="https://github.com/user-attachments/assets/2668f79b-4e89-4e45-a476-c04b9afae4bb" alt="Light Mode Screenshot 2" >
</div>
<div align="center">
  <img src="https://github.com/user-attachments/assets/1c6f22a7-5d29-4770-9050-de1c65129f39" alt="Dark Mode Screenshot" >
</div>

### Operation Demo

**Select** or **Ctrl+C** text, then click the 🔵 blue dot to generate audio. A 🟢 green dot will appear during generation, turning into a 🔴 red dot upon completion, after which you can press **Ctrl+V** to paste the file quickly!

<div align="center">
  <img src="https://github.com/user-attachments/assets/ff090bd3-4bb0-4bc3-91bb-49d934f1765c" alt="Operation Guide">
</div>

### Dynamic Feature Demo

<div align="center">
  <img src="https://github.com/user-attachments/assets/bf232f6c-9e19-418c-a943-2dc3dfd3ea7b" alt="GIF Demo" width="600">
</div>


## 📂 Project Structure

```text
Anki-TTS-PY/
├── assets/              # Resource files (icons, translation configs)
├── config/              # Configuration files (constants, settings management)
├── core/                # Core logic modules
│   ├── audio_gen.py     # Audio generation logic
│   ├── clipboard.py     # Clipboard monitoring
│   ├── files.py         # File operations
│   ├── history.py       # History management
│   ├── voice_db.py      # Voice database
│   └── voices.py        # Voice list management
├── ui/                  # User interface modules
│   ├── components/      # UI components
│   ├── float_window.py  # Floating window implementation
│   ├── main_window.py   # Main window implementation
│   └── tray_icon.py     # Tray icon implementation
├── utils/               # Utility functions
│   ├── i18n.py          # Internationalization support
│   └── text.py          # Text processing tools
├── main.py              # Program entry point
└── requirements.txt     # Project dependencies list
```

## 🚀 Installation & Running

This program is developed based on Python. Please ensure that Python 3.8 or higher is installed in your environment.

1.  **Install Dependencies**
    ```bash
    pip install -r Anki-TTS-PY/requirements.txt
    ```

2.  **Run Program**
    ```bash
    python Anki-TTS-PY/main.py
    ```

## Build Guide

If you wish to package the program as a standalone executable (EXE), you can follow these steps:

1.  **Install Dependencies**
    ```bash
    pip install -r Anki-TTS-PY/requirements.txt
    ```

2.  **Build EXE**
    ```bash
    python Anki-TTS-PY/build_exe.py
    ```

After building, the executable file will be located in the `dist/` directory.

---
<div align="center">
Made with ❤️ for Anki Users
</div>