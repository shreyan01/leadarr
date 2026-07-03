"""WCAG 2.x relative luminance / contrast ratio calculation.

Reference: https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
Pure math — no dependency on rendering — used to flag inline-styled text
that falls below the WCAG AA threshold (4.5:1 for normal text).
"""
from __future__ import annotations


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return r / 255.0, g / 255.0, b / 255.0


def _channel_luminance(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    r, g, b = _channel_luminance(r), _channel_luminance(g), _channel_luminance(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    l1 = relative_luminance(hex_a)
    l2 = relative_luminance(hex_b)
    lighter, darker = max(l1, l2), min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def meets_wcag_aa(hex_foreground: str, hex_background: str, *, large_text: bool = False) -> bool:
    threshold = 3.0 if large_text else 4.5
    return contrast_ratio(hex_foreground, hex_background) >= threshold
