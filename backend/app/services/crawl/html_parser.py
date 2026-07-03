"""Extraction of metadata, navigation, forms, and asset references from a
rendered page's HTML. Pure functions (HTML string in, dict out) so they're
unit-testable without spinning up Playwright.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

_FONT_URL_RE = re.compile(r"url\(([^)]+\.(?:woff2?|ttf|otf|eot))\)", re.I)


def extract_metadata(html: str, base_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    def meta_content(attr: str, value: str) -> str | None:
        tag = soup.find("meta", attrs={attr: value})
        return tag.get("content") if tag else None

    title = soup.title.string.strip() if soup.title and soup.title.string else None

    open_graph = {
        tag["property"][3:]: tag.get("content")
        for tag in soup.find_all("meta", attrs={"property": re.compile(r"^og:")})
        if tag.get("content")
    }
    twitter_card = {
        tag["name"][8:]: tag.get("content")
        for tag in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")})
        if tag.get("content")
    }
    structured_data = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            structured_data.append(json.loads(script.string or "{}"))
        except (json.JSONDecodeError, TypeError):
            continue

    return {
        "title": title,
        "description": meta_content("name", "description"),
        "open_graph": open_graph,
        "twitter_card": twitter_card,
        "structured_data": structured_data,
    }


def extract_favicon(html: str, base_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    icon = soup.find("link", rel=re.compile(r"icon", re.I))
    if icon and icon.get("href"):
        return urljoin(base_url, icon["href"])
    return urljoin(base_url, "/favicon.ico")


def extract_nav_structure(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    nav = soup.find("nav") or soup.find(attrs={"role": "navigation"})
    if nav is None:
        return []
    return [
        {"text": a.get_text(strip=True), "href": urljoin(base_url, a["href"])}
        for a in nav.find_all("a", href=True)
        if a.get_text(strip=True)
    ]


def extract_forms(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    forms = []
    for form in soup.find_all("form"):
        fields = [
            {"tag": field.name, "type": field.get("type"), "name": field.get("name"), "label": field.get("aria-label")}
            for field in form.find_all(["input", "select", "textarea"])
        ]
        forms.append({"action": form.get("action"), "method": (form.get("method") or "get").lower(), "fields": fields})
    return forms


def extract_buttons(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    buttons = []
    for btn in soup.find_all("button"):
        buttons.append({"text": btn.get_text(strip=True), "type": btn.get("type", "button")})
    for link_btn in soup.find_all("a", attrs={"class": re.compile(r"btn|button", re.I)}):
        buttons.append({"text": link_btn.get_text(strip=True), "type": "link"})
    return buttons


def extract_images(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    return [
        {"src": urljoin(base_url, img["src"]), "alt": img.get("alt"), "has_alt": bool(img.get("alt"))}
        for img in soup.find_all("img", src=True)
    ]


def extract_js_files(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return sorted({urljoin(base_url, s["src"]) for s in soup.find_all("script", src=True)})


def extract_css_files(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return sorted(
        {urljoin(base_url, link["href"]) for link in soup.find_all("link", rel="stylesheet", href=True)}
    )


def extract_fonts(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    fonts = set()
    for link in soup.find_all("link", href=re.compile(r"fonts\.(googleapis|gstatic)\.com", re.I)):
        fonts.add(urljoin(base_url, link["href"]))
    for style in soup.find_all("style"):
        for match in _FONT_URL_RE.findall(style.get_text() or ""):
            fonts.add(urljoin(base_url, match.strip("'\"")))
    return sorted(fonts)


def extract_headings(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    headings = []
    for tag in soup.find_all(re.compile(r"^h[1-6]$")):
        text = tag.get_text(strip=True)
        if text:
            headings.append({"level": int(tag.name[1]), "text": text})
    return headings


def extract_inline_color_pairs(html: str) -> list[dict]:
    """Best-effort static contrast check: elements with both `color` and
    `background-color` set via inline style. Elements styled through
    external CSS aren't visible to a static parse — this catches the
    common, easily-fixed case without claiming full coverage."""
    soup = BeautifulSoup(html, "html.parser")
    pairs = []
    for tag in soup.find_all(style=True):
        style = tag["style"]
        color_match = re.search(r"(?<![\w-])color\s*:\s*(#[0-9a-fA-F]{3,6})", style)
        bg_match = re.search(r"background-color\s*:\s*(#[0-9a-fA-F]{3,6})", style)
        if color_match and bg_match:
            pairs.append(
                {
                    "text": tag.get_text(strip=True)[:80],
                    "foreground": color_match.group(1),
                    "background": bg_match.group(1),
                }
            )
    return pairs


def extract_clickable_non_interactive_elements(html: str) -> list[dict]:
    """Flags `onclick` handlers on elements that aren't natively focusable
    (div/span instead of button/a) and have no `tabindex`/`role` — the same
    static heuristic used by eslint-plugin-jsx-a11y's
    `no-static-element-interactions` rule."""
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    for tag in soup.find_all(onclick=True):
        if tag.name in ("button", "a", "input", "select", "textarea"):
            continue
        if tag.get("tabindex") is not None or tag.get("role"):
            continue
        issues.append({"tag": tag.name, "text": tag.get_text(strip=True)[:80]})
    return issues



def parse_sitemap_urls(sitemap_xml: str) -> list[str]:
    soup = BeautifulSoup(sitemap_xml, "xml")
    return [loc.get_text(strip=True) for loc in soup.find_all("loc")]


def same_origin(url: str, base_url: str) -> bool:
    return urlparse(url).netloc == urlparse(base_url).netloc
