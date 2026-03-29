import logging
from typing import Any

import httpx
from app.core.config import settings
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MapboxFeature(BaseModel):
    id: str | None = None
    type: str
    geometry: dict[str, Any]
    properties: dict[str, Any]
    relevance: float | None = None


class MapboxResponse(BaseModel):
    type: str
    features: list[MapboxFeature]
    attribution: str | None = None


class MapboxClient:
    SEARCH_BOX_URL = "https://api.mapbox.com/search/searchbox/v1/forward"
    GEOCODING_V6_URL = "https://api.mapbox.com/search/geocode/v6/forward"

    def __init__(self, access_token: str | None = None) -> None:
        self.access_token = access_token or settings.MAPBOX_ACCESS_TOKEN
        if not self.access_token:
            logger.warning("Mapbox access token is missing.")

    async def _get(self, url: str, params: dict[str, Any]) -> MapboxResponse | None:
        """Base method for GET requests to Mapbox API."""
        if not self.access_token:
            return None

        params["access_token"] = self.access_token

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)

                if response.status_code == 422:
                    logger.error(f"[MAPBOX] 422 Unprocessable. URL: {url} | Body: {response.text}")
                    return None

                response.raise_for_status()
                data = response.json()
                return MapboxResponse(**data)
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[MAPBOX] HTTP error occurred: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            logger.error(f"[MAPBOX] An error occurred: {e}")

        return None

    async def search_box(
        self,
        query: str,
        country_code: str | None = None,
        proximity: str | None = None,
        types: str | None = "poi,address,street",
        limit: int = 5,
    ) -> MapboxResponse | None:
        """Search using Mapbox Search Box API v1."""
        params: dict[str, Any] = {"q": query, "limit": limit, "types": types}
        if country_code:
            params["country"] = country_code.lower()
        if proximity:
            params["proximity"] = proximity

        return await self._get(self.SEARCH_BOX_URL, params)

    async def geocode_v6(
        self,
        query: str,
        country_code: str | None = None,
        proximity: str | None = None,
        types: str | None = "street,address",
        limit: int = 5,
    ) -> MapboxResponse | None:
        """Search using Mapbox Geocoding API v6."""
        params: dict[str, Any] = {"q": query, "limit": limit, "types": types}
        if country_code:
            params["country"] = country_code.lower()
        if proximity:
            params["proximity"] = proximity

        return await self._get(self.GEOCODING_V6_URL, params)
