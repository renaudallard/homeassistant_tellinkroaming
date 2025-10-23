# 202510231345
"""Private credential storage for Tellink using Home Assistant Store(private=True)."""
from __future__ import annotations

from typing import Any, Dict, Optional
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1
STORAGE_KEY = "tellink_credentials"


class CredentialStore:
    """Wrapper around HA Store to keep credentials per entry_id in private storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY, private=True)
        self._cache: Dict[str, Dict[str, Any]] | None = None

    async def _ensure_loaded(self) -> Dict[str, Dict[str, Any]]:
        if self._cache is None:
            self._cache = await self._store.async_load() or {}
        return self._cache

    async def async_get(self, entry_id: str) -> Optional[Dict[str, Any]]:
        data = await self._ensure_loaded()
        return data.get(entry_id)

    async def async_save(self, entry_id: str, username: str, password: str) -> None:
        data = await self._ensure_loaded()
        data[entry_id] = {"username": username, "password": password}
        await self._store.async_save(data)

    async def async_delete(self, entry_id: str) -> None:
        data = await self._ensure_loaded()
        if entry_id in data:
            data.pop(entry_id)
            await self._store.async_save(data)


def get_credential_store(hass: HomeAssistant) -> CredentialStore:
    """Get a singleton credential store instance."""
    key = "_tellink_credential_store"
    store: CredentialStore | None = hass.data.get(key)  # type: ignore[assignment]
    if store is None:
        store = CredentialStore(hass)
        hass.data[key] = store
    return store
