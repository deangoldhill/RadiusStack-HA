"""DataUpdateCoordinator for RadiusStack-HA."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RadiusStackApi, RadiusStackApiError
from .const import (
    DOMAIN,
    DATA_OVERVIEW,
    DATA_LIVE,
    DATA_FAILED_AUTH,
    DATA_ACTIVE_SESSIONS,
    DATA_CONTAINERS,
)

_LOGGER = logging.getLogger(__name__)


class RadiusStackCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls all RadiusStack API endpoints on a single timer."""

    def __init__(self, hass: HomeAssistant, api: RadiusStackApi, scan_interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            results = await asyncio.gather(
                self.api.get_dashboard_overview(),
                self.api.get_live_stats(),
                self.api.get_failed_auth(),
                self.api.get_active_sessions(),
                self.api.get_containers(),
                return_exceptions=True,
            )
        except RadiusStackApiError as err:
            raise UpdateFailed(f"RadiusStack-HA API error: {err}") from err

        defaults = [{}, {}, {}, [], []]
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                _LOGGER.warning("RadiusStack-HA endpoint %d failed: %s", i, result)
                processed.append(defaults[i])
            else:
                processed.append(result)

        return {
            DATA_OVERVIEW:        processed[0],
            DATA_LIVE:            processed[1],
            DATA_FAILED_AUTH:     processed[2],
            DATA_ACTIVE_SESSIONS: processed[3],
            DATA_CONTAINERS:      processed[4],
        }
