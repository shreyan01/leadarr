from __future__ import annotations

from app.services.vision.vision_prompts import build_vision_prompt
from app.services.vision.vision_scoring import parse_vision_scores


class TestBuildVisionPrompt:
    def test_includes_business_name_and_device(self):
        prompt = build_vision_prompt(business_name="Acme Roofing", device="mobile")
        assert "Acme Roofing" in prompt
        assert "mobile" in prompt

    def test_requests_json_only_response(self):
        prompt = build_vision_prompt(business_name="Acme Roofing", device="desktop")
        assert "JSON object" in prompt
        assert '"trust"' in prompt
        assert '"overall"' in prompt


class TestParseVisionScores:
    def test_maps_all_fields_to_column_names(self):
        structured = {
            "trust": 80, "professionalism": 75, "modernity": 60, "whitespace": 70,
            "typography": 65, "layout": 72, "visual_hierarchy": 68, "cta": 55,
            "conversion": 50, "brand_consistency": 77, "nav_clarity": 82,
            "mobile_friendliness": 90, "overall": 71,
        }
        result = parse_vision_scores(structured)
        assert result["trust_score"] == 80
        assert result["overall_score"] == 71
        assert result["mobile_friendliness_score"] == 90

    def test_clamps_out_of_range_scores(self):
        result = parse_vision_scores({"trust": 150, "professionalism": -20})
        assert result["trust_score"] == 100
        assert result["professionalism_score"] == 0

    def test_handles_missing_fields_as_none(self):
        result = parse_vision_scores({"trust": 80})
        assert result["typography_score"] is None

    def test_computes_overall_when_missing_from_average(self):
        result = parse_vision_scores({"trust": 80, "professionalism": 60})
        assert result["overall_score"] == 70

    def test_handles_non_numeric_gracefully(self):
        result = parse_vision_scores({"trust": "very good", "professionalism": 80})
        assert result["trust_score"] is None
        assert result["professionalism_score"] == 80

    def test_empty_input_returns_all_none(self):
        result = parse_vision_scores({})
        assert all(v is None for v in result.values())
