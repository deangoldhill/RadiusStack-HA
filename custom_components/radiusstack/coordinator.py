"""Coordinator that collects read-only RadiusStack telemetry."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RadiusStackApi, RadiusStackApiError
from .const import DATA_ACTIVE_SESSIONS, DATA_DEPLETED, DATA_DOWNSTREAM, DATA_DOWNSTREAM_STATS, DATA_FAILED_AUTH, DATA_LIVE, DATA_NAS, DATA_NAS_STATS, DATA_OVERVIEW, DATA_SYSTEM_STATUS, DATA_USERS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class RadiusStackCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the selected RadiusStack Global or tenant API scope."""

    def __init__(self, hass: HomeAssistant, api: RadiusStackApi, scan_interval: int) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=scan_interval))
        self.api = api

    async def _collect_optional(self, name: str, coroutine: Any, default: Any) -> Any:
        try:
            return await coroutine
        except RadiusStackApiError as err:
            _LOGGER.debug("RadiusStack optional endpoint %s is unavailable: %s", name, err)
            return default

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            overview = await self.api.get_dashboard_overview()
        except RadiusStackApiError as err:
            raise UpdateFailed(f"RadiusStack API error: {err}") from err

        live, failed_auth, sessions, status, users, nas, downstream, depleted = await asyncio.gather(
            self._collect_optional("live stats", self.api.get_live_stats(), {}),
            self._collect_optional("failed auth", self.api.get_failed_auth(), {}),
            self._collect_optional("active sessions", self.api.get_active_sessions(), []),
            self._collect_optional("system status", self.api.get_system_status(), {}),
            self._collect_optional("users", self.api.get_users(), []),
            self._collect_optional("NAS", self.api.get_nas(), []),
            self._collect_optional("downstream destinations", self.api.get_downstream_destinations(), []),
            self._collect_optional("depleted allocations", self.api.get_depleted_allocations(), {}),
        )
        nas_stats_results = await asyncio.gather(*[
            self._collect_optional(f"NAS {item.get('id')}", self.api.get_nas_stats(int(item["id"])), {})
            for item in nas if item.get("id") is not None
        ])
        downstream_stats_results = await asyncio.gather(*[
            self._collect_optional(f"downstream destination {item.get('id')}", self.api.get_downstream_stats(int(item["id"])), {})
            for item in downstream if item.get("id") is not None
        ])
        return {
            DATA_OVERVIEW: overview, DATA_LIVE: live, DATA_FAILED_AUTH: failed_auth,
            DATA_ACTIVE_SESSIONS: sessions, DATA_SYSTEM_STATUS: status, DATA_USERS: users,
            DATA_NAS: nas, DATA_NAS_STATS: {str(item["id"]): result for item, result in zip(nas, nas_stats_results, strict=False) if item.get("id") is not None},
            DATA_DOWNSTREAM: downstream, DATA_DOWNSTREAM_STATS: {str(item["id"]): result for item, result in zip(downstream, downstream_stats_results, strict=False) if item.get("id") is not None},
            DATA_DEPLETED: depleted,
        }
