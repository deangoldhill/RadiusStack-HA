"""The RadiusStack Home Assistant integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RadiusStackApi
from .const import CONF_API_KEY, CONF_SCAN_INTERVAL, CONF_TENANT_ID, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import RadiusStackCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a selected RadiusStack scope from a config entry."""
    options = entry.options
    api = RadiusStackApi(
        entry.data[CONF_HOST], entry.data[CONF_PORT],
        options.get(CONF_API_KEY, entry.data[CONF_API_KEY]),
        options.get(CONF_TENANT_ID, entry.data.get(CONF_TENANT_ID)),
        async_get_clientsession(hass),
    )
    coordinator = RadiusStackCoordinator(hass, api, options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)))
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
