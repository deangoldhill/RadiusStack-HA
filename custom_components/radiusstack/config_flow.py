"""Config and options flow for RadiusStack-HA."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RadiusStackApi, RadiusStackApiError, RadiusStackAuthError
from .const import CONF_API_KEY, CONF_SCAN_INTERVAL, CONF_TENANT_ID, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN, MIN_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


# Zero is the UI-safe Global-scope sentinel.  Do not use a custom callable here:
# Home Assistant 2026 serializes config schemas for its frontend and rejects it.
TENANT_ID_VALIDATOR = vol.All(vol.Coerce(int), vol.Range(min=0))
STEP_USER_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(int, vol.Range(min=1, max=65535)),
    vol.Required(CONF_API_KEY): str,
    vol.Optional(CONF_TENANT_ID, default=0): TENANT_ID_VALIDATOR,
    vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL)),
})


class RadiusStackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one Global or tenant-scoped RadiusStack connection."""

    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = {**user_input, CONF_TENANT_ID: int(user_input.get(CONF_TENANT_ID, 0) or 0) or None}
            api = RadiusStackApi(user_input[CONF_HOST], user_input[CONF_PORT], user_input[CONF_API_KEY], user_input[CONF_TENANT_ID], async_get_clientsession(self.hass))
            try:
                await api.test_connection()
            except RadiusStackAuthError:
                errors["base"] = "invalid_auth"
            except RadiusStackApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected RadiusStack config-flow error")
                errors["base"] = "unknown"
            else:
                tenant = user_input.get(CONF_TENANT_ID)
                unique_id = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:tenant:{tenant if tenant is not None else 'global'}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                scope = f"Tenant {tenant}" if tenant is not None else "Global"
                return self.async_create_entry(title=f"RadiusStack ({scope})", data=user_input)
        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return RadiusStackOptionsFlow(config_entry)


class RadiusStackOptionsFlow(config_entries.OptionsFlow):
    """Change the API key, tenant scope, and polling interval."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = {**user_input, CONF_TENANT_ID: int(user_input.get(CONF_TENANT_ID, 0) or 0) or None}
            api = RadiusStackApi(self._config_entry.data[CONF_HOST], self._config_entry.data[CONF_PORT], user_input[CONF_API_KEY], user_input[CONF_TENANT_ID], async_get_clientsession(self.hass))
            try:
                await api.test_connection()
            except RadiusStackAuthError:
                errors["base"] = "invalid_auth"
            except RadiusStackApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="", data=user_input)
        options = self._config_entry.options
        schema = vol.Schema({
            vol.Required(CONF_API_KEY, default=options.get(CONF_API_KEY, self._config_entry.data.get(CONF_API_KEY, ""))): str,
            vol.Optional(CONF_TENANT_ID, default=options.get(CONF_TENANT_ID, self._config_entry.data.get(CONF_TENANT_ID)) or 0): TENANT_ID_VALIDATOR,
            vol.Required(CONF_SCAN_INTERVAL, default=options.get(CONF_SCAN_INTERVAL, self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL)),
        })
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
