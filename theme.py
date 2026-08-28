"""
Spectrum 视觉设计令牌。

整体风格刻意贴近市面上的 AI 客户端（深色画布、青紫霓虹、毛玻璃卡片），
并混入 GitHub 贡献图那种克制的网格美学。所有颜色集中在此文件，
后续换肤或微调只需要改这一处。
"""

# ---------------------------------------------------------------------------
# 基础色板
# ---------------------------------------------------------------------------
BG = "#070B14"  # 近黑海军蓝，作为整页底色
BG_ELEVATED = "#0E1524"  # 卡片背后的第二层深色
SURFACE = "#14FFFFFF"  # 半透明白，配合 blur 形成毛玻璃
SURFACE_STRONG = "#1FFFFFFF"
BORDER = "#22FFFFFF"
BORDER_GLOW = "#3340F8FF"

TEXT = "#E8EEF7"
TEXT_MUTED = "#8B9BB4"
TEXT_DIM = "#5C6B82"

# 专注态：电光青；休息态：柔和紫。切换阶段时用这两种颜色制造明确反馈。
CYAN = "#22D3EE"
CYAN_DIM = "#0891B2"
CYAN_GLOW = "#6622D3EE"
PURPLE = "#A78BFA"
PURPLE_DIM = "#7C3AED"
PURPLE_GLOW = "#66A78BFA"
MAGENTA = "#F472B6"
AMBER = "#FBBF24"
GREEN = "#34D399"

# GitHub 风格热图（科技感青绿色阶，空格子接近 GitHub 深色空单元）
HEAT_EMPTY = "#161B22"
HEAT_LEVELS = [
    "#161B22",  # 0
    "#0E3A4A",  # 1
    "#155E75",  # 2–3
    "#0891B2",  # 4–6
    "#22D3EE",  # 7+
]

# 彩虹边框动画用的光谱色，模拟「AI 被唤醒」时的霓虹扫光
RAINBOW = [
    "#FF006E",
    "#FB5607",
    "#FFBE0B",
    "#06D6A0",
    "#3A86FF",
    "#8338EC",
    "#F72585",
]


def heat_color(count: int) -> str:
    """
    根据当天完成的番茄数映射热图颜色。

    分档参考 GitHub 贡献图的 5 档思路，但阈值按番茄钟密度下调：
    0 / 1 / 2-3 / 4-6 / 7+。
    """
    if count <= 0:
        return HEAT_LEVELS[0]
    if count == 1:
        return HEAT_LEVELS[1]
    if count <= 3:
        return HEAT_LEVELS[2]
    if count <= 6:
        return HEAT_LEVELS[3]
    return HEAT_LEVELS[4]


def hex_with_alpha(hex_color: str, alpha_hex: str = "FF") -> str:
    """把 #RRGGBB 转成 #AARRGGBB，方便做半透明描边/阴影。"""
    raw = hex_color.lstrip("#")
    if len(raw) == 6:
        return f"#{alpha_hex}{raw}"
    return hex_color
