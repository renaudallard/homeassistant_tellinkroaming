"""Config flow for Tellink Prepaid integration (HA 2025+) with secure cred migration + Reauth."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir

from .api import TellinkAPI, TellinkAuthError, TellinkConnectionError
from .const import DOMAIN, reauth_issue_id
from .credentials import credential_key, get_credential_store

_LOGGER = logging.getLogger(__name__)

# A zero or negative interval turns the coordinator into a busy loop.
MIN_INTERVAL = 60
MAX_INTERVAL = 86400


class TellinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Tellink config flow."""

    VERSION = 4  # Keep in sync with async_migrate_entry in __init__.py

    # --------------------------
    # Initial user setup
    # --------------------------
    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input["username"].strip()
            password = user_input["password"]

            api = TellinkAPI(username, password)

            try:
                _LOGGER.debug("Validating Tellink credentials for %s", username)
                await api.get_data()
            except TellinkConnectionError:
                errors["base"] = "cannot_connect"
            except TellinkAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error validating Tellink credentials")
                errors["base"] = "unknown"
            else:
                # Outside the try: _abort_if_unique_id_configured signals by raising.
                await self.async_set_unique_id(username.lower())
                self._abort_if_unique_id_configured()

                # Straight into private storage; the entry data never sees it.
                cred_store = get_credential_store(self.hass)
                await cred_store.async_save(username.lower(), username, password)

                return self.async_create_entry(
                    title=f"Tellink ({username})",
                    data={"username": username},
                    options={"scan_interval": 3600, "retry_interval": 3600},
                )

        data_schema = vol.Schema(
            {
                vol.Required("username"): str,
                vol.Required("password", description={"sensitive": True}): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    # --------------------------
    # Reauthentication
    # --------------------------
    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> TellinkOptionsFlowHandler:
        """Return the options flow handler."""
        return TellinkOptionsFlowHandler(config_entry)

    async def async_step_reauth(self, entry_data: dict) -> FlowResult:
        """Start reauth: ask the user for a new password."""
        self._reauth_username = entry_data.get("username")
        if not self._reauth_username:
            return self.async_abort(reason="unknown")
        self._reauth_entry = await self.async_set_unique_id(
            self._reauth_username.lower()
        )
        if not self._reauth_entry:
            return self.async_abort(reason="unknown")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        username = getattr(self, "_reauth_username", None)

        if user_input is not None and username:
            password = user_input["password"]
            api = TellinkAPI(username, password)
            try:
                _LOGGER.debug(
                    "Validating Tellink credentials during reauth for %s", username
                )
                await api.get_data()

                # Save to private credential store and clear the Repairs issue
                cred_store = get_credential_store(self.hass)
                await cred_store.async_save(
                    credential_key(self._reauth_entry), username, password
                )
                ir.async_delete_issue(
                    self.hass, DOMAIN, reauth_issue_id(self._reauth_entry.entry_id)
                )

                # The password lives in private storage, so nothing on the entry
                # changes and neither the update listener nor Home Assistant will
                # reload it on their own. Ask for the reload explicitly, or the
                # entry stays in SETUP_ERROR, which has no retry timer, and a
                # loaded entry keeps using the old password.
                self.hass.config_entries.async_schedule_reload(
                    self._reauth_entry.entry_id
                )
                return self.async_abort(reason="reauth_successful")
            except TellinkConnectionError:
                errors["base"] = "cannot_connect"
            except TellinkAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required("password", description={"sensitive": True}): str,
            }
        )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={"username": username or "unknown"},
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
                vol.Required(
                    "scan_interval", default=current.get("scan_interval", 3600)
                ): vol.All(int, vol.Range(min=MIN_INTERVAL, max=MAX_INTERVAL)),
                vol.Required(
                    "retry_interval", default=current.get("retry_interval", 3600)
                ): vol.All(int, vol.Range(min=MIN_INTERVAL, max=MAX_INTERVAL)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
