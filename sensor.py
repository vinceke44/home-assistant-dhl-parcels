"""Sensor platform for DHL Parcels (Netherlands)."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
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


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    """Shared device info for all DHL sensors."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="DHL Parcels",
        manufacturer="DHL",
        model="eCommerce NL",
        configuration_url="https://my.dhlecommerce.nl",
    )


class DHLParcelCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing the number of relevant parcels."""

    _attr_has_entity_name = True
    _attr_name = "Parcel Count"
    _attr_icon = "mdi:package-variant-closed"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "parcels"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_parcel_count"
        self._attr_device_info = _device_info(entry)

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
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_parcel_details"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int:
        """Return the parcel count as the state (usable in automations)."""
        return self.coordinator.data.get(ATTR_COUNT, 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Expose full parcel data as attributes."""
        return {
            ATTR_COUNT: self.coordinator.data.get(ATTR_COUNT, 0),
            ATTR_PARCELS: self.coordinator.data.get(ATTR_PARCELS, []),
        }
