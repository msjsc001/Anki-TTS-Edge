import flet as ft
from utils.i18n import i18n

class HomeView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.expand = True
        self.padding = 20
        
        # --- UI Components ---
        
        # 1. Text Input
        self.text_input = ft.TextField(
            hint_text="",
            multiline=True,
            min_lines=3,
            max_lines=5,
            expand=False,
            border_color=ft.Colors.OUTLINE,
            focused_border_color=ft.Colors.INDIGO,
        )
        
        # 2. Parameters (Sliders)
        self.rate_slider = self._build_slider(i18n.get("rate_label"), 0, -100, 100)
        self.volume_slider = self._build_slider(i18n.get("volume_label"), 0, -100, 100)

        self.volume_slider = self._build_slider(i18n.get("volume_label"), 0, -100, 100)

        # 2.5 Filters (Dual Dropdowns)
        self.lang_dropdown_left = ft.Dropdown(
            label="Language (Left)",
            text_size=14,
            on_change=lambda e: self._on_filter_change('left'),
            expand=True,
            dense=True
        )
        self.lang_dropdown_right = ft.Dropdown(
            label="Language (Right)", 
            text_size=14,
            on_change=lambda e: self._on_filter_change('right'),
            expand=True,
            dense=True
        )
        
        # 3. Voice Lists (Dual Column)
        # Using ListView for efficient scrolling
        self.list_left = ft.ListView(expand=True, spacing=2, padding=10, auto_scroll=False)
        self.list_right = ft.ListView(expand=True, spacing=2, padding=10, auto_scroll=False)
        
        # Region navigation (auto-wrap instead of scroll)
        self.region_nav_left = ft.Row(
            spacing=5, 
            wrap=True,
            run_spacing=5,
        )
        self.region_nav_right = ft.Row(
            spacing=5, 
            wrap=True,
            run_spacing=5,
        )
        
        # Headers for lists
        self.header_left = ft.Text(i18n.get("voice_list_label_1"), weight="bold")
        self.header_right = ft.Text(i18n.get("voice_list_label_2"), weight="bold")
        
        # Containers for lists (border style like text input, no gray background)
        list_container_left = ft.Container(
            content=ft.Column([
                self.header_left,
                ft.Container(content=self.region_nav_left, padding=ft.padding.only(bottom=5)),
                self.list_left
            ], spacing=5),
            expand=True,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=10,
            padding=10,
        )
        
        list_container_right = ft.Container(
            content=ft.Column([
                self.header_right,
                ft.Container(content=self.region_nav_right, padding=ft.padding.only(bottom=5)),
                self.list_right
            ], spacing=5),
            expand=True,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=10,
            padding=10,
        )
        
        # 4. Action Buttons
        self.btn_gen_a = ft.FilledTonalButton(
            text=i18n.get("generate_button_previous"), 
            icon=ft.Icons.PLAY_CIRCLE_OUTLINE, 
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            expand=True,
            height=50,
        )
        self.btn_gen_b = ft.FilledButton(
            text=i18n.get("generate_button_latest"), 
            icon=ft.Icons.PLAY_CIRCLE_FILLED, 
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), 
            expand=True, 
            height=50,
        )

        # 4.5 Audio Control Buttons (Replay, Stop)
        # 4.5 Audio Control Buttons (Replay, Stop)
        self.btn_replay = ft.IconButton(
            icon=ft.Icons.REPLAY,
            tooltip=i18n.get("control_replay", "Replay"),
            icon_size=24,
        )
        self.btn_play_pause = ft.IconButton(
            icon=ft.Icons.PLAY_CIRCLE_OUTLINE, # Default state
            selected_icon=ft.Icons.PAUSE_CIRCLE_OUTLINE, # Playing state
            tooltip=i18n.get("control_play_pause", "Play/Pause"),
            icon_size=24,
        )
        self.btn_stop = ft.IconButton(
            icon=ft.Icons.STOP_CIRCLE_OUTLINED,
            tooltip=i18n.get("control_stop", "Stop"),
            icon_color=ft.Colors.RED,
            icon_size=24,
        )
        
        # 5. Pin Button
        self.btn_pin = ft.IconButton(
             icon=ft.Icons.PUSH_PIN_OUTLINED,
             selected_icon=ft.Icons.PUSH_PIN,
             tooltip=i18n.get("window_pin", "Pin Window"),
             on_click=self._toggle_pin
        )

        # --- Layout Assembly ---
        # Header Row
        header_row = ft.Row(
            [
                ft.Text(i18n.get("input_text_label"), weight="bold", size=16),
                self.btn_pin
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        self.content = ft.Column(
            expand=True,
            alignment=ft.MainAxisAlignment.START,
            controls=[
                header_row,
                self.text_input,
                ft.Divider(height=10, color="transparent"),
                
                # Filters
                ft.Row([self.lang_dropdown_left, self.lang_dropdown_right], spacing=20),
                ft.Divider(height=10, color="transparent"),

                # Voice Selection Area
                ft.Row(
                    [list_container_left, list_container_right],
                    expand=True,
                    spacing=20,
                ),
                
                ft.Divider(height=10, color="transparent"),
                
                # Parameters Row
                ft.Row(
                    [
                        ft.Column([ft.Text(i18n.get("rate_label")), self.rate_slider], expand=True),
                        ft.Column([ft.Text(i18n.get("volume_label")), self.volume_slider], expand=True),
                    ],
                    spacing=20
                ),
                
                ft.Divider(height=10, color="transparent"),
                
                # Buttons Row
                ft.Row(
                    [
                        self.btn_gen_a, 
                        self.btn_gen_b,
                        ft.VerticalDivider(width=10),
                        self.btn_replay,
                        self.btn_play_pause,
                        self.btn_stop
                    ],
                    spacing=10,
                )
            ],
        )

    def _toggle_pin(self, e):
        e.control.selected = not e.control.selected
        e.control.update()
        if hasattr(self, 'on_pin_toggle'):
            self.on_pin_toggle(e.control.selected)

    def _build_slider(self, label, value, min_v, max_v):
        return ft.Slider(
            min=min_v, 
            max=max_v, 
            divisions=200, 
            value=value, 
            label="{value}%",
            active_color=ft.Colors.INDIGO,
        )

    # --- Methods to Populate Data (To be called by Controller) ---
    def set_dual_mode(self, enabled):
        self.dual_mode = enabled
        if enabled:
            self.btn_gen_a.visible = True
            self.btn_gen_b.text = i18n.get("generate_button_latest")
        else:
            self.btn_gen_a.visible = False
            self.btn_gen_b.text = i18n.get("generate_button_label")
        self.btn_gen_a.update()
        self.btn_gen_b.update()

    def set_selections(self, latest, previous):
        self.selected_voice_latest = latest
        self.selected_voice_previous = previous
        if hasattr(self, 'all_voices_data'):
            # Refresh both sides
            self._render_voices(self.all_voices_data)

    def populate_voices(self, voice_list, side='both'):
        # voice_list is a list of dicts: {"name": str, "lang": str, "region": str}
        self.all_voices_data = voice_list # Store for filtering
        
        # Extract Languages for Dropdowns
        langs = sorted(list(set([v["lang"] for v in voice_list])))
        
        # Create DISTINCT option lists for each dropdown to avoid shared control ownership issues
        options_left = [ft.dropdown.Option(l) for l in langs]
        options_right = [ft.dropdown.Option(l) for l in langs]
        
        # Update Dropdowns (preserve selection if possible)
        current_l = self.lang_dropdown_left.value
        current_r = self.lang_dropdown_right.value
        
        self.lang_dropdown_left.options = options_left
        self.lang_dropdown_right.options = options_right
        
        # Set Defaults if empty
        if not current_l:
            # Try find zh-CN or starts with zh
            zh = next((l for l in langs if l.startswith("zh")), langs[0] if langs else None)
            self.lang_dropdown_left.value = zh
            
        if not current_r:
             # Try find en-US or starts with en
            en = next((l for l in langs if l.startswith("en")), langs[0] if langs else None)
            self.lang_dropdown_right.value = en

        self.lang_dropdown_left.update()
        self.lang_dropdown_right.update()

        self._render_voices(voice_list, side)

    def _on_filter_change(self, side):
        if hasattr(self, 'all_voices_data'):
            self._render_voices(self.all_voices_data)

    def _render_voices(self, voice_list, side='both'):
        
        def filter_list(full_list, lang_filter):
            if not lang_filter: return full_list
            return [v for v in full_list if v["lang"] == lang_filter]
            
        left_voices = filter_list(voice_list, self.lang_dropdown_left.value)
        right_voices = filter_list(voice_list, self.lang_dropdown_right.value)
        
        def create_tiles(target_list, nav_row, data_source, list_ref, region_positions):
            target_list.controls.clear()
            nav_row.controls.clear()
            region_positions.clear()
            
            if not data_source:
                return
            
            # Collect unique regions for navigation
            regions = []
            for item in data_source:
                if item["region"] not in regions:
                    regions.append(item["region"])
            
            # Create region navigation chips
            control_index = 0  # Track control index for scrolling
            for region in regions:
                chip = ft.Container(
                    content=ft.Text(region, size=11, weight="w500", color="onPrimaryContainer"),
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    bgcolor="primaryContainer",
                    border_radius=12,
                    on_click=lambda e, r=region, lv=list_ref, rp=region_positions: self._scroll_to_region_by_index(lv, rp.get(r, 0)),
                    ink=True,
                )
                nav_row.controls.append(chip)
            
            current_region = None
            import re
            
            for item in data_source:
                name = item["name"]
                lang = item["lang"]
                region = item["region"]
                
                # Region section header
                if region != current_region:
                    # Record position before adding the header
                    region_positions[region] = len(target_list.controls)
                    
                    # Simple elegant header - centered badge style
                    section_header = ft.Container(
                        key=f"region_{region}",
                        content=ft.Text(
                            region, 
                            weight="bold", 
                            size=12, 
                            color="onSecondaryContainer",
                            text_align=ft.TextAlign.CENTER,
                        ),
                        bgcolor="secondaryContainer",
                        padding=ft.padding.symmetric(horizontal=12, vertical=4),
                        border_radius=15,
                        margin=ft.margin.only(top=12, bottom=6),
                        alignment=ft.alignment.center,
                    )
                    target_list.controls.append(section_header)
                    current_region = region
                
                # Simple display name extraction
                match = re.search(r", (.*Neural)\)$", name)
                display_name = match.group(1) if match else name

                # Selection status
                is_latest = hasattr(self, 'selected_voice_latest') and name == self.selected_voice_latest
                is_previous = hasattr(self, 'selected_voice_previous') and hasattr(self, 'dual_mode') and self.dual_mode and name == self.selected_voice_previous
                
                trailing_content = None
                bg = "surfaceVariant"
                
                # Colors
                BG_B = ft.Colors.TEAL_50 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.TEAL_900
                BG_A = ft.Colors.INDIGO_50 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.INDIGO_900
                BG_BOTH = ft.Colors.BLUE_50 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.BLUE_900
                
                show_b_badge = hasattr(self, 'dual_mode') and self.dual_mode
                
                if is_latest and is_previous:
                     trailing_content = ft.Row([
                         ft.Container(content=ft.Text("A", color="white", size=10, weight="bold"), bgcolor=ft.Colors.INDIGO, padding=5, border_radius=5),
                         ft.Container(content=ft.Text("B", color="white", size=10, weight="bold"), bgcolor=ft.Colors.TEAL, padding=5, border_radius=5)
                     ], spacing=5)
                     bg = BG_BOTH
                elif is_latest:
                     if show_b_badge:
                         trailing_content = ft.Container(content=ft.Text("B", color="white", size=10, weight="bold"), bgcolor=ft.Colors.TEAL, padding=5, border_radius=5)
                         bg = BG_B
                     else:
                         trailing_content = ft.Icon(ft.Icons.CHECK, color=ft.Colors.TEAL)
                         bg = BG_B
                elif is_previous:
                     trailing_content = ft.Container(content=ft.Text("A", color="white", size=10, weight="bold"), bgcolor=ft.Colors.INDIGO, padding=5, border_radius=5)
                     bg = BG_A

                tile = ft.ListTile(
                    leading=ft.Icon(ft.Icons.RECORD_VOICE_OVER, color=ft.Colors.ON_SURFACE),
                    title=ft.Text(display_name, size=14, weight="w500"),
                    trailing=trailing_content,
                    dense=True,
                    data=name,
                    on_click=self._on_voice_selected,
                    shape=ft.RoundedRectangleBorder(radius=8),
                    hover_color=ft.Colors.with_opacity(0.1, ft.Colors.INDIGO),
                    bgcolor=bg
                )
                target_list.controls.append(tile)
            
        if side == 'both':
            # Store region positions for scroll navigation
            self._region_positions_left = {}
            self._region_positions_right = {}
            create_tiles(self.list_left, self.region_nav_left, left_voices, self.list_left, self._region_positions_left)
            create_tiles(self.list_right, self.region_nav_right, right_voices, self.list_right, self._region_positions_right)
        
        self.update()
    
    def _scroll_to_region_by_index(self, list_view, index):
        """Scroll to a region section by control index - more reliable for distant items"""
        try:
            # Calculate approximate offset based on index
            # Average item height is roughly 50px (ListTile dense + section headers)
            estimated_offset = index * 50
            list_view.scroll_to(offset=estimated_offset, duration=300)
            self.page.update()
        except Exception as e:
            print(f"DEBUG: Scroll to region by index failed: {e}")

    def _on_voice_selected(self, e):
        self.selected_voice_name = e.control.data
        if hasattr(self, 'on_voice_selected'):
            self.on_voice_selected(e)

    # --- Getters ---
    def get_input_text(self):
        return self.text_input.value

    def set_input_text(self, text):
        self.text_input.value = text
        self.text_input.update()

    def get_params(self):
        rate = f"{int(self.rate_slider.value):+d}%"
        volume = f"{int(self.volume_slider.value):+d}%"
        return rate, volume

    def get_selected_voice(self):
        if hasattr(self, 'selected_voice_name'):
            return self.selected_voice_name
        return None

    def _toggle_pin(self, e):
        """Toggle pin (always on top) state"""
        self.btn_pin.selected = not self.btn_pin.selected
        self.btn_pin.update()
        
        is_pinned = self.btn_pin.selected
        print(f"DEBUG: Pin button toggled -> {is_pinned}")
        
        if hasattr(self, 'on_pin_toggle'):
            self.on_pin_toggle(is_pinned)
