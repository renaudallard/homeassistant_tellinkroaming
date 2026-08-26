"""Initialize the Tellink Prepaid integration (HA 2025+, secure credential handling + Repairs)."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TellinkAPI, TellinkAuthError, TellinkError
from .const import DEFAULT_INTERVAL, DOMAIN, MAX_INTERVAL, MIN_INTERVAL
from .credentials import CredentialStore, credential_key, get_credential_store

_LOGGER = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Setup / Teardown
# ----------------------------------------------------------------------


def _interval(seconds: object) -> timedelta:
    """Return a sane polling interval for a value read from the options.

    The options flow rejects anything outside the allowed range, but entries
    saved by an older version can still hold a zero, which would turn the
    coordinator into a busy loop against the portal.
    """
    try:
        value = int(seconds)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        value = DEFAULT_INTERVAL
    return timedelta(seconds=min(max(value, MIN_INTERVAL), MAX_INTERVAL))


async def _async_stored_password(
    hass: HomeAssistant,
    entry: ConfigEntry,
    cred_store: CredentialStore,
    username: str | None,
) -> str | None:
    """Return the stored password, moving older placements to the current key.

    Earlier versions keyed the store by entry id, and before that left the
    password in the entry data, which Home Assistant writes to a world
    readable file. Either is moved into private storage on first sight.
    """
    key = credential_key(entry)

    cred = await cred_store.async_get(key)
    if cred:
        return cred.get("password")

    legacy = await cred_store.async_get(entry.entry_id)
    password = legacy.get("password") if legacy else entry.data.get("password")
    if not username or not password:
        return None

    await cred_store.async_save(key, username, password)
    if legacy and key != entry.entry_id:
        await cred_store.async_delete(entry.entry_id)
    if entry.data.get("password") is not None:
        hass.config_entries.async_update_entry(
            entry, data={k: v for k, v in entry.data.items() if k != "password"}
        )
        _LOGGER.debug("[%s] Password moved out of the config entry", username)

    return password


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tellink integration from a config entry."""
    username = entry.data.get("username")

    cred_store = get_credential_store(hass)
    password = await _async_stored_password(hass, entry, cred_store, username)

    # If creds are missing or corrupt, open a Repairs issue and trigger reauth.
    # ConfigEntryAuthFailed makes Home Assistant start the reauth flow itself.
    if not username or not password:
        _LOGGER.error("[%s] Missing/corrupt Tellink credentials", username or "unknown")
        raise ConfigEntryAuthFailed("Missing credentials")

    api = TellinkAPI(username, password)

    scan_interval = _interval(entry.options.get("scan_interval"))
    retry_interval = _interval(entry.options.get("retry_interval"))

    async def async_update_data():
        """Fetch data from Tellink with retry/backoff logic."""
        try:
            _LOGGER.debug("[%s] Fetching Tellink data", username)
            data = await api.get_data()
        except TellinkAuthError as err:
            # Ask the user for a new password instead of retrying forever.
            coordinator.update_interval = retry_interval
            raise ConfigEntryAuthFailed(str(err)) from err
        except TellinkError as err:
            _LOGGER.warning(
                "[%s] Update failed: %s; retrying in %s s",
                username,
                err,
                retry_interval.total_seconds(),
            )
            coordinator.update_interval = retry_interval
            raise UpdateFailed(err) from err

        coordinator.update_interval = scan_interval
        return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        config_entry=entry,
        name=f"tellink_{username}",
        update_method=async_update_data,
        update_interval=scan_interval,
    )

    # Reload when the user changes the intervals in the options flow. Home
    # Assistant drops the listener again if setup goes on to fail, so an entry
    # that never came up will not react to an options change; the setup retry
    # picks the new values up instead.
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Raises ConfigEntryAuthFailed, ConfigEntryError or ConfigEntryNotReady itself;
    # catching those here would hide a refused login from the reauth machinery.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    _LOGGER.info("[%s] Tellink integration successfully initialized", username)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Tellink integration."""
    username = entry.data.get("username")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        _LOGGER.debug("[%s] Unloaded Tellink integration", username)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up credentials when an entry is removed."""
    cred_store = get_credential_store(hass)
    await cred_store.async_delete(credential_key(entry))
    await cred_store.async_delete(entry.entry_id)
    _LOGGER.debug("[%s] Removed stored credentials", entry.data.get("username"))


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload Tellink config entry when options are updated."""
    _LOGGER.debug("Reloading Tellink config entry for %s", entry.data.get("username"))
    await hass.config_entries.async_reload(entry.entry_id)


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
        _LOGGER.info(
            "[%s] Migrating Tellink config entry from v%d to v2", username, new_version
        )
        new_version = 2

    # v2 -> v3 (placeholder)
    if new_version < 3:
        _LOGGER.info(
            "[%s] Migrating Tellink config entry from v%d to v3", username, new_version
        )
        new_version = 3

    # v3 -> v4: move password into private storage and remove from entry data
    if new_version < 4:
        _LOGGER.info(
            "[%s] Migrating Tellink config entry from v%d to v4 (secure creds)",
            username,
            new_version,
        )
        cred_store = get_credential_store(hass)
        pwd = data.pop("password", None)
        if data.get("username") and pwd:
            await cred_store.async_save(
                credential_key(config_entry), data["username"], pwd
            )
            _LOGGER.debug("[%s] Password moved to private storage", username)
        # Nothing to migrate means setup will raise ConfigEntryAuthFailed and
        # Home Assistant will ask for the password itself.
        new_version = 4

    if new_version != current_version:
        hass.config_entries.async_update_entry(
            config_entry,
            data=data,
            options=config_entry.options,
            version=new_version,
        )
        _LOGGER.debug(
            "[%s] Migration complete: v%d -> v%d",
            username,
            current_version,
            new_version,
        )
    else:
        _LOGGER.debug("[%s] No migration needed (v%d)", username, current_version)

    return True
