# 更新日志 / Changelog

## v2.4 (2026-03-01)

### ✨ 新功能 / Features

- **即点即读精确定位**：点击文段中任意单词/字符时，直接从该位置开始播放，不再跳转到句首，定位更精确。
  **Precise click-to-play**: Clicking any word/character in the text now starts playback from that exact position instead of jumping to the sentence start, providing more precise control.

### 📦 构建 / Build

- **构建方式切换为 onedir 模式**：从 PyInstaller 单文件 (onefile) 切换为文件夹 (onedir) 模式，大幅提升 Windows 下的启动速度（消除杀毒软件扫描导致的延迟）。
  **Switch to onedir build**: Changed from PyInstaller single-file (onefile) to folder (onedir) mode, significantly improving Windows startup speed by eliminating antivirus scan delays.

---

## v2.3 (2026-03-01)

### 🔧 修复 / Fixes

- **修复 TTS 生成失败**：升级 `edge-tts` 至 7.2.7，修复微软 API 认证令牌过期导致的 403 错误，恢复所有语音的正常生成能力。
  **Fix TTS generation failure**: Upgraded `edge-tts` to 7.2.7, resolving 403 errors caused by expired Microsoft API authentication tokens. All voices are now functional again.

- **修复单词高亮跟随失效**：适配 `edge-tts` 7.x API 变更（`boundary` 参数默认值从 `WordBoundary` 改为 `SentenceBoundary`），显式传入 `boundary='WordBoundary'` 以恢复单词级时间戳和实时高亮。
  **Fix word-level highlight sync broken**: Adapted to `edge-tts` 7.x API change where the `boundary` parameter default changed from `WordBoundary` to `SentenceBoundary`. Now explicitly passes `boundary='WordBoundary'` to restore word-level timestamps and real-time highlighting.

- **修复重复函数定义** (`handle_generate_a`)：删除 `main.py` 中残留的重复函数定义。
  **Fix duplicate function definition** (`handle_generate_a`): Removed leftover duplicate definition in `main.py`.

- **修复窗口事件双重绑定**：移除旧 API 的事件绑定 (`page.on_window_event`)，仅保留新 API (`page.window.on_event`)，避免窗口关闭/最小化事件被触发两次。
  **Fix double window event binding**: Removed legacy API binding (`page.on_window_event`), keeping only the new API (`page.window.on_event`) to prevent duplicate event triggers on close/minimize.

- **修复 `MonitorManager.stop()` 缺失**：添加 `stop()` 方法作为 `stop_monitors()` 的别名，修复应用重启时的 `AttributeError`。
  **Fix missing `MonitorManager.stop()`**: Added `stop()` as an alias for `stop_monitors()`, fixing `AttributeError` on app restart.

- **修复卫星轮询中无效的 `locals()` 检查**：`satellite_loop` 中的 `monitor_manager` 是闭包变量，`locals()` 永远无法检测到它，已改用 `hasattr()` 检查。
  **Fix invalid `locals()` check in satellite loop**: `monitor_manager` is a closure variable, so `locals()` could never detect it. Replaced with `hasattr()`.

### ⚡ 优化 / Improvements

- **窗口缩放防抖**：拖拽调整窗口大小时，设置文件不再每帧写入磁盘，改为 300ms 防抖延迟写入，大幅降低 I/O 压力。
  **Window resize debounce**: Settings are no longer written to disk on every resize frame. Added 300ms debounce to significantly reduce I/O during window dragging.

- **日志改为追加模式**：剪贴板监控日志从覆盖模式 (`filemode='w'`) 改为 `RotatingFileHandler` 追加模式，保留历史诊断信息，文件上限 1MB 自动轮转。
  **Log rotation**: Clipboard monitor logging changed from overwrite mode (`filemode='w'`) to `RotatingFileHandler` with 1MB cap, preserving diagnostic history.

- **消除裸异常捕获**：全项目 14 处 `except: pass` 替换为 `except Exception`，避免吞掉关键错误信息。
  **Eliminate bare excepts**: All 14 instances of `except: pass` replaced with `except Exception` across the project to prevent silently swallowing critical errors.

- **删除死代码**：移除 `audio_gen.py` 中不再被调用的 `generate_audio` 和 `generate_audio_edge_tts_async` 函数及未使用的 `threading` 导入，代码行数减少 40%。
  **Remove dead code**: Removed unused `generate_audio` and `generate_audio_edge_tts_async` functions along with the unused `threading` import from `audio_gen.py`, reducing file size by 40%.

---

## v2.2 (2026-02-26)

- 历史记录深度清理：自动扫描音频目录，清除孤立的音频文件和配套数据文件。
  Deep history cleanup: Automatically scans audio directory and removes orphaned audio and metadata files.

## v2.1

- 高亮跟随朗读，即点即读，智能导航。
  Real-time word highlighting, click-to-play, smart sentence navigation.

## v2.0

- 全新 Flet (Flutter) 重构，现代化 UI。
  Full Flet (Flutter) rewrite with modern UI.
