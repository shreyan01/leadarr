from __future__ import annotations

import httpx
import pytest

from app.services.validation.validation_service import WebsiteValidationService


class TestNormalize:
    def test_adds_https_when_missing_scheme(self):
        assert WebsiteValidationService._normalize("example.com") == "https://example.com"

    def test_keeps_explicit_http_scheme(self):
        assert WebsiteValidationService._normalize("http://example.com") == "http://example.com"

    def test_returns_none_for_empty_string(self):
        assert WebsiteValidationService._normalize("   ") is None

    def test_returns_none_when_no_hostname(self):
        assert WebsiteValidationService._normalize("https:///path-only") is None


class TestDetectTechnologies:
    def test_detects_wordpress_from_generator_meta(self):
        html = '<meta name="generator" content="WordPress 6.4" />'
        detected = WebsiteValidationService._detect_technologies(html, httpx.Headers({}))
        assert "WordPress" in detected

    def test_detects_shopify_from_cdn_reference(self):
        html = '<script src="https://cdn.shopify.com/s/files/1/theme.js"></script>'
        detected = WebsiteValidationService._detect_technologies(html, httpx.Headers({}))
        assert "Shopify" in detected

    def test_includes_x_powered_by_header(self):
        detected = WebsiteValidationService._detect_technologies("<html></html>", httpx.Headers({"x-powered-by": "PHP/8.2"}))
        assert any("X-Powered-By" in d for d in detected)

    def test_no_false_positive_on_plain_html(self):
        detected = WebsiteValidationService._detect_technologies("<html><body>Hello</body></html>", httpx.Headers({}))
        assert detected == []
