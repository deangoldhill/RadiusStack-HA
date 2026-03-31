"""API client for RadiusStack-HA."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)
TIMEOUT = aiohttp.ClientTimeout(total=15)


class RadiusStackApiError(Exception):
    """Generic API error."""


class RadiusStackAuthError(RadiusStackApiError):
    """Authentication / authorisation error."""


class RadiusStackApi:
    """Async wrapper around the RadiusStack REST API."""

    def __init__(self, host: str, port: int, api_key: str, session: aiohttp.ClientSession) -> None:
        self._base = f"http://{host}:{port}"
        self._headers = {"X-API-Key": api_key, "Accept": "application/json"}
        self._session = session

    async def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self._base}{path}"
        try:
            async with self._session.get(
                url, headers=self._headers, params=params, timeout=TIMEOUT
            ) as resp:
                if resp.status == 401:
                    raise RadiusStackAuthError("Invalid API key")
                if resp.status == 403:
                    raise RadiusStackAuthError("Insufficient permissions")
                resp.raise_for_status()
                return await resp.json()
        except RadiusStackApiError:
            raise
        except aiohttp.ClientConnectorError as err:
            raise RadiusStackApiError(f"Cannot connect to {self._base}: {err}") from err
        except asyncio.TimeoutError as err:
            raise RadiusStackApiError(f"Timeout connecting to {self._base}") from err
        except Exception as err:
            raise RadiusStackApiError(f"Unexpected error: {err}") from err

    async def test_connection(self) -> bool:
        await self._get("/api/system/status")
        return True

    async def get_dashboard_overview(self) -> dict:
        return await self._get("/api/reports/dashboard-overview")

    async def get_live_stats(self) -> dict:
        return await self._get("/api/reports/live-stats")

    async def get_failed_auth(self) -> dict:
        return await self._get("/api/reports/failed-auth")

    async def get_active_sessions(self) -> list:
        data = await self._get("/api/sessions/active", {"limit": "500"})
        return data if isinstance(data, list) else []
