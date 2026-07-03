from __future__ import annotations

from app.adapters.discovery.google_places_provider import GooglePlacesDiscoveryProvider
from app.adapters.discovery.interfaces import DiscoveryProvider
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
            # OpenStreetMap/Overpass adapter is a natural zero-cost fallback;
            # add app/adapters/discovery/osm_provider.py and one case here.
            raise ProviderError("Discovery provider 'osm' adapter not yet implemented.")
        case _:
            raise ProviderError(f"Unknown discovery provider '{settings.DISCOVERY_PROVIDER}'.")
