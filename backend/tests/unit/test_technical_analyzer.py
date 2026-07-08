from __future__ import annotations

from app.services.technical import technical_analyzer as analyzer


class TestCheckSitemapPresent:
    def test_true_when_urls_present(self):
        assert analyzer.check_sitemap_present(["https://example.com/"]) is True

    def test_false_when_empty(self):
        assert analyzer.check_sitemap_present([]) is False


class TestCheckRobotsPresent:
    def test_true_when_content_present(self):
        assert analyzer.check_robots_present("User-agent: *\nDisallow:") is True

    def test_false_when_none_or_blank(self):
        assert analyzer.check_robots_present(None) is False
        assert analyzer.check_robots_present("   ") is False


class TestCheckSchemaMarkup:
    def test_present_and_valid(self):
        present, valid = analyzer.check_schema_markup([{"@type": "LocalBusiness", "name": "Acme"}])
        assert present is True
        assert valid is True

    def test_absent_when_empty(self):
        present, valid = analyzer.check_schema_markup([])
        assert present is False
        assert valid is False

    def test_present_but_invalid_without_type(self):
        present, valid = analyzer.check_schema_markup([{"name": "Acme"}])
        assert present is True
        assert valid is False


class TestCheckSocialMetadata:
    def test_both_present(self):
        og, tw = analyzer.check_social_metadata({"title": "Acme"}, {"card": "summary"})
        assert og is True
        assert tw is True

    def test_both_absent(self):
        og, tw = analyzer.check_social_metadata({}, {})
        assert og is False
        assert tw is False


class TestComputeTechnicalScore:
    def test_perfect_site_scores_100(self):
        score = analyzer.compute_technical_score(
            sitemap_present=True, robots_present=True, favicon_present=True,
            schema_present=True, schema_valid=True, open_graph_present=True,
            broken_links_count=0, oversized_images_count=0,
        )
        assert score == 100

    def test_missing_everything_scores_low(self):
        score = analyzer.compute_technical_score(
            sitemap_present=False, robots_present=False, favicon_present=False,
            schema_present=False, schema_valid=False, open_graph_present=False,
            broken_links_count=5, oversized_images_count=5,
        )
        assert score < 50

    def test_score_floors_at_max_combined_deduction(self):
        # Every penalty is individually capped, so the realistic worst case
        # isn't 0 — it's 100 minus the sum of every cap (10+8+5+12+8+25+20=88).
        score = analyzer.compute_technical_score(
            sitemap_present=False, robots_present=False, favicon_present=False,
            schema_present=False, schema_valid=False, open_graph_present=False,
            broken_links_count=100, oversized_images_count=100,
        )
        assert score == 12