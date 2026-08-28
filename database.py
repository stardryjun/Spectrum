"""
Spectrum 本地数据层。

使用标准库 sqlite3（无需额外依赖）持久化两类数据：
1. 自定义番茄钟模式（名称、专注分钟、休息分钟）
2. 每一次「专注」完成记录（时间戳 + 时长），供历史页统计与热图使用

数据库文件默认放在用户主目录下的 ~/.spectrum/spectrum.db，
这样无论用 `python main.py` 还是打包后的可执行文件，数据都不会丢。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class TimerMode:
    """一条可切换的计时模式。is_builtin=True 的内置模式不允许删除。"""

    id: int
    name: str
    focus_minutes: int
    break_minutes: int
    is_builtin: bool = False


@dataclass
class SessionRecord:
    """一次已完成的专注番茄。"""

    id: int
    completed_at: datetime
    mode_name: str
    focus_minutes: int


@dataclass
class StatsSummary:
    """历史页顶部四张摘要卡片所需的聚合数据。"""

    today: int
    week: int
    month: int
    total: int
    total_focus_minutes: int

    @property
    def total_hours_label(self) -> str:
        hours = self.total_focus_minutes / 60.0
        if hours < 10:
            return f"{hours:.1f} 小时"
        return f"{int(round(hours))} 小时"


class Database:
    """封装全部 SQLite 读写。UI 层只通过这个类访问数据，不直接写 SQL。"""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.path = db_path or self._default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False：Flet 的回调可能来自不同线程，避免误报。
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        self._seed_builtin_modes()

    @staticmethod
    def _default_path() -> Path:
        return Path.home() / ".spectrum" / "spectrum.db"

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        """创建表。IF NOT EXISTS 保证重复启动安全。"""
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS modes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                focus_minutes INTEGER NOT NULL,
                break_minutes INTEGER NOT NULL,
                is_builtin INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                completed_at TEXT NOT NULL,
                mode_name TEXT NOT NULL,
                focus_minutes INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_completed_at
                ON sessions (completed_at);
            """
        )
        self._conn.commit()

    def _seed_builtin_modes(self) -> None:
        """
        首次启动写入两条内置模式：
        - 经典番茄：25 + 5
        - 深度专注：50 + 10
        已存在则跳过，避免覆盖用户改名后的数据。
        """
        cur = self._conn.cursor()
        count = cur.execute("SELECT COUNT(*) FROM modes").fetchone()[0]
        if count > 0:
            return
        cur.executemany(
            """
            INSERT INTO modes (name, focus_minutes, break_minutes, is_builtin)
            VALUES (?, ?, ?, 1)
            """,
            [
                ("经典番茄", 25, 5),
                ("深度专注", 50, 10),
            ],
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # 模式 CRUD
    # ------------------------------------------------------------------
    def list_modes(self) -> List[TimerMode]:
        rows = self._conn.execute(
            "SELECT id, name, focus_minutes, break_minutes, is_builtin "
            "FROM modes ORDER BY is_builtin DESC, id ASC"
        ).fetchall()
        return [self._row_to_mode(r) for r in rows]

    def get_mode(self, mode_id: int) -> Optional[TimerMode]:
        row = self._conn.execute(
            "SELECT id, name, focus_minutes, break_minutes, is_builtin "
            "FROM modes WHERE id = ?",
            (mode_id,),
        ).fetchone()
        return self._row_to_mode(row) if row else None

    def add_mode(self, name: str, focus_minutes: int, break_minutes: int) -> TimerMode:
        self._validate_mode(name, focus_minutes, break_minutes)
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO modes (name, focus_minutes, break_minutes, is_builtin)
            VALUES (?, ?, ?, 0)
            """,
            (name.strip(), int(focus_minutes), int(break_minutes)),
        )
        self._conn.commit()
        mode = self.get_mode(cur.lastrowid)
        assert mode is not None
        return mode

    def update_mode(
        self, mode_id: int, name: str, focus_minutes: int, break_minutes: int
    ) -> None:
        self._validate_mode(name, focus_minutes, break_minutes)
        self._conn.execute(
            """
            UPDATE modes
            SET name = ?, focus_minutes = ?, break_minutes = ?
            WHERE id = ?
            """,
            (name.strip(), int(focus_minutes), int(break_minutes), mode_id),
        )
        self._conn.commit()

    def delete_mode(self, mode_id: int) -> bool:
        """删除自定义模式。内置模式拒绝删除，返回 False。"""
        row = self._conn.execute(
            "SELECT is_builtin FROM modes WHERE id = ?", (mode_id,)
        ).fetchone()
        if row is None or int(row["is_builtin"]) == 1:
            return False
        remaining = self._conn.execute("SELECT COUNT(*) FROM modes").fetchone()[0]
        if remaining <= 1:
            return False
        self._conn.execute("DELETE FROM modes WHERE id = ?", (mode_id,))
        self._conn.commit()
        return True

    @staticmethod
    def _validate_mode(name: str, focus_minutes: int, break_minutes: int) -> None:
        if not name or not name.strip():
            raise ValueError("模式名称不能为空")
        if int(focus_minutes) < 1 or int(focus_minutes) > 180:
            raise ValueError("专注时长需在 1–180 分钟之间")
        if int(break_minutes) < 1 or int(break_minutes) > 60:
            raise ValueError("休息时长需在 1–60 分钟之间")

    @staticmethod
    def _row_to_mode(row: sqlite3.Row) -> TimerMode:
        return TimerMode(
            id=int(row["id"]),
            name=str(row["name"]),
            focus_minutes=int(row["focus_minutes"]),
            break_minutes=int(row["break_minutes"]),
            is_builtin=bool(row["is_builtin"]),
        )

    # ------------------------------------------------------------------
    # 专注记录
    # ------------------------------------------------------------------
    def add_session(self, mode_name: str, focus_minutes: int, when: Optional[datetime] = None) -> None:
        """
        写入一条「专注完成」记录。

        只在专注阶段自然走完时调用；暂停 / 重置不会走到这里，
        因此彩虹动画与历史统计都不会被手动中断污染。
        """
        ts = (when or datetime.now()).isoformat(timespec="seconds")
        self._conn.execute(
            """
            INSERT INTO sessions (completed_at, mode_name, focus_minutes)
            VALUES (?, ?, ?)
            """,
            (ts, mode_name, int(focus_minutes)),
        )
        self._conn.commit()

    def list_sessions(self, limit: int = 500) -> List[SessionRecord]:
        rows = self._conn.execute(
            """
            SELECT id, completed_at, mode_name, focus_minutes
            FROM sessions
            ORDER BY completed_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_session(r) for r in rows]

    def sessions_grouped_by_date(self, limit: int = 500) -> List[Tuple[str, List[SessionRecord]]]:
        """按日期（本地 YYYY-MM-DD）分组，供历史列表渲染。"""
        groups: Dict[str, List[SessionRecord]] = {}
        order: List[str] = []
        for rec in self.list_sessions(limit=limit):
            key = rec.completed_at.strftime("%Y-%m-%d")
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(rec)
        return [(k, groups[k]) for k in order]

    def daily_counts(self, days: int = 371) -> Dict[str, int]:
        """
        返回 {YYYY-MM-DD: 完成数}，覆盖最近 `days` 天。
        371 ≈ 53 周，刚好铺满一张 GitHub 风格年历热图。
        """
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = self._conn.execute(
            """
            SELECT substr(completed_at, 1, 10) AS day, COUNT(*) AS n
            FROM sessions
            WHERE substr(completed_at, 1, 10) >= ?
            GROUP BY day
            """,
            (since,),
        ).fetchall()
        return {str(r["day"]): int(r["n"]) for r in rows}

    def get_stats(self) -> StatsSummary:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        # 本周从周一起算（ISO），与多数生产力工具一致。
        week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        month_start = now.strftime("%Y-%m-01")

        def _count_since(day: str) -> int:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE substr(completed_at, 1, 10) >= ?",
                (day,),
            ).fetchone()
            return int(row[0])

        today_n = self._conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE substr(completed_at, 1, 10) = ?",
            (today,),
        ).fetchone()[0]
        total_row = self._conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(focus_minutes), 0) FROM sessions"
        ).fetchone()
        return StatsSummary(
            today=int(today_n),
            week=_count_since(week_start),
            month=_count_since(month_start),
            total=int(total_row[0]),
            total_focus_minutes=int(total_row[1]),
        )

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> SessionRecord:
        raw = str(row["completed_at"])
        try:
            when = datetime.fromisoformat(raw)
        except ValueError:
            when = datetime.now()
        return SessionRecord(
            id=int(row["id"]),
            completed_at=when,
            mode_name=str(row["mode_name"]),
            focus_minutes=int(row["focus_minutes"]),
        )
