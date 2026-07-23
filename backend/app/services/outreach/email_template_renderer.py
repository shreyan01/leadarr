"""Renders the final HTML email from the model's plain-text draft.

Deliberately NOT asking the LLM to author the HTML itself: model-generated
markup is unpredictable (inconsistent tags, occasional broken structure),
and email clients are far less forgiving of malformed HTML than a browser
is. Instead, the model only supplies subject + body_text (plain paragraphs,
optionally using **bold** / *italic* markdown-lite markers for emphasis on
a short key phrase); this module wraps that into one deterministic,
hand-tested inline-CSS template every time, so styling is consistent and
reliable regardless of what the model produces.

Uses table-based layout — old-fashioned, but still the most broadly
compatible approach across email clients (particularly Outlook's Word-based
rendering engine, which ignores modern CSS layout entirely).
"""
from __future__ import annotations

import base64
import html
import re
from functools import lru_cache
from pathlib import Path

_LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "logo.png"

# Matches the logo's own solid black background and this app's own
# dark-canvas/brass design language — a dark header band with the logo
# looks deliberate, not like a transparency mistake, and reads as
# consistent branding rather than a mismatched header/body.
_HEADER_BG = "#0B0E14"
_BRAND_ACCENT = "#C99A44"
_BODY_BG = "#F7F7F8"
_TEXT_COLOR = "#27272A"

# Markdown-lite emphasis markers the model is allowed to use for a short
# key phrase (business name, one key finding, the call to action) —
# **bold** and *italic*. Applied to already-HTML-escaped text, so this
# only ever matches literal asterisks the model wrote, never anything a
# recipient's own content could inject.
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")


def _apply_emphasis_html(escaped_text: str) -> str:
    """Converts **bold**/*italic* markers into real tags. Must run AFTER
    html.escape() on the surrounding text, so the tags we inject here are
    the only real markup — anything from the model's own content stays
    inert text."""
    text = _BOLD_RE.sub(r"<strong>\1</strong>", escaped_text)
    text = _ITALIC_RE.sub(r"<em>\1</em>", text)
    return text


def strip_email_markdown(text: str) -> str:
    """Removes **bold**/*italic* markers for the plain-text MIME
    alternative — plain text can't render emphasis, so leaving literal
    asterisks in would just look like a formatting mistake to anyone whose
    client shows the plain-text part."""
    text = _BOLD_RE.sub(r"\1", text)
    text = _ITALIC_RE.sub(r"\1", text)
    return text


@lru_cache
def _logo_data_uri() -> str | None:
    if not _LOGO_PATH.exists():
        return None
    encoded = base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_branded_email_html(*, subject: str, body_text: str, sender_name: str) -> str:
    logo_uri = _logo_data_uri()
    logo_html = (
        f'<img src="{logo_uri}" alt="{html.escape(sender_name)}" width="40" height="40" '
        f'style="display:block; border-radius:8px;" />'
        if logo_uri
        else ""
    )

    paragraphs_html = "".join(
        f'<p style="margin:0 0 16px 0; color:{_TEXT_COLOR}; font-size:15px; line-height:1.7; '
        f'font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">'
        f'{_apply_emphasis_html(html.escape(paragraph))}</p>'
        for paragraph in body_text.split("\n\n")
        if paragraph.strip()
    )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{html.escape(subject)}</title></head>
<body style="margin:0; padding:0; background-color:{_BODY_BG};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{_BODY_BG}; padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px; background-color:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
          <tr>
            <td style="background-color:{_HEADER_BG}; padding:24px 32px;">
              <table role="presentation" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="vertical-align:middle;">{logo_html}</td>
                  <td style="vertical-align:middle; padding-left:12px; font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; font-size:17px; font-weight:600; color:#ffffff;">
                    {html.escape(sender_name)}
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;">
              {paragraphs_html}
            </td>
          </tr>
          <tr>
            <td style="padding:20px 32px; border-top:1px solid #EDEDF0;">
              <p style="margin:0; font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; font-size:12px; color:#9CA3AF;">
                Sent by <span style="color:{_BRAND_ACCENT};">{html.escape(sender_name)}</span>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""