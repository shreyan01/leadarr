from __future__ import annotations

from app.services.accessibility import accessibility_analyzer as analyzer
from app.services.crawl.html_parser import extract_clickable_non_interactive_elements, extract_headings


def test_extract_headings_orders_by_document_flow():
    html = "<h1>Welcome</h1><h3>Skipped h2</h3><h2>Services</h2>"
    headings = extract_headings(html)
    levels = [h["level"] for h in headings]
    assert levels == [1, 3, 2]


def test_heading_hierarchy_flags_skipped_level():
    headings = [{"level": 1, "text": "Welcome"}, {"level": 3, "text": "Skipped"}]
    issues = analyzer.compute_heading_hierarchy_issues(headings)
    assert any(i["type"] == "skipped_level" for i in issues)


def test_heading_hierarchy_flags_missing_h1():
    headings = [{"level": 2, "text": "Services"}]
    issues = analyzer.compute_heading_hierarchy_issues(headings)
    assert any(i["type"] == "missing_h1" for i in issues)


def test_heading_hierarchy_flags_multiple_h1():
    headings = [{"level": 1, "text": "A"}, {"level": 1, "text": "B"}]
    issues = analyzer.compute_heading_hierarchy_issues(headings)
    assert any(i["type"] == "multiple_h1" for i in issues)


def test_compute_missing_alt_counts_images_without_alt():
    images = [{"src": "a.jpg", "has_alt": True}, {"src": "b.jpg", "has_alt": False}]
    count, missing = analyzer.compute_missing_alt(images)
    assert count == 1
    assert missing[0]["src"] == "b.jpg"


def test_compute_unlabeled_buttons_flags_empty_text():
    buttons = [{"text": "Submit", "type": "submit"}, {"text": "", "type": "button"}]
    unlabeled = analyzer.compute_unlabeled_buttons(buttons)
    assert len(unlabeled) == 1


def test_extract_clickable_non_interactive_flags_div_with_onclick():
    html = '<div onclick="doThing()">Click me</div><button onclick="ok()">Fine</button>'
    issues = extract_clickable_non_interactive_elements(html)
    assert len(issues) == 1
    assert issues[0]["tag"] == "div"


def test_extract_clickable_non_interactive_ignores_element_with_tabindex():
    html = '<div onclick="doThing()" tabindex="0">Click me</div>'
    issues = extract_clickable_non_interactive_elements(html)
    assert issues == []


def test_accessibility_score_decreases_with_more_issues():
    perfect = analyzer.compute_accessibility_score(
        missing_alt_count=0, heading_issues_count=0, contrast_issues_count=0,
        unlabeled_buttons_count=0, unlabeled_fields_count=0, keyboard_nav_issues_count=0,
    )
    flawed = analyzer.compute_accessibility_score(
        missing_alt_count=5, heading_issues_count=2, contrast_issues_count=3,
        unlabeled_buttons_count=2, unlabeled_fields_count=1, keyboard_nav_issues_count=1,
    )
    assert perfect == 100
    assert flawed < perfect
