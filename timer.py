"""
番茄钟状态机。

职责边界：
- 本模块只负责「还剩多少秒 / 当前是专注还是休息 / 该不该触发完成回调」
- 不碰 UI、不写数据库
- UI 通过回调拿到 tick / phase_change / cycle_complete 事件后再去刷新界面和落库

完成规则（与需求严格对齐）：
- 专注自然走完 → 记一次番茄（由 UI 写库）并切到休息，给视觉反馈，不播彩虹
- 休息自然走完 → 一个完整「专注+休息」周期结束，触发彩虹边框，再回到专注
- 用户暂停或重置 → 不写库、不播彩虹
"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Awaitable, Callable, Optional

from database import TimerMode


class Phase(str, Enum):
    FOCUS = "focus"
    BREAK = "break"


# 回调类型：UI 层注入，Timer 本身保持同步/异步均可。
TickCallback = Callable[[int, Phase], None]
PhaseCallback = Callable[[Phase], None]
CycleCallback = Callable[[], None]
FocusDoneCallback = Callable[[], None]


class PomodoroTimer:
    """
    单线程协作式计时器。

    使用 page.run_task 启动的 asyncio 循环每秒递减 remaining。
    这样可以跟 Flet 的事件循环待在一起，避免额外线程里直接 page.update()。
    """

    def __init__(self, mode: TimerMode) -> None:
        self.mode = mode
        self.phase: Phase = Phase.FOCUS
        self.remaining: int = mode.focus_minutes * 60
        self.running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None

        self.on_tick: Optional[TickCallback] = None
        self.on_phase_change: Optional[PhaseCallback] = None
        self.on_focus_complete: Optional[FocusDoneCallback] = None
        self.on_cycle_complete: Optional[CycleCallback] = None

    # ------------------------------------------------------------------
    # 只读辅助
    # ------------------------------------------------------------------
    @property
    def total_seconds(self) -> int:
        if self.phase == Phase.FOCUS:
            return self.mode.focus_minutes * 60
        return self.mode.break_minutes * 60

    @property
    def progress(self) -> float:
        """0.0–1.0，给 ProgressRing 用。倒计时越接近 0，进度越满。"""
        total = max(self.total_seconds, 1)
        elapsed = total - self.remaining
        return max(0.0, min(1.0, elapsed / total))

    @property
    def display(self) -> str:
        seconds = max(0, self.remaining)
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    @property
    def phase_label(self) -> str:
        return "深度链接中" if self.phase == Phase.FOCUS else "神经冷却"

    @property
    def phase_sublabel(self) -> str:
        if self.phase == Phase.FOCUS:
            return "FOCUS SESSION"
        return "RECOVERY CYCLE"

    # ------------------------------------------------------------------
    # 控制
    # ------------------------------------------------------------------
    def apply_mode(self, mode: TimerMode) -> None:
        """切换模式会强制重置，避免旧模式的剩余秒数套到新时长上。"""
        self.stop()
        self.mode = mode
        self.phase = Phase.FOCUS
        self.remaining = mode.focus_minutes * 60
        self._emit_tick()

    def start(self, runner: Callable) -> None:
        """
        runner 必须是 Flet Page.run_task（或任何能调度 coroutine 的函数）。
        重复点击开始是幂等的：已经在跑就直接返回。
        """
        if self.running:
            return
        self.running = True
        self._stop_event = asyncio.Event()
        self._task = runner(self._loop)

    def pause(self) -> None:
        self.running = False
        if self._stop_event is not None:
            self._stop_event.set()

    def stop(self) -> None:
        self.pause()

    def reset(self) -> None:
        """重置当前阶段到满时长。不切换阶段，也不视为完成。"""
        self.stop()
        self.remaining = self.total_seconds
        self._emit_tick()

    # ------------------------------------------------------------------
    # 内部循环
    # ------------------------------------------------------------------
    async def _loop(self) -> None:
        """
        每秒醒来一次。用 wait_for + Event 实现「暂停立刻打断 sleep」，
        否则用户点暂停后最多还要空等 1 秒才停。
        """
        try:
            while self.running:
                assert self._stop_event is not None
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=1.0)
                    # Event 被 set → 暂停，退出循环
                    break
                except asyncio.TimeoutError:
                    pass
                if not self.running:
                    break
                self.remaining -= 1
                if self.remaining <= 0:
                    self.remaining = 0
                    self._emit_tick()
                    self._advance_phase()
                    # 阶段切换后继续跑下一阶段，无需用户再点开始
                    continue
                self._emit_tick()
        finally:
            self.running = False

    def _advance_phase(self) -> None:
        """
        自然倒计时归零时的状态迁移。

        FOCUS → BREAK：一次番茄完成（写库），给阶段切换反馈
        BREAK → FOCUS：完整周期完成（彩虹动画），准备下一轮
        """
        if self.phase == Phase.FOCUS:
            if self.on_focus_complete:
                self.on_focus_complete()
            self.phase = Phase.BREAK
            self.remaining = self.mode.break_minutes * 60
            if self.on_phase_change:
                self.on_phase_change(self.phase)
        else:
            if self.on_cycle_complete:
                self.on_cycle_complete()
            self.phase = Phase.FOCUS
            self.remaining = self.mode.focus_minutes * 60
            if self.on_phase_change:
                self.on_phase_change(self.phase)
        self._emit_tick()

    def _emit_tick(self) -> None:
        if self.on_tick:
            self.on_tick(self.remaining, self.phase)
