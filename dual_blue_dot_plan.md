# Anki-TTS-Edge "双蓝点" 功能实现计划

## 目标

在现有“蓝点”悬浮窗功能基础上，增加一个“双蓝点”模式，允许用户选择最近使用的两个声音，并通过左右两个蓝点按钮或主界面按钮分别触发音频生成。

## 核心需求

1.  **模式开关:** 设置中添加“双蓝点(先后选择两个声音)”开关。
2.  **声音选择:**
    *   记录用户最近选择的两个不同声音：`latest` (最新) 和 `previous` (上一次)。
    *   选择新声音时，`latest` 变为 `previous`，新声音变为 `latest`。
    *   若只选过一个，`previous` 和 `latest` 相同。
    *   UI 上视觉区分 `latest` 和 `previous` 的选中状态。
3.  **悬浮窗:**
    *   启用模式后，显示两个紧挨着的圆形“音”按钮。
    *   左按钮使用 `previous` 声音，右按钮使用 `latest` 声音。
4.  **主界面生成按钮:**
    *   启用模式后，底部生成按钮变为两个。
    *   左按钮使用 `previous` 声音，右按钮使用 `latest` 声音。
5.  **翻译:** 补充英文翻译。
6.  **原则:** 最小化对无关代码的改动。

## 详细执行步骤

### 阶段 1: 数据模型与设置

1.  **修改 `load_settings` (EdgeTTSApp):**
    *   在 `defaults` 字典中，移除 `selected_voice`，添加 `selected_voice_latest` (默认 `DEFAULT_VOICE`) 和 `selected_voice_previous` (默认 `DEFAULT_VOICE`)。
    *   添加 `dual_blue_dot_enabled` (默认 `False`)。
    *   处理向后兼容：若存在旧 `selected_voice`，赋值给新 key。
2.  **修改 `save_settings` (EdgeTTSApp):**
    *   移除保存 `selected_voice`。
    *   添加保存 `selected_voice_latest`, `selected_voice_previous`, `dual_blue_dot_enabled`。
3.  **修改 `EdgeTTSApp.__init__`:**
    *   添加实例变量：`self.dual_blue_dot_enabled` (ctk.BooleanVar), `self.selected_voice_latest`, `self.selected_voice_previous`。
    *   逐步移除或重构对 `self.current_full_voice_name` 的依赖。

### 阶段 2: UI 修改 - 设置界面

1.  **修改 `EdgeTTSApp.__init__` (Settings Tab):**
    *   在 `clipboard_frame` 中添加 `self.dual_blue_dot_switch` (ctk.CTkSwitch)。
    *   绑定 `command=self._toggle_dual_blue_dot_mode`。
    *   添加到 `self._language_widgets` 和 `switches_to_color`。
2.  **添加 `_toggle_dual_blue_dot_mode` 方法 (EdgeTTSApp):**
    *   (稍后实现完整逻辑)。
3.  **更新 `translations.json`:**
    *   添加 `"settings_dual_blue_dot_label"` 的中英文翻译。

### 阶段 3: UI 修改 - 声音列表

1.  **修改 `_select_voice_inline(self, full_name)` (EdgeTTSApp):**
    *   实现新的选择逻辑：更新 `latest` 和 `previous`，刷新列表，保存设置。
2.  **修改 `_populate_inline_voice_list(self, side)` (EdgeTTSApp):**
    *   根据 `is_latest` 和 `is_previous` 状态确定按钮背景色 (`color_latest_bg`, `color_previous_bg`)。
    *   应用不同的背景色和对应的文字颜色。
3.  **修改 `update_voice_ui` (EdgeTTSApp):**
    *   加载 `latest` 和 `previous` 设置。
    *   确保 `previous` 有效。
    *   移除对 `current_full_voice_name` 的依赖。

### 阶段 4: UI 修改 - 主界面生成按钮

1.  **修改 `EdgeTTSApp.__init__` (Bottom Frame):**
    *   移除单个 `generate_button`。
    *   创建 `self.generate_button_left` 和 `self.generate_button_right`。
    *   绑定命令 `lambda: self.generate_audio_manual(voice_type='previous')` 和 `lambda: self.generate_audio_manual(voice_type='latest')`。
    *   添加到 `_language_widgets` 和 `buttons_to_color`。
    *   调用 `self._update_main_generate_buttons_visibility()`。
2.  **创建 `_update_main_generate_buttons_visibility` 方法 (EdgeTTSApp):**
    *   根据 `dual_blue_dot_enabled` 状态显示/隐藏左右按钮（或使用单独的单按钮）。
3.  **修改 `generate_audio_manual(self, voice_type)` (EdgeTTSApp):**
    *   接受 `voice_type` 参数。
    *   根据 `voice_type` 获取 `voice` (`latest` 或 `previous`)。
    *   修改按钮状态管理（禁用/启用）。
    *   调用 `generate_audio`。

### 阶段 5: 浮窗逻辑修改

1.  **重构 `show_float_window` -> `_show_single_float_window(self, text=None)`:**
    *   修改按钮命令为 `_trigger_generate_from_float(voice_type='latest', ...)`。
2.  **创建 `_show_dual_float_window(self, text=None)` (EdgeTTSApp):**
    *   创建 Toplevel 窗口和两个按钮 `btn_left`, `btn_right`。
    *   绑定命令 `_trigger_generate_from_float(voice_type='previous', ...)` 和 `_trigger_generate_from_float(voice_type='latest', ...)`。
    *   设置自动关闭。
3.  **创建 `show_float_window_controller(self, text=None)` (EdgeTTSApp):** (新入口点)
    *   获取鼠标位置。
    *   根据 `dual_blue_dot_enabled` 调用 `_show_single_float_window` 或 `_show_dual_float_window`。
4.  **修改 `_trigger_float_from_selection` 和 `_trigger_float_from_poll`:**
    *   调用 `self.show_float_window_controller(...)`。
5.  **修改 `trigger_generate_from_float` -> `_trigger_generate_from_float(self, voice_type, text)`:**
    *   实现获取位置、销毁浮窗、选声音、处理触发方式、调用 `_process_and_generate_audio` 的逻辑。
6.  **修改 `_process_and_generate_audio(self, text, position, voice_to_use)` (EdgeTTSApp):**
    *   添加 `voice_to_use` 参数。
    *   使用 `voice_to_use` 调用 `generate_audio`。

### 阶段 6: 模式切换与收尾

1.  **完成 `_toggle_dual_blue_dot_mode` 方法 (EdgeTTSApp):**
    *   调用 `_update_main_generate_buttons_visibility()`。
    *   调用 `_populate_inline_voice_list('left')` 和 `_populate_inline_voice_list('right')`。
    *   调用 `self.save_settings()`。
    *   更新状态栏。
2.  **测试:** 全面测试所有相关功能和模式。
3.  **代码审查与优化:** 清理代码，移除冗余。