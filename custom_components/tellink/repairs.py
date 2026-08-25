"""Repairs fix flows for Tellink (adds the 'Fix' button for reauth)."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import TellinkAPI, TellinkAuthError, TellinkConnectionError
from .const import DOMAIN
from .credentials import credential_key, get_credential_store

_LOGGER = logging.getLogger(__name__)


class TellinkRepairFlow(RepairsFlow):
    """Repairs flow to reauthenticate Tellink credentials."""

    def __init__(self, hass: HomeAssistant, issue_id: str, data: dict | None) -> None:
        super().__init__()
        self.hass = hass
        self.issue_id = issue_id
        self._entry_id: str | None = (data or {}).get("entry_id")
        self._username: str | None = (data or {}).get("username")

    async def async_step_init(self, user_input: dict | None = None):
        """Ask user for the new password and validate it."""
        errors: dict[str, str] = {}

        if user_input is not None:
            password: str = user_input["password"]

            if not self._entry_id or not self._username:
                _LOGGER.error("Repairs flow missing context (entry_id/username)")
                return self.async_abort(reason="unknown")

            # Validate credentials via API
            try:
                api = TellinkAPI(self._username, password)
                await api.get_data()

                # Save into private credential store
                entry = self.hass.config_entries.async_get_entry(self._entry_id)
                if not entry:
                    _LOGGER.error(
                        "Repairs flow: config entry %s is gone", self._entry_id
                    )
                    return self.async_abort(reason="unknown")

                cred_store = get_credential_store(self.hass)
                await cred_store.async_save(
                    credential_key(entry), self._username, password
                )

                # Clear the issue and reload the entry
                ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)
                await self.hass.config_entries.async_reload(self._entry_id)

                return self.async_create_entry(
                    title="Reauthentication successful", data={}
                )
            except TellinkConnectionError:
                errors["base"] = "cannot_connect"
            except TellinkAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during Tellink repairs reauth")
                errors["base"] = "unknown"

        # Use HA selectors for a password-style field (hidden entry)
        schema = vol.Schema(
            {
                vol.Required("password"): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                )
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={"username": self._username or "unknown"},
        )


async def async_create_fix_flow(hass: HomeAssistant, issue_id: str, data: dict | None):
    """Entry point for HA Repairs to create our Fix flow."""
    return TellinkRepairFlow(hass, issue_id, data)
