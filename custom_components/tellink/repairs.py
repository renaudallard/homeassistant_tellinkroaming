# 202510231505
"""Repairs fix flows for Tellink (adds the 'Fix' button for reauth)."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType
from homeassistant.components.repairs import RepairsFlow

from .const import DOMAIN
from .api import TellinkAPI
from .credentials import get_credential_store

_LOGGER = logging.getLogger(__name__)

ISSUE_ID_REAUTH = "reauth_required"


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
                data = await api.get_data()
                if not data:
                    errors["base"] = "invalid_auth"
                else:
                    # Save into private credential store
                    cred_store = get_credential_store(self.hass)
                    await cred_store.async_save(self._entry_id, self._username, password)

                    # Clear the issue and reload the entry
                    ir.async_delete_issue(self.hass, DOMAIN, ISSUE_ID_REAUTH)
                    entry = self.hass.config_entries.async_get_entry(self._entry_id)
                    if entry:
                        await self.hass.config_entries.async_reload(self._entry_id)

                    return self.async_create_entry(title="Reauthentication successful", data={})
            except TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
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
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)


async def async_create_fix_flow(hass: HomeAssistant, issue_id: str, data: dict | None):
    """Entry point for HA Repairs to create our Fix flow."""
    return TellinkRepairFlow(hass, issue_id, data)
