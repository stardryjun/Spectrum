"""
Spectrum — 跨平台 AI 风格番茄钟。

入口职责：
- 装配 Page 主题、窗口、导航
- 把 Database / PomodoroTimer / HomeView / HistoryView 焊在一起
- 实现「完整专注+休息周期完成」时的彩虹边框全屏动画
- 专注自然结束时写入 SQLite（暂停/重置不写）
"""

from __future__ import annotations

import asyncio
from typing import List

import flet as ft

import theme
from database import Database, TimerMode
from timer import Phase, PomodoroTimer
from ui.history import HistoryView
from ui.home import HomeView


# 彩虹动画时长（秒）。需求要求 3–5 秒，取中位偏长一点更有「被唤醒」的仪式感。
RAINBOW_SECONDS = 4.2
RAINBOW_FRAMES = 28


def main(page: ft.Page) -> None:
    page.title = "Spectrum"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = theme.BG
    page.padding = 0
    page.theme = ft.Theme(color_scheme_seed=theme.CYAN)
    # 桌面窗口：竖屏手机比例，方便同时预览移动端布局。
    page.window.width = 430
    page.window.height = 860
    page.window.min_width = 380
    page.window.min_height = 700
    page.window.bgcolor = theme.BG

    db = Database()
    modes = db.list_modes()
    timer = PomodoroTimer(modes[0])

    # ------------------------------------------------------------------
    # 彩虹边框 overlay
    # 四条渐变边贴在 Stack 最上层，默认透明。周期完成时扫过光谱色。
    # ignore_interactions=True 保证动画不会挡住按钮点击。
    # ------------------------------------------------------------------
    def _edge(width=None, height=None, begin=None, end=None, **pos) -> ft.Container:
        """屏幕四边的霓虹光条。pos 传入 top/left/right/bottom 以便在 Stack 里贴边。"""
        return ft.Container(
            width=width,
            height=height,
            gradient=ft.LinearGradient(
                begin=begin or ft.Alignment(-1, 0),
                end=end or ft.Alignment(1, 0),
                colors=theme.RAINBOW,
            ),
            shadow=ft.BoxShadow(blur_radius=32, spread_radius=4, color="#66FFFFFF"),
            **pos,
        )

    top_edge = _edge(height=6, begin=ft.Alignment(-1, 0), end=ft.Alignment(1, 0), top=0, left=0, right=0)
    bottom_edge = _edge(height=6, begin=ft.Alignment(1, 0), end=ft.Alignment(-1, 0), bottom=0, left=0, right=0)
    left_edge = _edge(width=6, begin=ft.Alignment(0, -1), end=ft.Alignment(0, 1), top=0, bottom=0, left=0)
    right_edge = _edge(width=6, begin=ft.Alignment(0, 1), end=ft.Alignment(0, -1), top=0, bottom=0, right=0)

    rainbow_frame = ft.Container(
        left=0,
        top=0,
        right=0,
        bottom=0,
        visible=False,
        opacity=0,
        ignore_interactions=True,
        content=ft.Stack(
            expand=True,
            controls=[top_edge, bottom_edge, left_edge, right_edge],
        ),
    )

    async def play_rainbow() -> None:
        """
        完整「专注 + 休息」周期自然走完时触发。

        实现思路：旋转 RAINBOW 色表，每帧赋给四条边的 LinearGradient，
        同时把 overlay 透明度拉到 1，持续约 4 秒后淡出。
        手动暂停 / 重置不会调用本函数。
        """
        rainbow_frame.visible = True
        rainbow_frame.opacity = 1
        page.update()
        colors: List[str] = list(theme.RAINBOW)
        steps = RAINBOW_FRAMES
        interval = RAINBOW_SECONDS / steps
        for i in range(steps):
            # 每次把最后一个颜色挪到最前，形成沿边缘流动的光谱。
            colors = colors[-1:] + colors[:-1]
            grad_h = ft.LinearGradient(
                begin=ft.Alignment(-1, 0),
                end=ft.Alignment(1, 0),
                colors=list(colors),
            )
            grad_h_rev = ft.LinearGradient(
                begin=ft.Alignment(1, 0),
                end=ft.Alignment(-1, 0),
                colors=list(colors),
            )
            grad_v = ft.LinearGradient(
                begin=ft.Alignment(0, -1),
                end=ft.Alignment(0, 1),
                colors=list(colors),
            )
            grad_v_rev = ft.LinearGradient(
                begin=ft.Alignment(0, 1),
                end=ft.Alignment(0, -1),
                colors=list(colors),
            )
            top_edge.gradient = grad_h
            bottom_edge.gradient = grad_h_rev
            left_edge.gradient = grad_v
            right_edge.gradient = grad_v_rev
            # 后半段开始降低透明度，结束时优雅消失。
            if i > steps * 0.65:
                t = (i - steps * 0.65) / (steps * 0.35)
                rainbow_frame.opacity = max(0.0, 1.0 - t)
            page.update()
            await asyncio.sleep(interval)
        rainbow_frame.opacity = 0
        rainbow_frame.visible = False
        page.update()

    # ------------------------------------------------------------------
    # 视图
    # ------------------------------------------------------------------
    def apply_mode(mode: TimerMode) -> None:
        timer.apply_mode(mode)
        home.refresh_phase(timer.phase)

    home = HomeView(page, db, timer, on_mode_changed=apply_mode)
    history = HistoryView(page, db)

    home_slot = ft.Container(expand=True, visible=True, content=home.root)
    history_slot = ft.Container(expand=True, visible=False, content=history.root)

    def on_nav_change(e: ft.ControlEvent) -> None:
        idx = getattr(e.control, "selected_index", 0) or 0
        home_slot.visible = idx == 0
        history_slot.visible = idx == 1
        if idx == 1:
            history.refresh()
        page.update()

    page.navigation_bar = ft.NavigationBar(
        bgcolor="#CC070B14",
        indicator_color="#3322D3EE",
        shadow_color="#00000000",
        selected_index=0,
        on_change=on_nav_change,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.BOLT_OUTLINED,
                selected_icon=ft.Icons.BOLT_ROUNDED,
                label="专注",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.AUTO_GRAPH_OUTLINED,
                selected_icon=ft.Icons.AUTO_GRAPH,
                label="历史",
            ),
        ],
    )

    # ------------------------------------------------------------------
    # Timer → UI / DB
    # ------------------------------------------------------------------
    def on_tick(remaining: int, phase: Phase) -> None:
        home.refresh_tick()

    def on_phase_change(phase: Phase) -> None:
        home.refresh_phase(phase)

    def on_focus_complete() -> None:
        """专注阶段自然走完：落库。暂停/重置不会进入这里。"""
        db.add_session(timer.mode.name, timer.mode.focus_minutes)

    def on_cycle_complete() -> None:
        """休息也自然走完：一个番茄周期闭环，触发彩虹。"""
        page.run_task(play_rainbow)

    timer.on_tick = on_tick
    timer.on_phase_change = on_phase_change
    timer.on_focus_complete = on_focus_complete
    timer.on_cycle_complete = on_cycle_complete

    def on_close(e: ft.ControlEvent) -> None:
        timer.stop()
        db.close()

    page.on_close = on_close

    # 背景：深色径向光斑，给「AI 控制台」一点空间纵深。
    backdrop = ft.Container(
        expand=True,
        gradient=ft.RadialGradient(
            center=ft.Alignment(0, -0.6),
            radius=1.2,
            colors=["#1A155E75", theme.BG],
        ),
    )

    # 彩虹边框挂在 overlay，才能盖住导航栏，真正贴满窗口四边。
    page.overlay.append(rainbow_frame)

    page.add(
        ft.Stack(
            expand=True,
            controls=[
                backdrop,
                ft.SafeArea(
                    expand=True,
                    content=ft.Stack(
                        expand=True,
                        controls=[home_slot, history_slot],
                    ),
                ),
            ],
        )
    )


if __name__ == "__main__":
    ft.run(main)
