"""Initialize the Tellink prepaid integration."""
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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tellink integration from a config entry."""
    username = entry.data.get("username")
    password = entry.data.get("password")

    api = TellinkAPI(username, password)

    # Retrieve polling intervals from options, with sensible defaults
    scan_interval = timedelta(seconds=entry.options.get("scan_interval", 3600))
    retry_interval = timedelta(seconds=entry.options.get("retry_interval", 3600))

    async def async_update_data():
        """Fetch data from Tellink with retry and error handling."""
        try:
            _LOGGER.debug("[%s] Fetching Tellink data", username)
            data = await api.get_data()
            if not data:
                raise UpdateFailed("Empty or invalid data returned from Tellink API")

            # Reset back to normal interval on successful fetch
            coordinator.update_interval = scan_interval
            return data

        except Exception as err:
            _LOGGER.warning(
                "[%s] Update failed: %s; retry in %s seconds",
                username,
                err,
                retry_interval.total_seconds(),
            )
            coordinator.update_interval = retry_interval
            raise UpdateFailed(err)

    # Create a shared coordinator per config entry
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

    # Store coordinator for this entry
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Forward to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    _LOGGER.info("[%s] Tellink integration successfully initialized", username)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Tellink integration."""
    username = entry.data.get("username")
    _LOGGER.debug("Unloading Tellink integration for %s", username)
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


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries to the latest version."""
    version = config_entry.version
    _LOGGER.debug("Starting migration for Tellink entry version %s", version)

    # Migration path from v1 → v1.1.0
    if version == 1:
        new_data = {**config_entry.data}
        new_options = {**config_entry.options}

        # No structural changes yet, but we future-proof the schema here.
        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            options=new_options,
            version=2,  # increment internal version to mark migrated
        )

        _LOGGER.info(
            "Successfully migrated Tellink config entry for %s to version 1.1.0",
            new_data.get("username", "unknown"),
        )
        return True

    _LOGGER.debug("No migration required for Tellink entry (version %s)", version)
    return True
