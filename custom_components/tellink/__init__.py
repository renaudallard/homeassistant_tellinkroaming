# 202510231505
"""Initialize the Tellink Prepaid integration (HA 2025+, secure credential handling + Repairs)."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .api import TellinkAPI
from .credentials import get_credential_store

_LOGGER = logging.getLogger(__name__)

ISSUE_ID_REAUTH = "reauth_required"


# ----------------------------------------------------------------------
# Helpers: Repairs (issue registry)
# ----------------------------------------------------------------------

def _create_reauth_issue(hass: HomeAssistant, entry: ConfigEntry, username: str | None) -> None:
    """Create a Repairs issue to guide the user to reauthenticate (with Fix button)."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_ID_REAUTH,
        is_fixable=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key="reauth_required",
        translation_placeholders={
            "entry_title": entry.title or "Tellink",
            "username": username or "unknown",
        },
        # This 'data' block is passed to our repairs fix flow so we know which entry to fix
        data={"entry_id": entry.entry_id, "username": username or "unknown"},
        learn_more_url="https://my.home-assistant.io/redirect/config_flow_start?domain=tellink",
    )


def _delete_reauth_issue(hass: HomeAssistant) -> None:
    """Delete the reauth issue if it exists."""
    ir.async_delete_issue(hass, DOMAIN, ISSUE_ID_REAUTH)


# ----------------------------------------------------------------------
# Setup / Teardown
# ----------------------------------------------------------------------

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tellink integration from a config entry."""
    username = entry.data.get("username")

    cred_store = get_credential_store(hass)
    cred = await cred_store.async_get(entry.entry_id)
    password = cred.get("password") if cred else entry.data.get("password")

    # Opportunistic migration (if the migration step hasn't run yet)
    if username and entry.data.get("password"):
        await cred_store.async_save(entry.entry_id, username, entry.data["password"])
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "password": None},
            version=max(entry.version, 4),
        )
        password = entry.data["password"]

    # If creds are missing or corrupt, open a Repairs issue and trigger reauth
    if not username or not password:
        _LOGGER.error("[%s] Missing/corrupt Tellink credentials", username or "unknown")
        _create_reauth_issue(hass, entry, username)
        try:
            await hass.config_entries.async_start_reauth(entry)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not start reauth flow automatically; Repair issue created")
        raise ConfigEntryNotReady("Missing credentials")

    # Credentials are present; ensure any old issue is cleared
    _delete_reauth_issue(hass)

    api = TellinkAPI(username, password)

    scan_interval = timedelta(seconds=entry.options.get("scan_interval", 3600))
    retry_interval = timedelta(seconds=entry.options.get("retry_interval", 3600))

    async def async_update_data():
        """Fetch data from Tellink with retry/backoff logic."""
        try:
            _LOGGER.debug("[%s] Fetching Tellink data", username)
            data = await api.get_data()
            if not data:
                raise UpdateFailed("Empty or invalid data returned from Tellink API")

            coordinator.update_interval = scan_interval
            return data
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "[%s] Update failed: %s; retrying in %s s",
                username,
                err,
                retry_interval.total_seconds(),
            )
            coordinator.update_interval = retry_interval
            raise UpdateFailed(err)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"tellink_{username}",
        update_method=async_update_data,
        update_interval=scan_interval,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("[%s] Failed initial Tellink data refresh: %s", username, err)
        raise ConfigEntryNotReady from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    _LOGGER.info("[%s] Tellink integration successfully initialized", username)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Tellink integration."""
    username = entry.data.get("username")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.debug("[%s] Unloaded Tellink integration", username)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload Tellink config entry when options are updated."""
    username = entry.data.get("username")
    _LOGGER.debug("Reloading Tellink config entry for %s", username)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


# ----------------------------------------------------------------------
# Migration handler — keeps entry versions consistent
# ----------------------------------------------------------------------

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old Tellink entries to the latest version (4 with secure creds + Repairs)."""
    current_version = config_entry.version or 1
    data = dict(config_entry.data)
    new_version = current_version
    username = data.get("username", "unknown")

    # v1 -> v2 (placeholder)
    if new_version < 2:
        _LOGGER.info("[%s] Migrating Tellink config entry from v%d to v2", username, new_version)
        new_version = 2

    # v2 -> v3 (placeholder)
    if new_version < 3:
        _LOGGER.info("[%s] Migrating Tellink config entry from v%d to v3", username, new_version)
        new_version = 3

    # v3 -> v4: move password into private storage and remove from entry data
    if new_version < 4:
        _LOGGER.info("[%s] Migrating Tellink config entry from v%d to v4 (secure creds)", username, new_version)
        cred_store = get_credential_store(hass)
        pwd = data.pop("password", None)
        if data.get("username") and pwd:
            await cred_store.async_save(config_entry.entry_id, data["username"], pwd)
            _LOGGER.debug("[%s] Password moved to private storage", username)
        else:
            # No password found to migrate; create a Repair issue so user can reauth
            _create_reauth_issue(hass, config_entry, data.get("username"))
        new_version = 4

    if new_version != current_version:
        hass.config_entries.async_update_entry(
            config_entry,
            data=data,
            options=config_entry.options,
            version=new_version,
        )
        _LOGGER.debug("[%s] Migration complete: v%d -> v%d", username, current_version, new_version)
    else:
        _LOGGER.debug("[%s] No migration needed (v%d)", username, current_version)

    return True
