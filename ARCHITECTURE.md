# Anki-TTS-Edge Architecture

## 1. 核心运行链路

- `Anki-TTS-Flet/main.py`
  - Flet 主窗口入口。
  - 负责页面初始化、托盘/卫星窗/监听器接线、播放状态机与视图联动。
- `Anki-TTS-Flet/core/audio_gen.py`
  - 使用 `edge-tts` 生成音频与词级时间戳。
  - 生成文件统一落到 `%APPDATA%/Anki-TTS-Edge/audio/`。
- `Anki-TTS-Flet/core/history.py`
  - 维护历史记录 JSON。
  - 历史上限不仅裁剪记录，还必须同步删除被挤出的音频与时间戳文件。
- `Anki-TTS-Flet/core/clipboard.py`
  - 负责剪贴板监听、划词复制注入、卫星窗进程通信。
- `Anki-TTS-Flet/core/satellite.py`
  - 独立 `tkinter` 进程，显示单点/双点悬浮操作入口。
- `Anki-TTS-Flet/ui/*.py`
  - `home_view.py` 负责输入、声音列表、播放控件与高亮文本覆盖层。
  - `history_view.py` 负责历史展示与删除/清空操作。
  - `settings_view.py` 负责主题、监听、托盘、窗口尺寸、数据目录等设置项。

## 2. 关键状态边界

- 播放状态只以 `main.py` 内的 `current_audio_state` 为唯一真源。
- 切换音频文件时，必须同步重置：
  - `path`
  - `timestamps`
  - `text`
  - `current_sentence_index`
  - `current_playback_start_ms`
  - `stop_playback_at_ms`
- 播放监控协程必须保持单实例。
  - 新播放开始时提升 `run_id`，旧监控循环自动失效退出。
  - 暂停/恢复不能重复启动监控循环。

## 3. 持久化规则

- 用户数据统一存储到 `%APPDATA%/Anki-TTS-Edge/`。
- 只允许以下长期文件存在：
  - `voice_settings.json`
  - `history.json`
  - `voices_cache.json`
  - `logs/monitor_debug.log`
  - `audio/*.mp3`
  - `audio/*.timestamps.json`
- 音频文件名必须全局唯一。
  - 不能只用秒级时间戳，否则高频连续生成会发生覆盖。
  - 当前实现使用 `微秒时间戳 + 短 UUID`。

## 4. UI / 设置约束

- `appearance_mode` 是主题持久化唯一字段。
  - 旧版 `theme_dark` 仅做兼容迁移，不再继续写入。
- 剪贴板监听与划词监听是两个独立能力：
  - `monitor_clipboard_enabled`
  - `monitor_selection_enabled`
- 双蓝点模式依赖划词监听，但剪贴板监听不依赖划词监听。

## 5. 已修复的高风险问题

- 修复安装依赖缺失导致的启动即崩：
  - 新增 `pynput`
  - 新增 `pywin32`
- 修复旧版 Flet 窗口 API 残留：
  - 统一为 `page.window.visible`
  - 统一为 `page.window.minimized`
  - 统一为 `page.window.to_front()`
- 修复历史回放复用上一条音频的高亮/时间轴污染。
- 修复历史缓存上限只删 JSON 不删磁盘文件。
- 修复主题设置无法跨重启稳定恢复。
- 修复设置页把剪贴板监听错误绑死到划词监听。
- 修复播放监控协程可重复并发启动导致的状态竞态。
- 修复历史记录展示读取错误字段导致的空信息。

## 6. 当前工程注意事项

- `requirements.txt` 与 README 安装说明必须保持同步，否则用户会按文档装出一个不可运行环境。
- 涉及窗口前置、显示、销毁的 Flet `Window` 方法优先按官方异步接口使用。
- 如果未来增加“清理数据目录”能力，必须按类别清理：
  - 音频
  - 历史
  - 日志
  - 语音缓存
  - 设置
