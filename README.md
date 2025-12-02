# Anki-TTS-Edge

**[English Documentation](https://github.com/msjsc001/Anki-TTS-Edge/blob/master/README-EN.md)**

<div align="center">

Anki-TTS-Edge 是一个基于微软 Edge TTS 技术的免费、高质量语音生成工具。它专为 Anki 学习者设计，能够快速将文本转换为自然流畅的语音文件插入 ANKI ，也可以用于任何语言的朗读和音频文件生成，助力语言学习 。

<img src="https://github.com/user-attachments/assets/d0a3d252-7240-4739-9854-77f16cc2d257" alt="Header Image">

   [![GitHub release (latest by date)](https://img.shields.io/github/v/release/msjsc001/Anki-TTS-Edge)](https://github.com/msjsc001/Anki-TTS-Edge/releases/latest) [![GitHub last commit](https://img.shields.io/github/last-commit/msjsc001/Anki-TTS-Edge)](https://github.com/msjsc001/Anki-TTS-Edge/commits/master) [![GitHub All Releases Downloads](https://img.shields.io/github/downloads/msjsc001/Anki-TTS-Edge/total?label=Downloads&color=brightgreen)](https://github.com/msjsc001/Anki-TTS-Edge/releases)

</div>

## ✨ 核心特性

- **微软 Edge 神经网络语音支持**：利用 Edge TTS 接口，免费提供自然、逼真的多语言发音体验。
- **双蓝点模式**：支持“双蓝点”交互，可快速切换或先后选择两种不同的声音（如一男一女，或不同口音）进行生成。（v1.7.3）
- **生成历史记录**：内置历史记录面板，自动保存生成记录，方便随时回溯和管理已生成的音频文件。（v1.8.0）
- **剪贴板/划词监控**：智能监控系统剪贴板或鼠标划选动作，自动捕获文本并弹出悬浮窗，极大提升制卡效率。
- **悬浮窗与托盘**：提供桌面悬浮窗和系统托盘功能，能够无缝集成到您的桌面工作流中，不占用额外屏幕空间。


## 📸 截图与演示

### 界面概览

<div align="center">
  <img src="https://github.com/user-attachments/assets/1971ed73-c1b8-4784-b3d0-e1ad892b5004" alt="Light Mode Screenshot 1" >
  <img src="https://github.com/user-attachments/assets/2668f79b-4e89-4e45-a476-c04b9afae4bb" alt="Light Mode Screenshot 2" >
</div>
<div align="center">
  <img src="https://github.com/user-attachments/assets/1c6f22a7-5d29-4770-9050-de1c65129f39" alt="Dark Mode Screenshot" >
</div>

### 操作演示

**划选** 或 **Ctrl+C** 文字后点击 🔵 蓝点生成音频，生成音频中会出现 🟢 绿点，生成结束后变为 🔴 红点，而后可按 **Ctrl+V** 快捷粘贴文件！

<div align="center">
  <img src="https://github.com/user-attachments/assets/ff090bd3-4bb0-4bc3-91bb-49d934f1765c" alt="Operation Guide">
</div>

### 动态功能演示

<div align="center">
  <img src="https://github.com/user-attachments/assets/bf232f6c-9e19-418c-a943-2dc3dfd3ea7b" alt="GIF Demo" width="600">
</div>


## 📂 项目结构

```text
Anki-TTS-PY/
├── assets/              # 资源文件 (图标, 翻译配置)
├── config/              # 配置文件 (常量, 设置管理)
├── core/                # 核心逻辑模块
│   ├── audio_gen.py     # 音频生成逻辑
│   ├── clipboard.py     # 剪贴板监控
│   ├── files.py         # 文件操作
│   ├── history.py       # 历史记录管理
│   ├── voice_db.py      # 声音数据库
│   └── voices.py        # 声音列表管理
├── ui/                  # 用户界面模块
│   ├── components/      # UI 组件
│   ├── float_window.py  # 悬浮窗实现
│   ├── main_window.py   # 主窗口实现
│   └── tray_icon.py     # 托盘图标实现
├── utils/               # 工具函数
│   ├── i18n.py          # 国际化支持
│   └── text.py          # 文本处理工具
├── main.py              # 程序启动入口
└── requirements.txt     # 项目依赖列表
```

## 🚀 安装与运行

本程序基于 Python 开发，请确保您的环境中已安装 Python 3.8 或更高版本。

1.  **安装依赖**
    ```bash
    pip install -r Anki-TTS-PY/requirements.txt
    ```

2.  **运行程序**
    ```bash
    python Anki-TTS-PY/main.py
    ```

## 构建指南 (Build)

如果您希望将程序打包为独立的可执行文件（EXE），可以按照以下步骤操作：

1.  **安装依赖**
    ```bash
    pip install -r Anki-TTS-PY/requirements.txt
    ```

2.  **构建 EXE**
    ```bash
    python Anki-TTS-PY/build_exe.py
    ```

构建完成后，可执行文件将位于 `dist/` 目录下。

---
<div align="center">
Made with ❤️ for Anki Users
</div>
