"""Config flow for Tellink Prepaid integration (HA 2025+ secure)."""
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

    VERSION = 3  # bumped because we’re changing how credentials are stored

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
                    # Encrypt and store credentials securely
                    secret_password = await secrets.async_store_secret(
                        self.hass, f"tellink_{username}_password", password
                    )

                    await self.async_set_unique_id(username.lower())
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Tellink ({username})",
                        data={"username": username, "password": password},
                    )
            except TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error validating Tellink credentials: %s", err)
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
