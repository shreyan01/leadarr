from __future__ import annotations

from app.adapters.discovery.google_places_provider import GooglePlacesDiscoveryProvider
from app.adapters.discovery.interfaces import DiscoveryProvider
from app.adapters.discovery.osm_provider import OsmDiscoveryProvider
from app.core.config import Settings, get_settings
from app.core.exceptions import ProviderError


def get_discovery_provider(settings: Settings | None = None) -> DiscoveryProvider:
    settings = settings or get_settings()
    match settings.DISCOVERY_PROVIDER:
        case "google_places":
            if not settings.GOOGLE_PLACES_API_KEY:
                raise ProviderError("GOOGLE_PLACES_API_KEY is not configured.")
            return GooglePlacesDiscoveryProvider(settings.GOOGLE_PLACES_API_KEY.get_secret_value())
        case "osm":
            # Free, keyless, global (including Europe) — see osm_provider.py
            # for the Nominatim+Overpass approach and its trade-offs vs.
            # Google Places (no ratings/reviews, inconsistent website coverage).
            return OsmDiscoveryProvider()
        case _:
            raise ProviderError(f"Unknown discovery provider '{settings.DISCOVERY_PROVIDER}'.")