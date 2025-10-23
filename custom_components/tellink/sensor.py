# 202510231200
"""Tellink sensor platform (Home Assistant 2025+ compatible)."""
from __future__ import annotations

import logging
from datetime import datetime, date
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up Tellink sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    username = entry.data.get("username")

    _LOGGER.debug("[%s] Setting up Tellink sensors", username)

    entities: list[SensorEntity] = [
        TellinkBalanceSensor(coordinator, username),
        TellinkStatusSensor(coordinator, username),
        TellinkUsernameSensor(coordinator, username),
        TellinkExpirySensor(coordinator, username),
    ]
    async_add_entities(entities)


# ----------------------------------------------------------------------
# Base class
# ----------------------------------------------------------------------

class BaseTellinkSensor(CoordinatorEntity, SensorEntity):
    """Base class for Tellink sensors."""

    def __init__(self, coordinator, username: str, sensor_type: str, icon: str):
        super().__init__(coordinator)
        self._username = username
        self._attr_name = f"Tellink {sensor_type} ({username})"
        self._attr_unique_id = f"tellink_{sensor_type.lower()}_{username}"
        self._attr_icon = icon

    @property
    def data(self) -> dict:
        """Shortcut to coordinator data."""
        return self.coordinator.data or {}


# ----------------------------------------------------------------------
# Individual sensors
# ----------------------------------------------------------------------

class TellinkBalanceSensor(BaseTellinkSensor):
    """Representation of the Tellink prepaid balance sensor."""

    _attr_native_unit_of_measurement = "€"

    def __init__(self, coordinator, username):
        super().__init__(coordinator, username, "Balance", "mdi:currency-eur")

    @property
    def native_value(self):
        """Return the current balance."""
        return self.data.get("balance")

    @property
    def icon_color(self) -> str | None:
        """Return dynamic color based on balance amount."""
        balance = self.data.get("balance")
        if balance is None:
            return None

        try:
            balance = float(balance)
        except (TypeError, ValueError):
            return None

        if balance < 2:
            return "red"
        elif balance < 4:
            return "orange"
        return "green"


class TellinkStatusSensor(BaseTellinkSensor):
    """Representation of the Tellink account status sensor."""

    def __init__(self, coordinator, username):
        super().__init__(coordinator, username, "Status", "mdi:information")

    @property
    def native_value(self):
        """Return the account status string."""
        return self.data.get("status")


class TellinkUsernameSensor(BaseTellinkSensor):
    """Representation of the Tellink username sensor."""

    def __init__(self, coordinator, username):
        super().__init__(coordinator, username, "Username", "mdi:account")

    @property
    def native_value(self):
        """Return the Tellink username."""
        return self.data.get("username")


class TellinkExpirySensor(BaseTellinkSensor):
    """Representation of the Tellink expiry date sensor."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator, username):
        super().__init__(coordinator, username, "Expiry", "mdi:calendar")

    @property
    def native_value(self) -> date | None:
        """Return expiry as a proper date object (required by HA 2025+)."""
        expiry_value = self.data.get("expiry")
        if not expiry_value:
            return None

        if isinstance(expiry_value, date):
            return expiry_value

        try:
            return datetime.fromisoformat(expiry_value).date()
        except Exception:
            _LOGGER.debug("[%s] Could not parse expiry value: %s", self._username, expiry_value)
            return None
