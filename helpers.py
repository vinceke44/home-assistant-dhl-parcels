"""Shared helpers for DHL Parcels integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return shared DeviceInfo for all DHL Parcels entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="DHL Parcels",
        manufacturer="DHL",
        model="eCommerce NL",
        configuration_url="https://my.dhlecommerce.nl",
    )
