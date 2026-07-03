from __future__ import annotations

from app.services.scoring.lead_scoring_engine import LeadPriority, ScoreInputs, compute_lead_score


def _inputs(**overrides) -> ScoreInputs:
    defaults = dict(
        performance_score=80, seo_score=80, accessibility_score=80, security_hygiene_score=80,
        design_score=80, google_rating=4.5, review_count=100, website_age_years=2.0,
        outdated_technology=False,
    )
    defaults.update(overrides)
    return ScoreInputs(**defaults)


def test_high_quality_site_scores_low_opportunity():
    result = compute_lead_score(_inputs())
    assert result.overall_score < 40


def test_poor_quality_site_scores_high_opportunity():
    result = compute_lead_score(
        _inputs(performance_score=20, seo_score=15, accessibility_score=10, security_hygiene_score=25, design_score=20)
    )
    assert result.overall_score > 60


def test_missing_fields_are_excluded_not_zeroed():
    with_all = compute_lead_score(_inputs())
    without_design = compute_lead_score(_inputs(design_score=None))
    # Removing a component should re-normalize weights, not just drop score
    # toward zero, so the two results should be in a similar ballpark.
    assert abs(with_all.overall_score - without_design.overall_score) < 25


def test_all_optional_fields_missing_leaves_only_technology_component():
    result = compute_lead_score(
        ScoreInputs(
            performance_score=None, seo_score=None, accessibility_score=None,
            security_hygiene_score=None, design_score=None, google_rating=None,
            review_count=None, website_age_years=None, outdated_technology=False,
        )
    )
    # technology is a required boolean flag (not an optional measurement),
    # so it's the only component that can never be excluded.
    assert result.components == {"technology": 20.0}
    assert result.overall_score == 20.0
    assert result.priority == LeadPriority.LOW


def test_priority_bands_are_monotonic_with_score():
    low = compute_lead_score(_inputs(performance_score=95, seo_score=95, accessibility_score=95, security_hygiene_score=95, design_score=95))
    high = compute_lead_score(_inputs(performance_score=5, seo_score=5, accessibility_score=5, security_hygiene_score=5, design_score=5))
    priority_order = [LeadPriority.LOW, LeadPriority.MEDIUM, LeadPriority.HIGH, LeadPriority.CRITICAL]
    assert priority_order.index(low.priority) <= priority_order.index(high.priority)


def test_components_sum_reflects_available_inputs_only():
    result = compute_lead_score(_inputs(website_age_years=None))
    assert "website_age" not in result.components
    assert "performance" in result.components


def test_outdated_technology_increases_score():
    modern = compute_lead_score(_inputs(outdated_technology=False))
    outdated = compute_lead_score(_inputs(outdated_technology=True))
    assert outdated.overall_score > modern.overall_score
