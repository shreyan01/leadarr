"""Provider-agnostic business discovery contract.

``DiscoveryService`` (app/services/discovery) depends only on this Protocol.
Adding a new source (e.g. OpenStreetMap/Overpass, Yelp) means writing one
adapter class here and registering it in ``registry.py`` — no other file
changes, matching the pattern used for AI providers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class DiscoveredBusiness:
    name: str
    category: str
    website_url: str | None
    phone: str | None
    address: str | None
    city: str
    country: str
    latitude: float | None
    longitude: float | None
    provider_place_id: str | None
    google_rating: float | None
    review_count: int | None
    email: str | None = None
    facebook_url: str | None = None
    instagram_url: str | None = None


class DiscoveryProvider(Protocol):
    async def search(
        self, *, country: str, city: str, category: str, limit: int = 20
    ) -> list[DiscoveredBusiness]: ...