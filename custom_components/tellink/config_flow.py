"""Config flow for Tellink Prepaid integration (HA 2025+)."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .api import TellinkAPI

_LOGGER = logging.getLogger(__name__)


class TellinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Tellink config flow."""

    VERSION = 2

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input["username"].strip()
            password = user_input["password"]

            api = TellinkAPI(username, password)

            try:
                _LOGGER.debug("Validating Tellink credentials for %s", username)
                data = await api.get_data()
                if not data:
                    errors["base"] = "invalid_auth"
                else:
                    await self.async_set_unique_id(username.lower())
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Tellink ({username})",
                        data=user_input,
                    )
            except TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error validating Tellink credentials: %s", err)
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required("username"): str,
                vol.Required("password"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_import(self, import_config: dict) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_config)


class TellinkOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Tellink options (polling intervals)."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Manage the Tellink options."""
        if user_input is not None:
            _LOGGER.debug("Options updated: %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        current_scan = options.get("scan_interval", 3600)
        current_retry = options.get("retry_interval", 3600)

        help_scan = "How often to update data from Tellink (in seconds). Default: 3600 (1 hour)."
        help_retry = "How long to wait before retrying after a failed update (in seconds). Default: 3600 (1 hour)."

        data_schema = vol.Schema(
            {
                vol.Optional(
                    "scan_interval",
                    description={"suggested_value": current_scan, "description": help_scan},
                    default=current_scan,
                ): int,
                vol.Optional(
                    "retry_interval",
                    description={"suggested_value": current_retry, "description": help_retry},
                    default=current_retry,
                ): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
