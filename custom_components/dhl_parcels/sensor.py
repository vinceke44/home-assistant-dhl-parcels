"""Sensor platform for DHL Parcels (Netherlands)."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    ATTR_COUNT,
    ATTR_PARCELS,
)
from .helpers import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DHL Parcels sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([
        DHLParcelCountSensor(coordinator, entry),
        DHLParcelDetailsSensor(coordinator, entry),
        DHLNextDeliverySensor(coordinator, entry),
    ])


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
        self._attr_device_info = device_info(entry)

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
        self._attr_device_info = device_info(entry)

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


class DHLNextDeliverySensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the earliest expected delivery time among active parcels."""

    _attr_has_entity_name = True
    _attr_name = "Next Expected Delivery"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_next_delivery"
        self._attr_device_info = device_info(entry)

    @property
    def native_value(self) -> datetime | None:
        """Return the earliest ETA among active parcels, or None if none."""
        dates: list[datetime] = []
        for parcel in self.coordinator.data.get(ATTR_PARCELS, []):
            moment = (parcel.get("receivingTimeIndication") or {}).get("moment")
            if moment:
                parsed = dt_util.parse_datetime(moment)
                if parsed:
                    dates.append(parsed)
        return min(dates) if dates else None

    @property
    def extra_state_attributes(self) -> dict:
        """Expose all active parcels sorted by ETA."""
        upcoming = []
        for parcel in self.coordinator.data.get(ATTR_PARCELS, []):
            moment = (parcel.get("receivingTimeIndication") or {}).get("moment")
            if moment:
                upcoming.append({
                    "barcode": parcel.get("barcode"),
                    "sender": (parcel.get("sender") or {}).get("name"),
                    "eta": moment,
                    "category": parcel.get("category"),
                    "status": parcel.get("status"),
                })
        upcoming.sort(key=lambda x: x["eta"])
        return {"upcoming": upcoming}
