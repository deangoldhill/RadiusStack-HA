"""Async API client for RadiusStack-HA."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=15)


class RadiusStackApiError(Exception):
    """Generic RadiusStack API error."""


class RadiusStackAuthError(RadiusStackApiError):
    """Authentication or authorisation error."""


class RadiusStackApi:
    """Read-only async wrapper around documented RadiusStack API endpoints."""

    def __init__(self, host: str, port: int, api_key: str, tenant_id: int | None, session: aiohttp.ClientSession) -> None:
        self._base = f"http://{host}:{port}"
        self._headers = {"X-API-Key": api_key, "Accept": "application/json"}
        if tenant_id is not None:
            self._headers["X-Tenant-ID"] = str(tenant_id)
        self._session = session

    async def _post(self, path: str) -> Any:
        try:
            async with self._session.post(f"{self._base}{path}", headers=self._headers, timeout=TIMEOUT) as response:
                if response.status in (401, 403):
                    raise RadiusStackAuthError("API key is invalid or lacks write access")
                response.raise_for_status()
                return await response.json()
        except RadiusStackApiError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise RadiusStackApiError(f"Request to {self._base}{path} failed: {err}") from err

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        try:
            async with self._session.get(f"{self._base}{path}", headers=self._headers, params=params, timeout=TIMEOUT) as response:
                if response.status in (401, 403):
                    raise RadiusStackAuthError("API key is invalid or lacks read-only access")
                response.raise_for_status()
                return await response.json()
        except RadiusStackApiError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise RadiusStackApiError(f"Request to {self._base}{path} failed: {err}") from err

    async def test_connection(self) -> bool:
        await self._get("/api/system/status")
        return True

    async def get_dashboard_overview(self) -> dict[str, Any]: return await self._get("/api/reports/dashboard-overview")
    async def get_live_stats(self) -> dict[str, Any]: return await self._get("/api/reports/live-stats")
    async def get_failed_auth(self) -> dict[str, Any]: return await self._get("/api/reports/failed-auth")
    async def get_active_sessions(self) -> list[dict[str, Any]]:
        data = await self._get("/api/sessions/active", {"limit": "500"})
        return data if isinstance(data, list) else []
    async def get_system_status(self) -> dict[str, Any]: return await self._get("/api/system/status")
    async def get_users(self) -> list[dict[str, Any]]:
        data = await self._get("/api/users")
        return data if isinstance(data, list) else []
    async def get_nas(self) -> list[dict[str, Any]]:
        data = await self._get("/api/nas")
        return data if isinstance(data, list) else []
    async def get_downstream_destinations(self) -> list[dict[str, Any]]:
        data = await self._get("/api/downstream-destinations")
        return data if isinstance(data, list) else []
    async def get_depleted_allocations(self) -> dict[str, Any]: return await self._get("/api/reports/depleted-allocations", {"view": "summary"})
    async def get_nas_stats(self, nas_id: int) -> dict[str, Any]: return await self._get(f"/api/nas/{nas_id}/stats", {"window": "day"})
    async def get_downstream_stats(self, destination_id: int) -> dict[str, Any]: return await self._get(f"/api/downstream-destinations/{destination_id}/stats", {"window": "day"})
    async def restart_container(self, container_name: str) -> dict[str, Any]: return await self._post(f"/api/system/restart/{container_name}")
