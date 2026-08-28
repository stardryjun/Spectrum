"""
历史记录与统计界面。

布局严格按需求分三层：
1. 顶部：今日 / 本周 / 本月 / 总时长 摘要卡片
2. 中部：GitHub 风格贡献日历热图（Flet 原生方块，不依赖 matplotlib）
3. 底部：按日期分组的可滚动记录列表

热图选择原生控件而不是 WebView / 静态图，是为了：
- 移动端打包无需捆绑浏览器或 matplotlib 的 mpl-data
- 主题色能直接跟 AI 深色界面统一
- 点击方块可以立刻在下方列表里对上同一天
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional

import flet as ft

import theme
from database import Database, SessionRecord


WEEKDAY_LABELS = ["一", "二", "三", "四", "五", "六", "日"]
MONTH_LABELS = ["", "1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]

# 热图格子尺寸。桌面端 12px 接近 GitHub；窄屏会在 build 时按宽度再压缩。
CELL = 11
GAP = 3
WEEKS = 53


class HistoryView:
    def __init__(self, page: ft.Page, db: Database) -> None:
        self.page = page
        self.db = db
        self.stats_row = ft.ResponsiveRow(spacing=10, run_spacing=10)
        self.heatmap_host = ft.Container()
        self.legend = self._build_legend()
        self.list_host = ft.Column(spacing=10, expand=True, scroll=ft.ScrollMode.AUTO)
        self.empty_hint = ft.Text(
            "还没有完成的番茄。跑完一个专注周期后会出现在这里。",
            color=theme.TEXT_MUTED,
            size=13,
            text_align=ft.TextAlign.CENTER,
        )
        self.root = self._build()

    def _build(self) -> ft.Control:
        return ft.Container(
            expand=True,
            padding=ft.Padding.symmetric(horizontal=20, vertical=12),
            content=ft.Column(
                expand=True,
                spacing=16,
                controls=[
                    ft.Text("历史信号", size=20, weight=ft.FontWeight.W_600, color=theme.TEXT),
                    ft.Text(
                        "每一次专注都被记录成光谱上的一个脉冲。",
                        size=12,
                        color=theme.TEXT_MUTED,
                    ),
                    self.stats_row,
                    self._glass(
                        ft.Column(
                            spacing=10,
                            tight=True,
                            controls=[
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    controls=[
                                        ft.Text("贡献日历", size=13, color=theme.TEXT, weight=ft.FontWeight.W_500),
                                        self.legend,
                                    ],
                                ),
                                ft.Row(
                                    scroll=ft.ScrollMode.AUTO,
                                    controls=[self.heatmap_host],
                                ),
                            ],
                        ),
                        padding=ft.Padding.all(14),
                    ),
                    ft.Text("按日归档", size=13, color=theme.TEXT_MUTED, weight=ft.FontWeight.W_500),
                    self.list_host,
                ],
            ),
        )

    def refresh(self) -> None:
        """每次切到历史 Tab 时调用，重新读库。"""
        stats = self.db.get_stats()
        self.stats_row.controls = [
            self._stat_card("今日", f"{stats.today}", "个番茄"),
            self._stat_card("本周", f"{stats.week}", "个番茄"),
            self._stat_card("本月", f"{stats.month}", "个番茄"),
            self._stat_card("总专注", stats.total_hours_label, f"{stats.total} 次"),
        ]
        counts = self.db.daily_counts(days=WEEKS * 7)
        self.heatmap_host.content = self._build_heatmap(counts)
        self._rebuild_list()
        self.page.update()

    # ------------------------------------------------------------------
    # 摘要卡片
    # ------------------------------------------------------------------
    def _stat_card(self, label: str, value: str, hint: str) -> ft.Control:
        return ft.Container(
            col={"xs": 6, "sm": 3},
            padding=ft.Padding.all(14),
            border_radius=16,
            bgcolor=theme.SURFACE,
            blur=ft.Blur(16, 16, ft.BlurTileMode.CLAMP),
            border=ft.Border.all(1, theme.BORDER),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text(label, size=11, color=theme.TEXT_MUTED),
                    ft.Text(value, size=22, weight=ft.FontWeight.W_600, color=theme.TEXT),
                    ft.Text(hint, size=10, color=theme.TEXT_DIM),
                ],
            ),
        )

    # ------------------------------------------------------------------
    # GitHub 风格热图
    # ------------------------------------------------------------------
    def _build_heatmap(self, counts: Dict[str, int]) -> ft.Control:
        """
        构造 7 行 × 53 列的日历矩阵。

        列 = 一周（周一到周日，符合中文习惯；GitHub 原版是周日开头，
        若要改回只需把 weekday 映射对调）。
        今天之后的格子透明，避免「未来贡献」的错觉。
        """
        today = date.today()
        this_monday = today - timedelta(days=today.weekday())
        start = this_monday - timedelta(weeks=WEEKS - 1)

        month_row: List[ft.Control] = [ft.Container(width=18)]  # 给星期标签留空
        last_month: Optional[int] = None
        columns: List[ft.Control] = []

        cursor = start
        week_index = 0
        while cursor <= this_monday:
            # 月份标签：只在该周包含某月 1 号、或本列是新年第一周时画一次
            month_here = None
            for d in range(7):
                day = cursor + timedelta(days=d)
                if day.day == 1:
                    month_here = day.month
                    break
            if week_index == 0:
                month_here = start.month
            if month_here is not None and month_here != last_month:
                month_row.append(
                    ft.Container(
                        width=CELL + GAP,
                        content=ft.Text(MONTH_LABELS[month_here], size=9, color=theme.TEXT_DIM),
                    )
                )
                last_month = month_here
            else:
                month_row.append(ft.Container(width=CELL + GAP))

            cells: List[ft.Control] = []
            for weekday in range(7):
                day = cursor + timedelta(days=weekday)
                key = day.isoformat()
                if day > today:
                    cells.append(ft.Container(width=CELL, height=CELL))
                    continue
                n = counts.get(key, 0)
                color = theme.heat_color(n)
                is_today = day == today
                cells.append(
                    ft.Container(
                        width=CELL,
                        height=CELL,
                        border_radius=2,
                        bgcolor=color,
                        border=ft.Border.all(1, theme.CYAN) if is_today else None,
                        tooltip=f"{key}  ·  {n} 个番茄",
                    )
                )
            columns.append(
                ft.Column(spacing=GAP, controls=cells, tight=True)
            )
            cursor += timedelta(weeks=1)
            week_index += 1

        weekday_col = ft.Column(
            spacing=GAP,
            tight=True,
            controls=[
                ft.Container(
                    width=18,
                    height=CELL,
                    content=ft.Text(lab, size=8, color=theme.TEXT_DIM),
                )
                for lab in WEEKDAY_LABELS
            ],
        )
        grid = ft.Row(spacing=GAP, tight=True, controls=columns)
        return ft.Column(
            spacing=6,
            tight=True,
            controls=[
                ft.Row(spacing=0, tight=True, controls=month_row),
                ft.Row(
                    spacing=6,
                    tight=True,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[weekday_col, grid],
                ),
            ],
        )

    def _build_legend(self) -> ft.Control:
        cells = [
            ft.Container(width=10, height=10, border_radius=2, bgcolor=c)
            for c in theme.HEAT_LEVELS
        ]
        return ft.Row(
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("少", size=9, color=theme.TEXT_DIM),
                *cells,
                ft.Text("多", size=9, color=theme.TEXT_DIM),
            ],
        )

    # ------------------------------------------------------------------
    # 按日分组列表
    # ------------------------------------------------------------------
    def _rebuild_list(self) -> None:
        self.list_host.controls.clear()
        groups = self.db.sessions_grouped_by_date()
        if not groups:
            self.list_host.controls.append(
                ft.Container(
                    padding=30,
                    alignment=ft.Alignment.CENTER,
                    content=self.empty_hint,
                )
            )
            return
        for day, records in groups:
            self.list_host.controls.append(self._day_group(day, records))

    def _day_group(self, day: str, records: List[SessionRecord]) -> ft.Control:
        total_min = sum(r.focus_minutes for r in records)
        header = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text(self._pretty_date(day), color=theme.TEXT, size=13, weight=ft.FontWeight.W_500),
                ft.Text(f"{len(records)} 个 · {total_min} 分钟", color=theme.TEXT_MUTED, size=11),
            ],
        )
        tiles = [self._record_tile(r) for r in records]
        return ft.Column(spacing=6, tight=True, controls=[header, *tiles])

    def _record_tile(self, rec: SessionRecord) -> ft.Control:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=12,
            bgcolor=theme.SURFACE,
            border=ft.Border.all(1, theme.BORDER),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.Container(
                                width=8,
                                height=8,
                                border_radius=8,
                                bgcolor=theme.CYAN,
                                shadow=ft.BoxShadow(blur_radius=8, color=theme.CYAN_GLOW),
                            ),
                            ft.Text(rec.mode_name, color=theme.TEXT, size=13),
                        ],
                    ),
                    ft.Text(
                        f"{rec.completed_at.strftime('%H:%M')}  ·  {rec.focus_minutes} min",
                        color=theme.TEXT_MUTED,
                        size=12,
                    ),
                ],
            ),
        )

    @staticmethod
    def _pretty_date(iso_day: str) -> str:
        try:
            d = date.fromisoformat(iso_day)
        except ValueError:
            return iso_day
        today = date.today()
        if d == today:
            return "今天"
        if d == today - timedelta(days=1):
            return "昨天"
        return d.strftime("%Y年%m月%d日")

    def _glass(self, content: ft.Control, padding: Optional[ft.Padding] = None) -> ft.Container:
        return ft.Container(
            content=content,
            padding=padding or ft.Padding.all(16),
            border_radius=18,
            bgcolor=theme.SURFACE,
            blur=ft.Blur(18, 18, ft.BlurTileMode.CLAMP),
            border=ft.Border.all(1, theme.BORDER),
        )
