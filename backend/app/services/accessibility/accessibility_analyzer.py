"""Computes accessibility findings from static HTML analysis. Pure
functions operating on data already extracted by ``html_parser`` (images,
forms, buttons, headings) plus two additional static checks — inline-style
contrast and non-interactive-element click handlers. This is what's
feasible without a full render/AST pass; genuinely dynamic issues (focus
order, live-region announcements) need Phase 5+ vision/manual review and
aren't claimed here.
"""
from __future__ import annotations

from app.services.accessibility.contrast import contrast_ratio, meets_wcag_aa


def compute_heading_hierarchy_issues(headings: list[dict]) -> list[dict]:
    issues = []
    h1_count = sum(1 for h in headings if h["level"] == 1)
    if h1_count == 0 and headings:
        issues.append({"type": "missing_h1", "detail": "Page has headings but no <h1>."})
    if h1_count > 1:
        issues.append({"type": "multiple_h1", "detail": f"Page has {h1_count} <h1> elements."})

    previous_level = 0
    for heading in headings:
        level = heading["level"]
        if previous_level and level > previous_level + 1:
            issues.append(
                {
                    "type": "skipped_level",
                    "detail": f"Heading '{heading['text'][:60]}' jumps from h{previous_level} to h{level}.",
                }
            )
        previous_level = level
    return issues


def compute_missing_alt(images: list[dict]) -> tuple[int, list[dict]]:
    missing = [img for img in images if not img.get("has_alt")]
    return len(missing), missing


def compute_unlabeled_buttons(buttons: list[dict]) -> list[dict]:
    return [b for b in buttons if not b.get("text")]


def compute_unlabeled_form_fields(forms: list[dict]) -> list[dict]:
    unlabeled = []
    for form in forms:
        for field in form.get("fields", []):
            if field.get("type") in ("hidden", "submit", "button"):
                continue
            if not field.get("label") and not field.get("name"):
                unlabeled.append(field)
    return unlabeled


def compute_contrast_issues(color_pairs: list[dict]) -> list[dict]:
    issues = []
    for pair in color_pairs:
        ratio = contrast_ratio(pair["foreground"], pair["background"])
        if not meets_wcag_aa(pair["foreground"], pair["background"]):
            issues.append({**pair, "contrast_ratio": ratio, "wcag_aa_minimum": 4.5})
    return issues


def compute_keyboard_nav_issues(clickable_non_interactive: list[dict]) -> list[dict]:
    return clickable_non_interactive


def compute_accessibility_score(
    *,
    missing_alt_count: int,
    heading_issues_count: int,
    contrast_issues_count: int,
    unlabeled_buttons_count: int,
    unlabeled_fields_count: int,
    keyboard_nav_issues_count: int,
) -> int:
    score = 100
    score -= min(missing_alt_count * 3, 25)
    score -= min(heading_issues_count * 5, 15)
    score -= min(contrast_issues_count * 4, 20)
    score -= min(unlabeled_buttons_count * 4, 15)
    score -= min(unlabeled_fields_count * 5, 15)
    score -= min(keyboard_nav_issues_count * 5, 10)
    return max(0, min(100, score))
