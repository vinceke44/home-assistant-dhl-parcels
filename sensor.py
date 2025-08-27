"""Sensor platform for DHL Parcels (Netherlands)."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ATTR_COUNT,
    ATTR_PARCELS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DHL Parcels sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities: list[SensorEntity] = [
        DHLParcelCountSensor(coordinator, entry),
        DHLParcelDetailsSensor(coordinator, entry),
    ]
    async_add_entities(entities)


class DHLParcelCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing the number of relevant parcels."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM  # Not strictly needed, but allows categorization
    _attr_name = "Parcel Count"
    _attr_icon = "mdi:package-variant-closed"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_parcel_count"

    @property
    def native_value(self) -> int:
        """Return the number of active parcels."""
        return self.coordinator.data.get(ATTR_COUNT, 0)


class DHLParcelDetailsSensor(CoordinatorEntity, SensorEntity):
    """Sensor exposing detailed parcel information as attributes."""

    _attr_has_entity_name = True
    _attr_name = "Parcel Details"
    _attr_icon = "mdi:package-variant"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_parcel_details"

    @property
    def native_value(self) -> str:
        """Return a summary value for UI (e.g., number of parcels)."""
        return f"{self.coordinator.data.get(ATTR_COUNT, 0)} parcels"

    @property
    def extra_state_attributes(self) -> dict:
        """Expose full parcel data as attributes."""
        return {
            ATTR_COUNT: self.coordinator.data.get(ATTR_COUNT, 0),
            ATTR_PARCELS: self.coordinator.data.get(ATTR_PARCELS, []),
        }
