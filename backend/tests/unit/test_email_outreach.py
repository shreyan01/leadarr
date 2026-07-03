from __future__ import annotations

import json

import pytest

from app.core.exceptions import ProviderError
from app.services.outreach.email_parser import detect_spam_language, parse_email_response

VALID_EMAIL = {
    "subject": "A quick note about yoursite.com",
    "body_text": (
        "Hi there,\n\nI took a look at your website and noticed a few quick "
        "wins that could help more visitors find you, especially around "
        "page load speed. Would you be open to a short call this week?\n\n"
        "Best,\nAlex"
    ),
    "body_html": "<p>Hi there,</p><p>I took a look at your website...</p>",
}


class TestParseEmailResponse:
    def test_parses_clean_json(self):
        result = parse_email_response(json.dumps(VALID_EMAIL))
        assert result["subject"] == VALID_EMAIL["subject"]
        assert result["body_html"] is not None

    def test_strips_code_fences(self):
        fenced = "```json\n" + json.dumps(VALID_EMAIL) + "\n```"
        result = parse_email_response(fenced)
        assert result["subject"] == VALID_EMAIL["subject"]

    def test_raises_on_invalid_json(self):
        with pytest.raises(ProviderError):
            parse_email_response("not json")

    def test_raises_on_missing_subject(self):
        incomplete = {"body_text": VALID_EMAIL["body_text"]}
        with pytest.raises(ProviderError):
            parse_email_response(json.dumps(incomplete))

    def test_raises_on_spam_language(self):
        spammy = {**VALID_EMAIL, "subject": "ACT NOW!!! Limited time offer!!!"}
        with pytest.raises(ProviderError):
            parse_email_response(json.dumps(spammy))

    def test_missing_html_defaults_to_none(self):
        no_html = {k: v for k, v in VALID_EMAIL.items() if k != "body_html"}
        result = parse_email_response(json.dumps(no_html))
        assert result["body_html"] is None


class TestDetectSpamLanguage:
    def test_detects_act_now_phrase(self):
        assert "act now" in detect_spam_language("Act now before it's too late")

    def test_detects_excessive_exclamation(self):
        hits = detect_spam_language("Amazing!!! Don't miss out!!!")
        assert "excessive exclamation points" in hits

    def test_detects_shouting_caps(self):
        hits = detect_spam_language("THIS IS URGENT AND IMPORTANT")
        assert "excessive capitalization" in hits

    def test_clean_professional_text_has_no_hits(self):
        assert detect_spam_language(VALID_EMAIL["body_text"]) == []
