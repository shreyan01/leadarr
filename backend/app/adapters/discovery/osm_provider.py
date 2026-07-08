"""OpenStreetMap discovery adapter.

Two free, keyless public services, chained together:
1. Nominatim (OSM's geocoder) resolves "city, country" -> a bounding box.
2. Overpass API queries OSM for businesses within that box matching the
   requested category.

No API key, no billing account, no metered usage — rate-limited by fair-use
policy rather than money. Trade-off vs. Google Places: OSM is community-
edited, so website/rating coverage is inconsistent (weaker in the US than
Europe), and there are no ratings/reviews at all. To make the most of what
IS there, this adapter also captures phone/email/Facebook/Instagram tags as
fallback contact info when a business has no `website` tag — a business
whose only web presence is a Facebook page is still a real, often *better*
lead (it shows they've tried to be findable online and just never got a
real site), not a dead end to discard.
"""
from __future__ import annotations

import re

import httpx

from app.adapters.discovery.interfaces import DiscoveredBusiness
from app.core.exceptions import ProviderError

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Nominatim's usage policy asks for an identifying User-Agent on every
# request — this is a courtesy requirement of the free service, not
# optional decoration.
_USER_AGENT = "LeadForgeDiscoveryBot/1.0 (self-hosted lead-gen audit tool)"

# Curated mapping from common business-category phrases (matching the
# product brief's own examples: Roofing, Dentist, Tax Firm, Law Firm,
# Restaurant, HVAC, Auto Repair, Real Estate) to the OSM tag(s) that
# actually represent them. OSM has no free-text "category" field, so this
# is how a plain-English category becomes a real query.
_CATEGORY_TAG_MAP: dict[str, list[tuple[str, str]]] = {
    "roofing": [("craft", "roofer")],
    "roofer": [("craft", "roofer")],
    "dentist": [("amenity", "dentist")],
    "dental": [("amenity", "dentist")],
    "tax firm": [("office", "tax_advisor")],
    "tax advisor": [("office", "tax_advisor")],
    "accountant": [("office", "accountant")],
    "accounting": [("office", "accountant")],
    "law firm": [("office", "lawyer")],
    "lawyer": [("office", "lawyer")],
    "attorney": [("office", "lawyer")],
    "restaurant": [("amenity", "restaurant")],
    "hvac": [("craft", "hvac")],
    "auto repair": [("shop", "car_repair")],
    "mechanic": [("shop", "car_repair")],
    "real estate": [("office", "estate_agent")],
    "realtor": [("office", "estate_agent")],
    "plumber": [("craft", "plumber")],
    "plumbing": [("craft", "plumber")],
    "electrician": [("craft", "electrician")],
    "hair salon": [("shop", "hairdresser")],
    "salon": [("shop", "hairdresser")],
    "cafe": [("amenity", "cafe")],
    "coffee shop": [("amenity", "cafe")],
    "hotel": [("tourism", "hotel")],
    "gym": [("leisure", "fitness_centre")],
    "fitness": [("leisure", "fitness_centre")],
    "insurance": [("office", "insurance")],
    "veterinarian": [("amenity", "veterinary")],
    "vet": [("amenity", "veterinary")],
    "doctor": [("amenity", "doctors")],
    "clinic": [("amenity", "doctors")],
    "pharmacy": [("amenity", "pharmacy")],
    "bakery": [("shop", "bakery")],
    "florist": [("shop", "florist")],
}

# Fallback tag set used when the category doesn't match anything curated
# above — casts a wider net across the general-purpose OSM business
# namespaces, filtered by a case-insensitive name match on the category text.
_FALLBACK_TAG_KEYS = ["shop", "office", "craft", "amenity"]


_NAME_NOISE_RE = re.compile(r"[^\w\s]")


def _normalize_name(name: str) -> str:
    """Lowercase, strip punctuation/extra whitespace so trivial formatting
    differences ("H&B Tax Firm" vs "H & B Tax Firm") don't defeat dedup."""
    return re.sub(r"\s+", " ", _NAME_NOISE_RE.sub(" ", name.lower())).strip()


