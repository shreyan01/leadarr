"""Computes the technical/SEO findings the product spec lists (missing
sitemap/robots, schema markup, social metadata, page load time) from data
the crawl stage already collected. Pure functions — no network I/O here;
the stage service does the fetching, this module just judges what was found.
"""
from __future__ import annotations


def check_sitemap_present(sitemap_urls: list[str]) -> bool:
    return bool(sitemap_urls)


def check_robots_present(robots_txt: str | None) -> bool:
    return bool(robots_txt and robots_txt.strip())


def check_schema_markup(structured_data: list) -> tuple[bool, bool]:
    """Returns (present, valid). "Valid" here means each entry parsed as
    real JSON-LD with a recognizable @type — html_parser already dropped
    anything that failed to parse as JSON, so presence of a non-empty,
    correctly-shaped list is the practical definition of valid available
    without a full schema.org vocabulary validator."""
    if not structured_data:
        return False, False
    valid = all(isinstance(item, dict) and "@type" in item for item in structured_data)
    return True, valid


def check_social_metadata(open_graph: dict, twitter_card: dict) -> tuple[bool, bool]:
    return bool(open_graph), bool(twitter_card)


def compute_technical_score(
    *,
    sitemap_present: bool,
    robots_present: bool,
    favicon_present: bool,
    schema_present: bool,
    schema_valid: bool,
    open_graph_present: bool,
    broken_links_count: int,
    oversized_images_count: int,
) -> int:
    score = 100
    if not sitemap_present:
        score -= 10
    if not robots_present:
        score -= 8
    if not favicon_present:
        score -= 5
    if not schema_present:
        score -= 12
    elif not schema_valid:
        score -= 6
    if not open_graph_present:
        score -= 8
    score -= min(broken_links_count * 5, 25)
    score -= min(oversized_images_count * 4, 20)
    return max(0, min(100, score))