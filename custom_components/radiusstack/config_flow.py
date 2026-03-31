"""Config flow for RadiusStack-HA."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RadiusStackApi, RadiusStackApiError, RadiusStackAuthError
from .const import (
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(int, vol.Range(min=1, max=65535)),
    vol.Required(CONF_API_KEY): str,
    vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
        int, vol.Range(min=MIN_SCAN_INTERVAL)
    ),
})


class RadiusStackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for RadiusStack-HA."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = RadiusStackApi(
                host=user_input[CONF_HOST],
                port=user_input[CONF_PORT],
                api_key=user_input[CONF_API_KEY],
                session=session,
            )
            try:
                await api.test_connection()
            except RadiusStackAuthError:
                errors["base"] = "invalid_auth"
            except RadiusStackApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during RadiusStack-HA config flow")
                errors["base"] = "unknown"
            else:
                unique_id = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"RadiusStack-HA ({user_input[CONF_HOST]}:{user_input[CONF_PORT]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return RadiusStackOptionsFlow(config_entry)


class RadiusStackOptionsFlow(config_entries.OptionsFlow):
    """Options flow — change API key and poll interval after setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = RadiusStackApi(
                host=self._config_entry.data[CONF_HOST],
                port=self._config_entry.data[CONF_PORT],
                api_key=user_input[CONF_API_KEY],
                session=session,
            )
            try:
                await api.test_connection()
            except RadiusStackAuthError:
                errors["base"] = "invalid_auth"
            except RadiusStackApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Required(
                CONF_API_KEY,
                default=self._config_entry.options.get(
                    CONF_API_KEY, self._config_entry.data.get(CONF_API_KEY, "")
                ),
            ): str,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=self._config_entry.options.get(
                    CONF_SCAN_INTERVAL,
                    self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ),
            ): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL)),
        })

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