class OsmDiscoveryProvider:
    def __init__(self, timeout_s: float = 30.0) -> None:
        self._timeout_s = timeout_s

    async def search(
        self, *, country: str, city: str, category: str, limit: int = 20
    ) -> list[DiscoveredBusiness]:
        bbox = await self._geocode_bbox(city=city, country=country)
        query = self._build_overpass_query(category=category, bbox=bbox)

        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.post(
                    _OVERPASS_URL, data={"data": query}, headers={"User-Agent": _USER_AGENT}
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            # httpx timeout exceptions often stringify to "" with no
            # message — include the exception type so failures are
            # actually diagnosable instead of a blank error.
            raise ProviderError(f"Overpass query failed: {type(exc).__name__}: {exc}") from exc

        results: list[DiscoveredBusiness] = []
        for element in data.get("elements", []):
            business = self._parse_element(element, category=category, city=city, country=country)
            if business is not None:
                results.append(business)

        results = self._deduplicate(results)
        return results[:limit]

    @staticmethod
    def _deduplicate(businesses: list[DiscoveredBusiness]) -> list[DiscoveredBusiness]:
        """OSM frequently maps one real business as multiple elements — a
        point AND a building outline, or duplicate community edits — each
        with a distinct element ID, so ID-based dedup (what the repository
        layer does) doesn't catch it. Groups by normalized name instead and
        keeps the most complete record per group (preferring one with a
        website, then other contact info, then whichever came first)."""
        best_by_name: dict[str, DiscoveredBusiness] = {}

        def completeness(b: DiscoveredBusiness) -> tuple:
            return (
                bool(b.website_url),
                bool(b.phone or b.email),
                bool(b.facebook_url or b.instagram_url),
                bool(b.address),
            )

        for business in businesses:
            key = _normalize_name(business.name)
            existing = best_by_name.get(key)
            if existing is None or completeness(business) > completeness(existing):
                best_by_name[key] = business

        return list(best_by_name.values())

    async def _geocode_bbox(self, *, city: str, country: str) -> tuple[float, float, float, float]:
        """Returns (south, north, west, east)."""
        params = {"city": city, "country": country, "format": "json", "limit": 1}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.get(
                    _NOMINATIM_URL, params=params, headers={"User-Agent": _USER_AGENT}
                )
                response.raise_for_status()
                results = response.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Nominatim geocoding failed: {exc}") from exc

        if not results:
            raise ProviderError(f"Could not geocode '{city}, {country}' via Nominatim.")

        south, north, west, east = (float(v) for v in results[0]["boundingbox"])
        return south, north, west, east

    @staticmethod
    def _build_overpass_query(*, category: str, bbox: tuple[float, float, float, float]) -> str:
        south, north, west, east = bbox
        bbox_str = f"{south},{west},{north},{east}"
        category_key = category.strip().lower()
        tag_pairs = _CATEGORY_TAG_MAP.get(category_key)
        if not tag_pairs and category_key.endswith("s"):
            # Forgiving match for plurals ("Tax Firms" -> "tax firm") so a
            # small wording difference doesn't silently fall through to the
            # much more expensive broad fallback query below.
            tag_pairs = _CATEGORY_TAG_MAP.get(category_key[:-1])
        if tag_pairs:
            clauses = "\n".join(
                f'  node["{k}"="{v}"]({bbox_str});\n  way["{k}"="{v}"]({bbox_str});' for k, v in tag_pairs
            )
        else:
            # No curated mapping — search the general business namespaces
            # for a name containing the category text (best-effort).
            escaped = category.strip().replace('"', '\\"')
            clauses = "\n".join(
                f'  node["{key}"]["name"~"{escaped}",i]({bbox_str});\n'
                f'  way["{key}"]["name"~"{escaped}",i]({bbox_str});'
                for key in _FALLBACK_TAG_KEYS
            )

        return f"[out:json][timeout:25];\n(\n{clauses}\n);\nout center 40;"

    @staticmethod
    def _parse_element(element: dict, *, category: str, city: str, country: str) -> DiscoveredBusiness | None:
        tags = element.get("tags", {})
        name = tags.get("name")
        if not name:
            return None  # unnamed nodes aren't useful leads

        if element["type"] == "way" and "center" in element:
            lat, lon = element["center"]["lat"], element["center"]["lon"]
        else:
            lat, lon = element.get("lat"), element.get("lon")

        address_parts = [
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
            tags.get("addr:city") or city,
        ]
        address = " ".join(p for p in address_parts if p) or None

        return DiscoveredBusiness(
            name=name,
            category=category,
            website_url=tags.get("website") or tags.get("contact:website"),
            phone=tags.get("phone") or tags.get("contact:phone"),
            address=address,
            city=city,
            country=country,
            latitude=lat,
            longitude=lon,
            provider_place_id=f"osm:{element['type']}:{element['id']}",
            google_rating=None,  # OSM has no ratings/reviews — not fabricated
            review_count=None,
            email=tags.get("email") or tags.get("contact:email"),
            facebook_url=tags.get("contact:facebook") or tags.get("facebook"),
            instagram_url=tags.get("contact:instagram") or tags.get("instagram"),
        )