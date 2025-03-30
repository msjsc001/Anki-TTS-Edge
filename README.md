基于 [Edge-TTS](https://github.com/rany2/edge-tts) 的 Anki 音频生成工具，免费、快速地为你的 Anki 学习卡片添加高质量的微软 Edge 语音。

## ✨ 功能特性

*   **一键生成**：快速为 Anki 卡片选中的文本生成 `.mp3` 音频文件。
*   **快捷操作**：支持右键复制文本后，点击界面上的 🔵 蓝色按钮快速生成音频，并自动将音频文件名复制到剪贴板 (方便粘贴到 Anki 字段)。
*   **多种语音**：支持微软 Edge TTS 提供的多种语言和语音角色选择。
*   **简洁界面**：提供易于使用的图形用户界面 (GUI)。
*   **自动保存**：生成的音频文件自动保存到你指定的 Anki 媒体库文件夹 (`collection.media`)。

## 🚀 快速开始 (推荐)

如果你不想配置 Python 环境，可以直接下载我们为你打包好的 Windows 可执行文件 (`.exe`)：

1.  **前往 Releases 页面**：访问项目的 [GitHub Releases](https://github.com/msjsc001/Anki-TTS-Edge/releases) 页面。
2.  **下载最新版本**：找到最新的版本，下载名为 `Anki-TTS-Edge.zip` (或类似名称) 的压缩包。
3.  **解压运行**：将压缩包解压到你喜欢的任意位置，然后双击运行 `Anki-TTS-Edge.exe` 即可！ 🎉

## 🛠️ 从源码运行 (适合开发者)

如果你熟悉 Python 并希望自行修改或运行源码，请按以下步骤操作：

1.  **克隆仓库**：
    ```bash
    git clone https://github.com/msjsc001/Anki-TTS-Edge.git
    cd Anki-TTS-Edge
    ```
2.  **创建并激活虚拟环境** (推荐)：
    ```bash
    python -m venv .venv
    # Windows
    .\.venv\Scripts\activate
    # macOS/Linux
    # source .venv/bin/activate
    ```
3.  **安装依赖**：
    ```bash
    pip install -r requirements.txt
    ```
4.  **运行程序**：
    ```bash
    python Anki-TTS-Edge.py
    ```

## ⚙️ 如何打包 (开发者参考)

本项目使用 PyInstaller 进行打包。如果你修改了代码并希望重新打包：

1.  确保已在虚拟环境中安装 `pyinstaller` (`pip install pyinstaller`)。
2.  执行打包命令：
    ```bash
    .\.venv\Scripts\activate && pyinstaller Anki-TTS-Edge.spec
    ```
3.  打包后的 `.exe` 文件位于 `dist/Anki-TTS-Edge` 目录下。

## 📄 版权与依赖

*   本项目基于强大的 [edge-tts](https://github.com/rany2/edge-tts) 库开发，该库使用 GPL-3.0 许可证。
*   本项目自身也采用 GPL-3.0 许可证发布。这意味着你可以自由使用、修改和分发本项目的代码，但基于本项目修改后的代码也必须以 GPL-3.0 许可证开源。

## 🤝 参与贡献

欢迎通过提交 Issue 或 Pull Request 来为本项目做出贡献！

---

🌐 **项目地址**：[https://github.com/msjsc001/Anki-TTS-Edge](https://github.com/)
