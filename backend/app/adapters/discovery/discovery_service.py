from __future__ import annotations

import uuid

from app.adapters.discovery.interfaces import DiscoveredBusiness, DiscoveryProvider
from app.core.config import Settings
from app.core.logging import get_logger
from app.models.business import Business, BusinessStatus
from app.repositories.business_repository import BusinessRepository
from app.services.validation.validation_service import WebsiteValidationService

logger = get_logger(__name__)


class DiscoveryService:
    def __init__(
        self,
        provider: DiscoveryProvider,
        business_repo: BusinessRepository,
        validation_service: WebsiteValidationService,
        settings: Settings,
    ) -> None:
        self._provider = provider
        self._businesses = business_repo
        self._validation = validation_service
        self._settings = settings

    async def discover_and_persist(
        self, *, organization_id: uuid.UUID | None, country: str, city: str, category: str, limit: int = 20
    ) -> list[Business]:
        found = await self._provider.search(country=country, city=city, category=category, limit=limit)
        logger.info("discovery_search_completed", city=city, category=category, count=len(found))

        persisted: list[Business] = []
        for item in found:
            business = await self._persist_one(organization_id, item)
            persisted.append(business)
        return persisted

    async def _persist_one(self, organization_id: uuid.UUID | None, item: DiscoveredBusiness) -> Business:
        record = {
            "name": item.name,
            "category": item.category,
            "phone": item.phone,
            "address": item.address,
            "city": item.city,
            "country": item.country,
            "latitude": item.latitude,
            "longitude": item.longitude,
            "website_url": item.website_url,
            "google_place_id": item.provider_place_id,
            "google_rating": item.google_rating,
            "review_count": item.review_count,
            "discovery_provider": self._settings.DISCOVERY_PROVIDER,
            "email": item.email,
            "facebook_url": item.facebook_url,
            "instagram_url": item.instagram_url,
        }
        business = await self._businesses.upsert_discovered(organization_id=organization_id, data=record)

        if business.website_url:
            result = await self._validation.validate(business.website_url)
            if result.is_valid:
                business.status = BusinessStatus.VALIDATED
                if result.final_url:
                    business.website_url = result.final_url
            logger.info(
                "business_validated",
                business_id=str(business.id),
                is_valid=result.is_valid,
                technologies=result.detected_technologies,
            )
        elif business.is_social_only_lead:
            # No website to validate/audit, but a real lead nonetheless —
            # flagged distinctly rather than silently left in "discovered"
            # limbo, so it's findable as its own opportunity category.
            logger.info(
                "social_only_lead_discovered",
                business_id=str(business.id),
                has_facebook=bool(business.facebook_url),
                has_instagram=bool(business.instagram_url),
                has_phone=bool(business.phone),
            )

        return business