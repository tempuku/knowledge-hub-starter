#!/usr/bin/env python3
"""Deterministic PNG Home Screen icons for old iPads (stdlib only).

Icons are derived build artifacts: never generate per-project HTML or use
external image hosts. Avoids shipping binary sources in the OKF repository.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path


def chunk(name: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)


def color_at(x: int, y: int, size: int) -> tuple[int, int, int, int]:
    X = (x + 0.5) / size
    Y = (y + 0.5) / size
    radius = .17
    dx = max(radius - X, 0, X - (1 - radius))
    dy = max(radius - Y, 0, Y - (1 - radius))
    if dx * dx + dy * dy > radius * radius:
        return (0, 0, 0, 0)
    # iOS 5/6 glossy indigo icon with restrained reflection.
    t = Y
    red = int(92 * (1 - t) + 31 * t)
    green = int(145 * (1 - t) + 73 * t)
    blue = int(203 * (1 - t) + 135 * t)
    if Y < .49:
        shine = int(34 * (.49 - Y) / .49)
        red, green, blue = min(255, red + shine), min(255, green + shine), min(255, blue + shine)

    # Small drop shadow under an open-book silhouette.
    if .195 <= X <= .805 and .325 <= Y <= .78:
        if (.22 <= X <= .49 or .51 <= X <= .78) and .345 <= Y <= .735:
            return (246, 247, 239, 255)
        if .49 < X < .51 and .35 <= Y <= .74:
            return (215, 226, 246, 255)
    if .195 <= X <= .805 and .765 <= Y <= .785:
        return (17, 44, 80, 220)
    # Book-fold and two fine lines on the page.
    if .48 <= X <= .52 and .36 <= Y <= .73:
        return (159, 178, 204, 255)
    if .30 < X < .455 and .48 < Y < .492:
        return (192, 210, 229, 255)
    if .545 < X < .70 and .48 < Y < .492:
        return (192, 210, 229, 255)
    return (red, green, blue, 255)


def write_icon(path: Path, size: int) -> None:
    raw = bytearray()
    for y in range(size):
        raw.append(0)  # PNG filter: None
        for x in range(size):
            raw.extend(color_at(x, y, size))
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">2I5B", size, size, 8, 6, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    data += chunk(b"IEND", b"")
    path.write_bytes(data)


def write_icons(destination: Path) -> None:
    for size in (180, 192, 512):
        name = "apple-touch-icon.png" if size == 180 else f"icon-{size}.png"
        write_icon(destination / name, size)


if __name__ == "__main__":
    write_icons(Path(__file__).resolve().parents[2] / "dist")
