# 202510231345
"""Config flow for Tellink Prepaid integration (HA 2025+) with secure cred migration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .api import TellinkAPI

_LOGGER = logging.getLogger(__name__)


class TellinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Tellink config flow."""

    VERSION = 4  # Keep in sync with async_migrate_entry in __init__.py

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

                    # Store password temporarily in entry data; migration will move it to private storage (v4)
                    return self.async_create_entry(
                        title=f"Tellink ({username})",
                        data={"username": username, "password": password},
                        options={"scan_interval": 3600, "retry_interval": 3600},
                    )
            except TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error validating Tellink credentials")
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required("username"): str,
                vol.Required("password", description={"sensitive": True}): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )


# ----------------------------------------------------------------------
# Options Flow (scan_interval / retry_interval)
# ----------------------------------------------------------------------

class TellinkOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Tellink options."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Manage the Tellink options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._entry.options
        schema = vol.Schema(
            {
                vol.Required("scan_interval", default=current.get("scan_interval", 3600)): int,
                vol.Required("retry_interval", default=current.get("retry_interval", 3600)): int,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


async def async_get_options_flow(config_entry: config_entries.ConfigEntry):
    """Return the options flow handler."""
    return TellinkOptionsFlowHandler(config_entry)
