"""Button platform for RadiusStack-HA — restart containers."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import RadiusStackApi, RadiusStackApiError
from .const import DATA_CONTAINERS, DOMAIN
from .coordinator import RadiusStackCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RadiusStackCoordinator = hass.data[DOMAIN][entry.entry_id]
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]

    containers = coordinator.data.get(DATA_CONTAINERS, []) if coordinator.data else []
    entities = [
        RadiusStackRestartButton(coordinator.api, host, port, c["name"])
        for c in containers
        if c.get("name", "").startswith("radius_")
    ]
    async_add_entities(entities)


class RadiusStackRestartButton(ButtonEntity):
    """Button to restart a single RadiusStack container."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:restart"

    def __init__(
        self,
        api: RadiusStackApi,
        host: str,
        port: int,
        container_name: str,
    ) -> None:
        self._api = api
        self._container_name = container_name
        display = container_name.replace("radius_", "").replace("_", " ").title()
        self._attr_name = f"Restart {display}"
        self._attr_unique_id = f"radiusstack_{host}_{port}_restart_{container_name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{host}:{port}")},
            name=f"RadiusStack-HA ({host}:{port})",
            manufacturer="RadiusStack",
            model="FreeRADIUS Stack",
            configuration_url=f"http://{host}:{port}",
        )

    async def async_press(self) -> None:
        try:
            await self._api.restart_container(self._container_name)
            _LOGGER.info("RadiusStack-HA: restarted container %s", self._container_name)
        except RadiusStackApiError as err:
            _LOGGER.error(
                "RadiusStack-HA: failed to restart %s: %s",
                self._container_name,
                err,
            )
