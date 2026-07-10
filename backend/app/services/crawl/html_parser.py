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


_EMAIL_TEXT_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# Common false positives worth excluding — image/font/CSS references that
# happen to look like an email (e.g. "2x@retina.png" style asset names)
# and placeholder addresses that show up in templates.
_EMAIL_EXCLUDE_DOMAINS = {"example.com", "sentry.io", "wixpress.com", "godaddy.com", "yourdomain.com"}


def extract_contact_email(html: str) -> str | None:
    """Real `mailto:` links are the reliable source — essentially zero
    false positives, since a business only adds one deliberately. Falls
    back to scanning visible text for a plain-written address (very common
    on small-business "Contact Us" pages: "info@company.com" with no link
    behind it at all) if no mailto: link is present."""
    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().startswith("mailto:"):
            address = href[len("mailto:"):].split("?")[0].strip()
            if address and "@" in address:
                return address

    visible_text = soup.get_text(" ", strip=True)
    for match in _EMAIL_TEXT_RE.finditer(visible_text):
        candidate = match.group(0)
        domain = candidate.rsplit("@", 1)[-1].lower()
        if domain not in _EMAIL_EXCLUDE_DOMAINS:
            return candidate

    return None


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



def extract_all_links(html: str, base_url: str, *, same_origin_only: bool = True, limit: int = 30) -> list[str]:
    """All distinct <a href> links on the page, for broken-link checking.
    Capped and same-origin by default — checking every external link on
    the internet isn't the goal, just the site's own navigable pages."""
    soup = BeautifulSoup(html, "html.parser")
    seen: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        resolved = urljoin(base_url, href)
        if same_origin_only and not same_origin(resolved, base_url):
            continue
        if resolved not in seen:
            seen.append(resolved)
        if len(seen) >= limit:
            break
    return seen


def detect_google_business_link(html: str) -> str | None:
    """A business linking to its own Google Business/Maps listing from
    their site — checkable without the Places API. Doesn't tell us whether
    a listing exists if they *don't* link to one, only confirms it when
    they do."""
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"google\.com/maps|g\.page|business\.google\.com", href, re.I):
            return href
    return None



def parse_sitemap_urls(sitemap_xml: str) -> list[str]:
    soup = BeautifulSoup(sitemap_xml, "xml")
    return [loc.get_text(strip=True) for loc in soup.find_all("loc")]


def same_origin(url: str, base_url: str) -> bool:
    return urlparse(url).netloc == urlparse(base_url).netloc