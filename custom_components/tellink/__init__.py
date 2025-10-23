# 202510231305
"""Initialize the Tellink Prepaid integration (HA 2025+, safe credential handling)."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .api import TellinkAPI

_LOGGER = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Setup / Teardown
# ----------------------------------------------------------------------

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tellink integration from a config entry."""
    username = entry.data.get("username")
    password = entry.data.get("password")

    if not username or not password:
        _LOGGER.error("[%s] Missing Tellink credentials in config entry", username)
        raise ConfigEntryNotReady("Missing credentials")

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
        except Exception as err:
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
    except Exception as err:
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
    """Migrate old Tellink entries to the latest version (3)."""
    current_version = config_entry.version or 1
    data = dict(config_entry.data)  # keep as-is; adjust here if schema changes
    new_version = current_version
    username = data.get("username", "unknown")

    # v1 -> v2 (placeholder)
    if new_version < 2:
        _LOGGER.info("[%s] Migrating Tellink config entry from v%d to v2", username, new_version)
        new_version = 2

    # v2 -> v3 (no schema change today; reserved for future fields)
    if new_version < 3:
        _LOGGER.info("[%s] Migrating Tellink config entry from v%d to v3", username, new_version)
        new_version = 3

    # Apply version bump via async_update_entry (do NOT assign to config_entry.version directly)
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
