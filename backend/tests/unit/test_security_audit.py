from __future__ import annotations

from app.services.accessibility.contrast import contrast_ratio, meets_wcag_aa
from app.services.security_audit.header_analyzer import (
    analyze_cookie,
    analyze_headers,
    compute_hygiene_score,
    detect_mixed_content,
)
from app.services.security_audit.secret_scanner import scan_for_public_api_endpoints, scan_for_secrets


class TestAnalyzeHeaders:
    def test_detects_missing_security_headers(self):
        findings = analyze_headers({"Server": "nginx"})
        assert findings.hsts is False
        assert findings.csp is None
        assert findings.server_header == "nginx"

    def test_detects_present_security_headers_case_insensitively(self):
        findings = analyze_headers(
            {
                "Strict-Transport-Security": "max-age=31536000",
                "Content-Security-Policy": "default-src 'self'",
                "X-Frame-Options": "DENY",
            }
        )
        assert findings.hsts is True
        assert findings.csp == "default-src 'self'"
        assert findings.x_frame_options == "DENY"


class TestAnalyzeCookie:
    def test_flags_insecure_cookie(self):
        result = analyze_cookie("session=abc123; Path=/")
        assert result["secure"] is False
        assert result["http_only"] is False

    def test_flags_secure_httponly_samesite_cookie(self):
        result = analyze_cookie("session=abc123; Secure; HttpOnly; SameSite=Strict; Path=/")
        assert result["secure"] is True
        assert result["http_only"] is True
        assert result["same_site"] == "Strict"


class TestHygieneScore:
    def test_perfect_site_scores_100(self):
        findings = analyze_headers(
            {
                "Strict-Transport-Security": "max-age=1",
                "Content-Security-Policy": "default-src 'self'",
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
            }
        )
        score = compute_hygiene_score(
            https=True, header_findings=findings, mixed_content=False,
            directory_listing_exposed=False, exposed_source_maps_count=0,
            exposed_config_files_count=0, exposed_secrets_count=0,
        )
        assert score == 100

    def test_missing_https_and_headers_lowers_score(self):
        findings = analyze_headers({})
        score = compute_hygiene_score(
            https=False, header_findings=findings, mixed_content=False,
            directory_listing_exposed=False, exposed_source_maps_count=0,
            exposed_config_files_count=0, exposed_secrets_count=0,
        )
        assert score < 100

    def test_exposed_secrets_heavily_penalized(self):
        findings = analyze_headers({})
        score_no_secrets = compute_hygiene_score(
            https=True, header_findings=findings, mixed_content=False,
            directory_listing_exposed=False, exposed_source_maps_count=0,
            exposed_config_files_count=0, exposed_secrets_count=0,
        )
        score_with_secrets = compute_hygiene_score(
            https=True, header_findings=findings, mixed_content=False,
            directory_listing_exposed=False, exposed_source_maps_count=0,
            exposed_config_files_count=0, exposed_secrets_count=2,
        )
        assert score_with_secrets < score_no_secrets

    def test_score_never_goes_below_zero(self):
        findings = analyze_headers({})
        score = compute_hygiene_score(
            https=False, header_findings=findings, mixed_content=True,
            directory_listing_exposed=True, exposed_source_maps_count=10,
            exposed_config_files_count=10, exposed_secrets_count=10,
        )
        assert score == 0


class TestMixedContent:
    def test_detects_http_resource_on_https_page(self):
        html = '<img src="http://insecure.example.com/logo.png">'
        assert detect_mixed_content(html, page_is_https=True) is True

    def test_ignores_http_content_on_http_page(self):
        html = '<img src="http://insecure.example.com/logo.png">'
        assert detect_mixed_content(html, page_is_https=False) is False

    def test_no_false_positive_on_all_https_page(self):
        html = '<img src="https://secure.example.com/logo.png">'
        assert detect_mixed_content(html, page_is_https=True) is False


class TestSecretScanner:
    def test_detects_aws_access_key(self):
        content = "const key = 'AKIAABCDEFGHIJKLMNOP';"
        hits = scan_for_secrets(content, source="app.js")
        assert any(h["type"] == "AWS Access Key ID" for h in hits)

    def test_redacts_match_preview(self):
        content = "const key = 'AKIAABCDEFGHIJKLMNOP';"
        hits = scan_for_secrets(content, source="app.js")
        assert "AKIAABCDEFGHIJKLMNOP" not in hits[0]["match_preview"]

    def test_no_false_positive_on_plain_js(self):
        content = "function add(a, b) { return a + b; }"
        assert scan_for_secrets(content, source="app.js") == []

    def test_detects_public_api_endpoint(self):
        content = 'fetch("/api/v1/users").then(r => r.json())'
        endpoints = scan_for_public_api_endpoints(content)
        assert "/api/v1/users" in endpoints


class TestContrastRatio:
    def test_black_on_white_is_max_contrast(self):
        assert contrast_ratio("#000000", "#ffffff") == 21.0

    def test_identical_colors_have_ratio_one(self):
        assert contrast_ratio("#336699", "#336699") == 1.0

    def test_meets_wcag_aa_for_high_contrast_pair(self):
        assert meets_wcag_aa("#000000", "#ffffff") is True

    def test_fails_wcag_aa_for_low_contrast_pair(self):
        assert meets_wcag_aa("#777777", "#888888") is False
