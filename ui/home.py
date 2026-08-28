"""
主计时界面。

视觉结构（从上到下）：
1. 顶栏：Spectrum 标志 + 模式管理按钮
2. 模式选择下拉（从 SQLite 动态加载）
3. 超大倒计时数字 + 环形进度（视觉焦点）
4. 阶段标签（专注 / 休息，颜色随阶段切换）
5. 开始 / 暂停 / 重置

毛玻璃卡片、发光阴影、大号无衬线字体都在这里落地。
计时逻辑全部委托给 PomodoroTimer，本文件只负责渲染和用户手势。
"""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

import theme
from database import Database, TimerMode
from timer import Phase, PomodoroTimer


class HomeView:
    """主页控件树的持有者。main.py 创建一次，之后只调用 refresh_*。"""

    def __init__(
        self,
        page: ft.Page,
        db: Database,
        timer: PomodoroTimer,
        on_mode_changed: Callable[[TimerMode], None],
    ) -> None:
        self.page = page
        self.db = db
        self.timer = timer
        self.on_mode_changed = on_mode_changed

        # 这些控件会在 tick 时被原地改属性，必须先建出来再组树。
        self.time_text = ft.Text(
            timer.display,
            size=84,
            weight=ft.FontWeight.W_200,
            color=theme.TEXT,
            font_family="Courier New",
            text_align=ft.TextAlign.CENTER,
        )
        self.phase_chip = self._build_phase_chip()
        self.ring = ft.ProgressRing(
            value=timer.progress,
            width=280,
            height=280,
            stroke_width=6,
            color=theme.CYAN,
            bgcolor="#18FFFFFF",
        )
        self.status_hint = ft.Text(
            "READY TO ENGAGE",
            size=11,
            color=theme.TEXT_DIM,
            weight=ft.FontWeight.W_500,
        )
        self.start_btn = ft.Button(
            content="开始",
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            height=48,
            expand=True,
            style=ft.ButtonStyle(
                bgcolor=theme.CYAN,
                color="#041018",
                overlay_color="#22FFFFFF",
                shape=ft.RoundedRectangleBorder(radius=14),
            ),
            on_click=self._on_start,
        )
        self.pause_btn = ft.OutlinedButton(
            content="暂停",
            icon=ft.Icons.PAUSE_ROUNDED,
            height=48,
            expand=True,
            style=ft.ButtonStyle(
                color=theme.TEXT,
                side=ft.BorderSide(1, theme.BORDER),
                shape=ft.RoundedRectangleBorder(radius=14),
            ),
            on_click=self._on_pause,
        )
        self.reset_btn = ft.IconButton(
            icon=ft.Icons.REPLAY_ROUNDED,
            icon_color=theme.TEXT_MUTED,
            tooltip="重置当前阶段",
            on_click=self._on_reset,
        )
        self.mode_dropdown = ft.Dropdown(
            label="当前模式",
            filled=True,
            fill_color="#12FFFFFF",
            border_color=theme.BORDER,
            focused_border_color=theme.CYAN,
            color=theme.TEXT,
            label_style=ft.TextStyle(color=theme.TEXT_MUTED, size=12),
            text_size=14,
            border_radius=14,
            expand=True,
            options=[],
            on_select=self._on_mode_select,
        )
        self._refresh_mode_options(select_id=timer.mode.id)
        self.root = self._build()
        self._sync_phase_visuals(timer.phase)
        self._sync_buttons()

    # ------------------------------------------------------------------
    # 构建
    # ------------------------------------------------------------------
    def _build(self) -> ft.Control:
        return ft.Container(
            expand=True,
            padding=ft.Padding.symmetric(horizontal=24, vertical=12),
            content=ft.Column(
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=18,
                controls=[
                    self._build_header(),
                    self._build_mode_row(),
                    ft.Container(expand=True),
                    self._build_timer_stage(),
                    ft.Container(expand=True),
                    self._build_controls(),
                    ft.Container(height=8),
                ],
            ),
        )

    def _build_header(self) -> ft.Control:
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(
                            "SPECTRUM",
                            size=13,
                            weight=ft.FontWeight.W_700,
                            color=theme.CYAN,
                        ),
                        ft.Text(
                            "AI Focus Runtime",
                            size=11,
                            color=theme.TEXT_MUTED,
                        ),
                    ],
                ),
                ft.IconButton(
                    icon=ft.Icons.TUNE_ROUNDED,
                    icon_color=theme.TEXT_MUTED,
                    tooltip="管理时间模式",
                    on_click=self._open_mode_manager,
                ),
            ],
        )

    def _build_mode_row(self) -> ft.Control:
        return self._glass(
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            content=self.mode_dropdown,
        )

    def _build_phase_chip(self) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=6),
            border_radius=20,
            bgcolor="#2222D3EE",
            border=ft.Border.all(1, theme.CYAN),
            content=ft.Text(
                "FOCUS SESSION",
                size=11,
                weight=ft.FontWeight.W_600,
                color=theme.CYAN,
            ),
        )

    def _build_timer_stage(self) -> ft.Control:
        """倒计时是整页视觉焦点：280px 光环 + 84px 等宽数字。"""
        stacked = ft.Stack(
            width=280,
            height=280,
            alignment=ft.Alignment.CENTER,
            controls=[
                self.ring,
                ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                    controls=[
                        self.time_text,
                        self.status_hint,
                    ],
                ),
            ],
        )
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[self.phase_chip, stacked],
        )

    def _build_controls(self) -> ft.Control:
        return ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
            controls=[self.start_btn, self.pause_btn, self.reset_btn],
        )

    def _glass(
        self,
        content: ft.Control,
        padding: Optional[ft.Padding] = None,
        radius: int = 18,
    ) -> ft.Container:
        """半透明底 + 高斯模糊 + 细描边，即毛玻璃卡片。"""
        return ft.Container(
            content=content,
            padding=padding or ft.Padding.all(16),
            border_radius=radius,
            bgcolor=theme.SURFACE,
            blur=ft.Blur(18, 18, ft.BlurTileMode.CLAMP),
            border=ft.Border.all(1, theme.BORDER),
            shadow=ft.BoxShadow(
                blur_radius=24,
                color="#40000000",
                offset=ft.Offset(0, 8),
            ),
        )

    # ------------------------------------------------------------------
    # 刷新（由 Timer 回调 / 模式变更驱动）
    # ------------------------------------------------------------------
    def refresh_tick(self) -> None:
        self.time_text.value = self.timer.display
        self.ring.value = self.timer.progress
        if self.timer.running:
            self.status_hint.value = (
                "NEURAL LINK ACTIVE"
                if self.timer.phase == Phase.FOCUS
                else "COOLING CYCLE"
            )
        elif self.timer.remaining == self.timer.total_seconds:
            self.status_hint.value = "READY TO ENGAGE"
        else:
            self.status_hint.value = "PAUSED"
        start_label = "继续" if (
            not self.timer.running and self.timer.remaining != self.timer.total_seconds
        ) else "开始"
        self.start_btn.content = start_label
        self._sync_buttons()
        self.page.update()

    def refresh_phase(self, phase: Phase) -> None:
        self._sync_phase_visuals(phase)
        self.refresh_tick()

    def reload_modes(self, select_id: Optional[int] = None) -> None:
        self._refresh_mode_options(select_id=select_id or self.timer.mode.id)
        self.page.update()

    def _sync_phase_visuals(self, phase: Phase) -> None:
        """专注↔休息切换时的明确视觉反馈：光环、芯片、数字色一起变。"""
        accent = theme.CYAN if phase == Phase.FOCUS else theme.PURPLE
        glow = "#3322D3EE" if phase == Phase.FOCUS else "#33A78BFA"
        label = "FOCUS SESSION" if phase == Phase.FOCUS else "RECOVERY CYCLE"
        self.ring.color = accent
        self.time_text.color = theme.TEXT
        self.phase_chip.bgcolor = glow
        self.phase_chip.border = ft.Border.all(1, accent)
        chip_text = self.phase_chip.content
        if isinstance(chip_text, ft.Text):
            chip_text.value = label
            chip_text.color = accent

    def _sync_buttons(self) -> None:
        running = self.timer.running
        self.start_btn.disabled = running
        self.pause_btn.disabled = not running
        # 计时中不允许换模式，避免剩余秒数错位
        self.mode_dropdown.disabled = running

    def _refresh_mode_options(self, select_id: int) -> None:
        modes = self.db.list_modes()
        self.mode_dropdown.options = [
            ft.DropdownOption(
                key=str(m.id),
                text=f"{m.name}  ·  {m.focus_minutes}+{m.break_minutes}",
            )
            for m in modes
        ]
        self.mode_dropdown.value = str(select_id)

    # ------------------------------------------------------------------
    # 计时控制
    # ------------------------------------------------------------------
    def _on_start(self, e: ft.ControlEvent) -> None:
        self.timer.start(self.page.run_task)
        self._sync_buttons()
        self.status_hint.value = "NEURAL LINK ACTIVE"
        self.page.update()

    def _on_pause(self, e: ft.ControlEvent) -> None:
        self.timer.pause()
        self.refresh_tick()

    def _on_reset(self, e: ft.ControlEvent) -> None:
        self.timer.reset()
        self.refresh_tick()

    def _on_mode_select(self, e: ft.Event[ft.Dropdown]) -> None:
        if not e.control.value:
            return
        mode = self.db.get_mode(int(e.control.value))
        if mode is None:
            return
        self.on_mode_changed(mode)

    # ------------------------------------------------------------------
    # 模式管理对话框
    # ------------------------------------------------------------------
    def _open_mode_manager(self, e: ft.ControlEvent) -> None:
        """列出全部模式，支持新增 / 编辑 / 删除（内置模式不可删）。"""
        list_col = ft.Column(spacing=8, tight=True, scroll=ft.ScrollMode.AUTO, height=280)

        def rebuild_list() -> None:
            list_col.controls.clear()
            for mode in self.db.list_modes():
                list_col.controls.append(self._mode_tile(mode, rebuild_list, dialog))
            self.page.update()

        dialog = ft.AlertDialog(
            modal=True,
            bgcolor=theme.BG_ELEVATED,
            title=ft.Text("时间模式", color=theme.TEXT, weight=ft.FontWeight.W_600),
            content=ft.Container(width=360, content=list_col),
            actions=[
                ft.TextButton(
                    "新增模式",
                    on_click=lambda ev: self._open_editor_from_manager(None),
                ),
                ft.TextButton("关闭", on_click=lambda ev: self.page.pop_dialog()),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        rebuild_list()
        self.page.show_dialog(dialog)

    def _mode_tile(
        self,
        mode: TimerMode,
        rebuild_list: Callable[[], None],
        parent_dialog: ft.AlertDialog,
    ) -> ft.Control:
        badge = "内置" if mode.is_builtin else "自定义"
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=12,
            bgcolor=theme.SURFACE,
            border=ft.Border.all(1, theme.BORDER),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(mode.name, color=theme.TEXT, size=14, weight=ft.FontWeight.W_500),
                            ft.Text(
                                f"{mode.focus_minutes} 分钟专注  ·  {mode.break_minutes} 分钟休息  ·  {badge}",
                                color=theme.TEXT_MUTED,
                                size=11,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=0,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED,
                                icon_size=18,
                                icon_color=theme.TEXT_MUTED,
                                on_click=lambda e, m=mode: self._open_editor_from_manager(m),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_size=18,
                                icon_color=theme.MAGENTA if not mode.is_builtin else theme.TEXT_DIM,
                                disabled=mode.is_builtin,
                                tooltip="内置模式不可删除" if mode.is_builtin else "删除",
                                on_click=lambda e, m=mode: self._delete_mode(m, rebuild_list),
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _open_editor_from_manager(self, mode: Optional[TimerMode]) -> None:
        """先关掉列表对话框，再打开编辑器；保存/取消后重新打开列表。"""
        self.page.pop_dialog()
        self._open_mode_editor(mode, lambda: self._open_mode_manager(None))

    def _open_mode_editor(self, mode: Optional[TimerMode], on_saved: Callable[[], None]) -> None:
        name_field = ft.TextField(
            label="名称",
            value=mode.name if mode else "",
            color=theme.TEXT,
            border_color=theme.BORDER,
            focused_border_color=theme.CYAN,
            cursor_color=theme.CYAN,
        )
        focus_field = ft.TextField(
            label="专注（分钟）",
            value=str(mode.focus_minutes) if mode else "25",
            keyboard_type=ft.KeyboardType.NUMBER,
            color=theme.TEXT,
            border_color=theme.BORDER,
            focused_border_color=theme.CYAN,
            cursor_color=theme.CYAN,
        )
        break_field = ft.TextField(
            label="休息（分钟）",
            value=str(mode.break_minutes) if mode else "5",
            keyboard_type=ft.KeyboardType.NUMBER,
            color=theme.TEXT,
            border_color=theme.BORDER,
            focused_border_color=theme.CYAN,
            cursor_color=theme.CYAN,
        )
        error_text = ft.Text("", color=theme.MAGENTA, size=12)

        def save(ev: ft.ControlEvent) -> None:
            try:
                focus_m = int(str(focus_field.value or "0"))
                break_m = int(str(break_field.value or "0"))
                if mode is None:
                    created = self.db.add_mode(str(name_field.value or ""), focus_m, break_m)
                    self.reload_modes(select_id=created.id)
                    self.on_mode_changed(created)
                else:
                    self.db.update_mode(mode.id, str(name_field.value or ""), focus_m, break_m)
                    updated = self.db.get_mode(mode.id)
                    self.reload_modes(select_id=mode.id)
                    if updated and updated.id == self.timer.mode.id:
                        self.on_mode_changed(updated)
                self.page.pop_dialog()
                on_saved()
            except (TypeError, ValueError) as err:
                error_text.value = str(err) if str(err) else "请输入有效的整数分钟"
                self.page.update()

        editor = ft.AlertDialog(
            modal=True,
            bgcolor=theme.BG_ELEVATED,
            title=ft.Text("编辑模式" if mode else "新增模式", color=theme.TEXT),
            content=ft.Container(
                width=320,
                content=ft.Column(
                    spacing=12,
                    tight=True,
                    controls=[name_field, focus_field, break_field, error_text],
                ),
            ),
            actions=[
                ft.TextButton(
                    "取消",
                    on_click=lambda ev: (self.page.pop_dialog(), on_saved()),
                ),
                ft.Button(content="保存", on_click=save),
            ],
        )
        self.page.show_dialog(editor)

    def _delete_mode(self, mode: TimerMode, on_done: Callable[[], None]) -> None:
        ok = self.db.delete_mode(mode.id)
        if not ok:
            self.page.show_dialog(
                ft.SnackBar(content=ft.Text("无法删除：内置模式或只剩最后一个模式"))
            )
            return
        remaining = self.db.list_modes()
        if remaining and self.timer.mode.id == mode.id:
            self.reload_modes(select_id=remaining[0].id)
            self.on_mode_changed(remaining[0])
        else:
            self.reload_modes()
        on_done()
