from __future__ import annotations

from app.adapters.discovery.interfaces import DiscoveredBusiness
from app.adapters.discovery.osm_provider import OsmDiscoveryProvider, _normalize_name


def _biz(**overrides) -> DiscoveredBusiness:
    defaults = dict(
        name="H&B Tax Firm", category="Tax Firm", website_url=None, phone=None, address=None,
        city="New York", country="US", latitude=1.0, longitude=2.0, provider_place_id="osm:node:1",
        google_rating=None, review_count=None,
    )
    defaults.update(overrides)
    return DiscoveredBusiness(**defaults)


class TestNormalizeName:
    def test_lowercases_and_strips_punctuation(self):
        assert _normalize_name("H&B Tax Firm") == _normalize_name("H & B Tax Firm")

    def test_collapses_whitespace(self):
        assert _normalize_name("Acme   Roofing") == _normalize_name("Acme Roofing")


class TestDeduplicate:
    def test_collapses_duplicate_names_into_one(self):
        businesses = [
            _biz(provider_place_id="osm:node:1"),
            _biz(provider_place_id="osm:way:2"),
            _biz(provider_place_id="osm:node:3"),
        ]
        result = OsmDiscoveryProvider._deduplicate(businesses)
        assert len(result) == 1

    def test_prefers_the_record_with_a_website(self):
        businesses = [
            _biz(provider_place_id="osm:node:1", website_url=None),
            _biz(provider_place_id="osm:way:2", website_url="https://hbtax.example.com"),
        ]
        result = OsmDiscoveryProvider._deduplicate(businesses)
        assert len(result) == 1
        assert result[0].website_url == "https://hbtax.example.com"

    def test_distinct_businesses_are_not_merged(self):
        businesses = [_biz(name="H&B Tax Firm"), _biz(name="Acme Roofing")]
        result = OsmDiscoveryProvider._deduplicate(businesses)
        assert len(result) == 2

    def test_prefers_contact_info_over_bare_record(self):
        businesses = [
            _biz(provider_place_id="osm:node:1"),
            _biz(provider_place_id="osm:way:2", phone="+1 555 0100"),
        ]
        result = OsmDiscoveryProvider._deduplicate(businesses)
        assert len(result) == 1
        assert result[0].phone == "+1 555 0100"



class TestBuildOverpassQuery:
    def test_uses_curated_tag_mapping_for_known_category(self):
        query = OsmDiscoveryProvider._build_overpass_query(category="Roofing", bbox=(1.0, 2.0, 3.0, 4.0))
        assert '"craft"="roofer"' in query
        assert "1.0,3.0,2.0,4.0" in query

    def test_is_case_insensitive_on_category(self):
        query = OsmDiscoveryProvider._build_overpass_query(category="DENTIST", bbox=(1.0, 2.0, 3.0, 4.0))
        assert '"amenity"="dentist"' in query

    def test_falls_back_to_name_search_for_unknown_category(self):
        query = OsmDiscoveryProvider._build_overpass_query(category="Widget Emporium", bbox=(1.0, 2.0, 3.0, 4.0))
        assert 'name"~"Widget Emporium",i' in query
        assert '"shop"' in query and '"office"' in query


class TestParseElement:
    def test_extracts_basic_fields_from_node(self):
        element = {
            "type": "node",
            "id": 123,
            "lat": 30.1,
            "lon": -97.5,
            "tags": {"name": "Acme Roofing", "website": "https://acme.example.com", "phone": "+1 512 555 0100"},
        }
        result = OsmDiscoveryProvider._parse_element(element, category="Roofing", city="Austin", country="US")
        assert result is not None
        assert result.name == "Acme Roofing"
        assert result.website_url == "https://acme.example.com"
        assert result.phone == "+1 512 555 0100"
        assert result.provider_place_id == "osm:node:123"
        assert result.google_rating is None  # never fabricated

    def test_captures_social_and_email_fallback_when_no_website(self):
        element = {
            "type": "node",
            "id": 456,
            "lat": 30.1,
            "lon": -97.5,
            "tags": {
                "name": "Joe's Diner",
                "contact:facebook": "https://facebook.com/joesdiner",
                "contact:instagram": "https://instagram.com/joesdiner",
                "email": "joe@example.com",
            },
        }
        result = OsmDiscoveryProvider._parse_element(element, category="Restaurant", city="Austin", country="US")
        assert result is not None
        assert result.website_url is None
        assert result.facebook_url == "https://facebook.com/joesdiner"
        assert result.instagram_url == "https://instagram.com/joesdiner"
        assert result.email == "joe@example.com"

    def test_returns_none_for_unnamed_element(self):
        element = {"type": "node", "id": 789, "lat": 1.0, "lon": 2.0, "tags": {}}
        result = OsmDiscoveryProvider._parse_element(element, category="Roofing", city="Austin", country="US")
        assert result is None

    def test_uses_center_coordinates_for_way_elements(self):
        element = {
            "type": "way",
            "id": 111,
            "center": {"lat": 40.7, "lon": -74.0},
            "tags": {"name": "Big Store"},
        }
        result = OsmDiscoveryProvider._parse_element(element, category="Shop", city="NYC", country="US")
        assert result is not None
        assert result.latitude == 40.7
        assert result.longitude == -74.0

    def test_builds_address_from_addr_tags(self):
        element = {
            "type": "node",
            "id": 222,
            "lat": 1.0,
            "lon": 2.0,
            "tags": {"name": "Test Biz", "addr:housenumber": "123", "addr:street": "Main St"},
        }
        result = OsmDiscoveryProvider._parse_element(element, category="Shop", city="Austin", country="US")
        assert result is not None
        assert result.address == "123 Main St Austin"