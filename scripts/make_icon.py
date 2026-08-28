#!/usr/bin/env python3
"""Generate assets/icon.png — a 1024×1024 Spectrum mark (stdlib only)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE = 1024


def _pixel(x: int, y: int) -> tuple[int, int, int, int]:
    cx = cy = (SIZE - 1) / 2.0
    dx = x - cx
    dy = y - cy
    r = (dx * dx + dy * dy) ** 0.5
    max_r = SIZE * 0.48

    # Deep navy canvas
    bg = (7, 11, 20)
    if r > max_r:
        return (*bg, 255)

    # Soft inner glow
    t = r / max_r
    ring = abs(t - 0.72)
    glow = max(0.0, 1.0 - ring / 0.18)
    core = max(0.0, 1.0 - t / 0.55)

    # Cyan → purple sweep around the ring
    ang = (dx / (r + 1e-6) + 1) * 0.5
    cyan = (34, 211, 238)
    purple = (167, 139, 250)
    mix = ang
    ring_c = (
        int(cyan[0] * (1 - mix) + purple[0] * mix),
        int(cyan[1] * (1 - mix) + purple[1] * mix),
        int(cyan[2] * (1 - mix) + purple[2] * mix),
    )
    rr = int(bg[0] + (ring_c[0] - bg[0]) * glow + 18 * core)
    gg = int(bg[1] + (ring_c[1] - bg[1]) * glow + 40 * core)
    bb = int(bg[2] + (ring_c[2] - bg[2]) * glow + 70 * core)
    return (min(255, rr), min(255, gg), min(255, bb), 255)


def _png(pixels: bytes, width: int, height: int) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw.extend(pixels[y * stride : (y + 1) * stride])
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk(b"IHDR", ihdr),
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)),
            chunk(b"IEND", b""),
        ]
    )


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    buf = bytearray(SIZE * SIZE * 4)
    i = 0
    for y in range(SIZE):
        for x in range(SIZE):
            r, g, b, a = _pixel(x, y)
            buf[i : i + 4] = (r, g, b, a)
            i += 4
    out.write_bytes(_png(bytes(buf), SIZE, SIZE))
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
