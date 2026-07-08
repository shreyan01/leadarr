from __future__ import annotations

import io

from PIL import Image

from app.services.technical.image_analyzer import analyze_image


def _make_image_bytes(width: int, height: int, *, fmt: str = "PNG") -> bytes:
    img = Image.new("RGB", (width, height), color=(120, 120, 120))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


class TestAnalyzeImage:
    def test_small_image_is_not_oversized(self):
        data = _make_image_bytes(200, 150)
        result = analyze_image(data, url="https://example.com/small.png")
        assert result.width == 200
        assert result.height == 150
        assert result.is_oversized is False
        assert result.reason is None

    def test_wide_image_flagged_oversized_by_dimensions(self):
        data = _make_image_bytes(3000, 1500)
        result = analyze_image(data, url="https://example.com/hero.png")
        assert result.is_oversized is True
        assert "wide" in result.reason

    def test_reports_correct_size_bytes(self):
        data = _make_image_bytes(100, 100)
        result = analyze_image(data, url="https://example.com/tiny.png")
        assert result.size_bytes == len(data)

    def test_undecodable_bytes_still_returns_size_only(self):
        result = analyze_image(b"not a real image", url="https://example.com/broken.png")
        assert result.width is None
        assert result.height is None
        assert result.size_bytes == len(b"not a real image")