"""Flags images that are unnecessarily large for the web — either a huge
file size outright, or pixel dimensions far beyond anything a browser would
ever display at (a 4000px-wide hero image served at 800px wide, etc).
Uses Pillow to read actual dimensions rather than guessing from file size
alone, so the finding is concrete ("3600x2400px, 4.2MB") not a vague guess.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image

# A generous ceiling — genuinely oversized for near enough any web layout,
# not a nitpick over reasonably-sized hero images.
_MAX_REASONABLE_WIDTH_PX = 2000
_MAX_REASONABLE_FILE_SIZE_BYTES = 500_000  # 500KB


@dataclass
class ImageFinding:
    url: str
    size_bytes: int
    width: int | None
    height: int | None
    is_oversized: bool
    reason: str | None


def analyze_image(image_bytes: bytes, *, url: str) -> ImageFinding:
    size_bytes = len(image_bytes)
    width: int | None = None
    height: int | None = None

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
    except Exception:  # noqa: BLE001 — not a decodable image (SVG, broken data, etc.); size check alone still applies
        pass

    reasons = []
    if size_bytes > _MAX_REASONABLE_FILE_SIZE_BYTES:
        reasons.append(f"{size_bytes // 1024}KB file size")
    if width and width > _MAX_REASONABLE_WIDTH_PX:
        reasons.append(f"{width}px wide (uncommonly large for web display)")

    return ImageFinding(
        url=url,
        size_bytes=size_bytes,
        width=width,
        height=height,
        is_oversized=bool(reasons),
        reason="; ".join(reasons) if reasons else None,
    )
