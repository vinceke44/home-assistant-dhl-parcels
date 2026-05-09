"""Binary sensor platform for DHL Parcels (Netherlands)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ATTR_PARCELS
from .helpers import device_info

NEEDS_ACTION_CATEGORIES = frozenset({"INTERVENTION", "CUSTOMS", "PROBLEM", "EXCEPTION"})


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DHL Parcels binary sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([
        DHLParcelOutForDeliveryBinarySensor(coordinator, entry),
        DHLParcelNeedsActionBinarySensor(coordinator, entry),
    ])


class DHLParcelOutForDeliveryBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that is on when at least one parcel is out for delivery."""

    _attr_has_entity_name = True
    _attr_name = "Out for Delivery"
    _attr_icon = "mdi:package-variant-closed-deliver"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_out_for_delivery"
        self._attr_device_info = device_info(entry)

    @property
    def is_on(self) -> bool:
        """Return true when at least one parcel has category IN_DELIVERY."""
        parcels = self.coordinator.data.get(ATTR_PARCELS, [])
        return any(p.get("category") == "IN_DELIVERY" for p in parcels)

    @property
    def extra_state_attributes(self) -> dict:
        """Expose details of parcels currently out for delivery."""
        parcels = self.coordinator.data.get(ATTR_PARCELS, [])
        in_delivery = [p for p in parcels if p.get("category") == "IN_DELIVERY"]
        return {
            "count": len(in_delivery),
            "parcels": [
                {
                    "barcode": p.get("barcode"),
                    "sender": (p.get("sender") or {}).get("name"),
                    "status": p.get("status"),
                    "eta": (p.get("receivingTimeIndication") or {}).get("moment"),
                }
                for p in in_delivery
            ],
        }


class DHLParcelNeedsActionBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that is on when a parcel requires user action.

    Triggers on parcels that are explicitly flagged as intervenable by the
    DHL API, or whose category is one of INTERVENTION, CUSTOMS, PROBLEM,
    or EXCEPTION.
    """

    _attr_has_entity_name = True
    _attr_name = "Needs Action"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:package-variant-closed-alert"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_needs_action"
        self._attr_device_info = device_info(entry)

    @staticmethod
    def _needs_action(parcel: dict) -> bool:
        """Return True if this parcel requires user action.

        Purely category-based: intervenable=True is not used here because
        DHL sets it on all IN_DELIVERY parcels to indicate redirect is possible,
        which is not a problem state.
        """
        return parcel.get("category") in NEEDS_ACTION_CATEGORIES

    @property
    def is_on(self) -> bool:
        """Return true when at least one parcel needs action."""
        return any(
            self._needs_action(p)
            for p in self.coordinator.data.get(ATTR_PARCELS, [])
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Expose details of parcels that need action."""
        parcels = self.coordinator.data.get(ATTR_PARCELS, [])
        actionable = [p for p in parcels if self._needs_action(p)]
        return {
            "count": len(actionable),
            "parcels": [
                {
                    "barcode": p.get("barcode"),
                    "sender": (p.get("sender") or {}).get("name"),
                    "status": p.get("status"),
                    "category": p.get("category"),
                    "intervenable": p.get("intervenable", False),
                }
                for p in actionable
            ],
        }
