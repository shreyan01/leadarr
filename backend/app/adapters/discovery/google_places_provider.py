"""Google Places API (New) adapter — Text Search.

Docs: https://developers.google.com/maps/documentation/places/web-service/text-search
Uses only publicly documented, non-authenticated-to-a-target-site search —
this queries Google's own index, never the discovered business's site.
"""
from __future__ import annotations

import httpx

from app.adapters.discovery.interfaces import DiscoveredBusiness
from app.core.exceptions import ProviderError

_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_FIELD_MASK = ",".join(
    [
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.internationalPhoneNumber",
        "places.websiteUri",
        "places.rating",
        "places.userRatingCount",
        "places.id",
        "places.primaryTypeDisplayName",
    ]
)


class GooglePlacesDiscoveryProvider:
    def __init__(self, api_key: str, timeout_s: float = 20.0) -> None:
        self._api_key = api_key
        self._timeout_s = timeout_s

    async def search(
        self, *, country: str, city: str, category: str, limit: int = 20
    ) -> list[DiscoveredBusiness]:
        query = f"{category} in {city}, {country}"
        payload = {"textQuery": query, "maxResultCount": min(limit, 20)}
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.post(_SEARCH_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Google Places search failed: {exc}") from exc

        results: list[DiscoveredBusiness] = []
        for place in data.get("places", []):
            location = place.get("location", {})
            results.append(
                DiscoveredBusiness(
                    name=place.get("displayName", {}).get("text", "Unknown"),
                    category=place.get("primaryTypeDisplayName", {}).get("text", category),
                    website_url=place.get("websiteUri"),
                    phone=place.get("internationalPhoneNumber"),
                    address=place.get("formattedAddress"),
                    city=city,
                    country=country,
                    latitude=location.get("latitude"),
                    longitude=location.get("longitude"),
                    provider_place_id=place.get("id"),
                    google_rating=place.get("rating"),
                    review_count=place.get("userRatingCount"),
                )
            )
        return results
