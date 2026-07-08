from __future__ import annotations

from app.services.crawl.html_parser import (
    detect_google_business_link,
    extract_all_links,
    extract_buttons,
    extract_css_files,
    extract_favicon,
    extract_forms,
    extract_images,
    extract_js_files,
    extract_metadata,
    extract_nav_structure,
    parse_sitemap_urls,
)

SAMPLE_HTML = """
<html>
<head>
  <title> Acme Roofing | Home </title>
  <meta name="description" content="Roofing done right." />
  <meta property="og:title" content="Acme Roofing" />
  <meta property="og:image" content="/social.png" />
  <meta name="twitter:card" content="summary" />
  <link rel="icon" href="/favicon.png" />
  <link rel="stylesheet" href="/styles/main.css" />
  <script type="application/ld+json">{"@type": "LocalBusiness", "name": "Acme Roofing"}</script>
</head>
<body>
  <nav><a href="/services">Services</a><a href="/contact">Contact</a></nav>
  <form action="/quote" method="post">
    <input type="text" name="name" />
    <input type="email" name="email" />
  </form>
  <button type="submit">Get a Quote</button>
  <img src="/hero.jpg" alt="Roof repair crew" />
  <img src="/logo.png" />
  <script src="/app.js"></script>
</body>
</html>
"""

BASE_URL = "https://acmeroofing.example.com"


def test_extract_metadata_pulls_title_description_og_and_structured_data():
    meta = extract_metadata(SAMPLE_HTML, BASE_URL)
    assert meta["title"] == "Acme Roofing | Home"
    assert meta["description"] == "Roofing done right."
    assert meta["open_graph"]["title"] == "Acme Roofing"
    assert meta["twitter_card"]["card"] == "summary"
    assert meta["structured_data"][0]["@type"] == "LocalBusiness"


def test_extract_favicon_resolves_relative_url():
    assert extract_favicon(SAMPLE_HTML, BASE_URL) == f"{BASE_URL}/favicon.png"


def test_extract_nav_structure_resolves_links():
    nav = extract_nav_structure(SAMPLE_HTML, BASE_URL)
    hrefs = {item["href"] for item in nav}
    assert f"{BASE_URL}/services" in hrefs
    assert f"{BASE_URL}/contact" in hrefs


def test_extract_forms_captures_fields():
    forms = extract_forms(SAMPLE_HTML)
    assert len(forms) == 1
    assert forms[0]["method"] == "post"
    field_names = {f["name"] for f in forms[0]["fields"]}
    assert {"name", "email"} <= field_names


def test_extract_buttons_captures_submit_button():
    buttons = extract_buttons(SAMPLE_HTML)
    assert any(b["text"] == "Get a Quote" for b in buttons)


def test_extract_images_flags_missing_alt():
    images = extract_images(SAMPLE_HTML, BASE_URL)
    by_src = {img["src"]: img for img in images}
    assert by_src[f"{BASE_URL}/hero.jpg"]["has_alt"] is True
    assert by_src[f"{BASE_URL}/logo.png"]["has_alt"] is False


def test_extract_js_and_css_files_resolved():
    assert f"{BASE_URL}/app.js" in extract_js_files(SAMPLE_HTML, BASE_URL)
    assert f"{BASE_URL}/styles/main.css" in extract_css_files(SAMPLE_HTML, BASE_URL)


def test_parse_sitemap_urls_extracts_loc_entries():
    xml = """<?xml version="1.0"?>
    <urlset><url><loc>https://acmeroofing.example.com/</loc></url>
    <url><loc>https://acmeroofing.example.com/contact</loc></url></urlset>"""
    urls = parse_sitemap_urls(xml)
    assert urls == ["https://acmeroofing.example.com/", "https://acmeroofing.example.com/contact"]


def test_extract_all_links_dedupes_and_stays_same_origin():
    html = """
    <a href="/about">About</a>
    <a href="/about">About again</a>
    <a href="https://external.example.com/">External</a>
    <a href="#section">Anchor only</a>
    <a href="mailto:test@example.com">Email</a>
    """
    links = extract_all_links(html, BASE_URL)
    assert links == [f"{BASE_URL}/about"]


def test_extract_all_links_respects_limit():
    html = "".join(f'<a href="/page{i}">Page {i}</a>' for i in range(50))
    links = extract_all_links(html, BASE_URL, limit=5)
    assert len(links) == 5


def test_detect_google_business_link_finds_maps_url():
    html = '<a href="https://www.google.com/maps/place/Acme+Roofing">Find us</a>'
    assert detect_google_business_link(html) is not None


def test_detect_google_business_link_returns_none_when_absent():
    html = '<a href="/contact">Contact</a>'
    assert detect_google_business_link(html) is None