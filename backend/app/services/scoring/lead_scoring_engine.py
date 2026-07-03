"""Weighted lead-scoring engine.

Pure function: raw inputs in, a 0-100 opportunity score + per-component
breakdown + priority band out. Deliberately linear and auditable — an
agency salesperson needs to be able to explain *why* a lead scored 82, not
just trust a black box. Higher score = a website with more visible room for
improvement (i.e. a better sales opportunity), not a "better website" score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LeadPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Weights sum to 1.0 across the opportunity-relevant components. Business
# rating/reviews are signals of "this is a real, findable business worth
# pursuing" rather than website quality, so they get smaller weight than the
# audit-derived components that directly drive the pitch.
_WEIGHTS = {
    "performance": 0.16,
    "security": 0.14,
    "accessibility": 0.12,
    "seo": 0.16,
    "design": 0.18,
    "business_rating": 0.08,
    "review_count": 0.06,
    "website_age": 0.05,
    "technology": 0.05,
}

assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-9


@dataclass
class ScoreInputs:
    performance_score: int | None  # Lighthouse, 0-100 (higher = better site)
    seo_score: int | None  # Lighthouse, 0-100
    accessibility_score: int | None  # static analyzer, 0-100
    security_hygiene_score: int | None  # 0-100
    design_score: int | None  # vision overall, 0-100
    google_rating: float | None  # 0-5
    review_count: int | None
    website_age_years: float | None  # None if unknown
    outdated_technology: bool = False  # e.g. no modern framework detected


@dataclass
class ScoreResult:
    overall_score: float
    priority: LeadPriority
    components: dict[str, float]


def _invert(quality_score: int | None) -> float | None:
    """Converts a 0-100 *quality* score into a 0-100 *opportunity* score —
    a low-quality site is a bigger opportunity, so the scale flips."""
    if quality_score is None:
        return None
    return max(0.0, min(100.0, 100.0 - quality_score))


def _rating_component(rating: float | None) -> float | None:
    # A well-reviewed business with a bad website is the ideal pitch — high
    # rating raises the score (worth pursuing); no/low rating lowers it.
    if rating is None:
        return None
    return max(0.0, min(100.0, (rating / 5.0) * 100.0))


def _review_count_component(count: int | None) -> float | None:
    if count is None:
        return None
    # Diminishing returns past ~100 reviews — log-ish staircase, no external deps.
    if count <= 0:
        return 0.0
    if count < 10:
        return 20.0
    if count < 50:
        return 50.0
    if count < 150:
        return 75.0
    return 100.0


def _website_age_component(age_years: float | None) -> float | None:
    if age_years is None:
        return None
    # Older, unmaintained sites are a bigger opportunity.
    return max(0.0, min(100.0, (age_years / 10.0) * 100.0))


def _technology_component(outdated_technology: bool) -> float:
    return 80.0 if outdated_technology else 20.0


def compute_lead_score(inputs: ScoreInputs) -> ScoreResult:
    raw_components = {
        "performance": _invert(inputs.performance_score),
        "security": _invert(inputs.security_hygiene_score),
        "accessibility": _invert(inputs.accessibility_score),
        "seo": _invert(inputs.seo_score),
        "design": _invert(inputs.design_score),
        "business_rating": _rating_component(inputs.google_rating),
        "review_count": _review_count_component(inputs.review_count),
        "website_age": _website_age_component(inputs.website_age_years),
        "technology": _technology_component(inputs.outdated_technology),
    }

    available = {k: v for k, v in raw_components.items() if v is not None}
    if not available:
        return ScoreResult(overall_score=0.0, priority=LeadPriority.LOW, components={})

    weight_total = sum(_WEIGHTS[k] for k in available)
    overall = sum(_WEIGHTS[k] * v for k, v in available.items()) / weight_total

    return ScoreResult(
        overall_score=round(overall, 2),
        priority=_priority_band(overall),
        components={k: round(v, 2) for k, v in available.items()},
    )


def _priority_band(score: float) -> LeadPriority:
    if score >= 75:
        return LeadPriority.CRITICAL
    if score >= 55:
        return LeadPriority.HIGH
    if score >= 35:
        return LeadPriority.MEDIUM
    return LeadPriority.LOW
