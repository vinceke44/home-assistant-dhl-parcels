"""Init for DHL Parcels (NL) custom component."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_CATEGORIES,
    LOGIN_URL,
    PARCELS_URL,
    CATEGORIES,
    DEFAULT_UPDATE_INTERVAL,
    ATTR_COUNT,
    ATTR_PARCELS,
    EVENT_PARCEL_NEW,
    EVENT_PARCEL_STATUS_CHANGED,
    EVENT_PARCEL_DELIVERED,
    EVENT_PARCEL_WINDOW_UPDATED,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


class DHLApiError(Exception):
    """Generic API error."""


class DHLAuthError(DHLApiError):
    """Authentication failed or expired."""


class DHLClient:
    """Thin synchronous client around cloudscraper for DHL eCommerce NL."""

    def __init__(self) -> None:
        self._scraper = None
        self._logged_in = False

    def login(self, email: str, password: str) -> None:
        """Authenticate and keep session cookies (blocking, run in executor)."""
        import cloudscraper

        if self._logged_in:
            return

        if self._scraper is None:
            self._scraper = cloudscraper.create_scraper()

        resp = self._scraper.post(
            LOGIN_URL,
            json={"email": email, "password": password},
            timeout=30,
        )

        if resp.status_code in (401, 403):
            self._logged_in = False
            _LOGGER.error("DHL login failed (%s): %s", resp.status_code, resp.text[:200])
            raise DHLAuthError(f"Login rejected ({resp.status_code})")

        if resp.status_code != 200:
            _LOGGER.error("DHL login unexpected status %s: %s", resp.status_code, resp.text[:200])
            raise DHLApiError(f"Login failed: HTTP {resp.status_code}")

        self._logged_in = True

    def invalidate_session(self) -> None:
        """Mark session as expired so next login() call will re-authenticate."""
        self._logged_in = False

    def fetch_parcels(self) -> dict[str, Any]:
        """Fetch parcels JSON. Assumes session is authenticated."""
        if self._scraper is None:
            raise DHLAuthError("Not logged in, scraper not initialized")

        headers = {
            "Origin": "https://my.dhlecommerce.nl",
            "Referer": "https://my.dhlecommerce.nl/",
        }

        # DHL requires XSRF-TOKEN as a header as well as a cookie
        xsrf = next(
            (c.value for c in self._scraper.cookies if c.name == "XSRF-TOKEN"),
            None,
        )
        if xsrf:
            headers["X-XSRF-TOKEN"] = xsrf

        # Also send access_token as Bearer in case the API prefers header auth
        access_token = next(
            (c.value for c in self._scraper.cookies if c.name == "access_token"),
            None,
        )
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        resp = self._scraper.get(PARCELS_URL, headers=headers, timeout=30)

        if resp.status_code in (401, 403):
            self._logged_in = False
            _LOGGER.error("DHL parcel fetch failed (%s): %s", resp.status_code, resp.text[:200])
            raise DHLAuthError(f"Parcel fetch rejected ({resp.status_code})")

        if resp.status_code != 200:
            _LOGGER.error("DHL parcel fetch unexpected status %s: %s", resp.status_code, resp.text[:200])
            raise DHLApiError(f"Parcel fetch failed: HTTP {resp.status_code}")

        return resp.json()


def _parcel_event_data(parcel: dict[str, Any]) -> dict[str, Any]:
    """Extract the fields we want to include in every parcel event."""
    return {
        "parcel_id": parcel.get("parcelId"),
        "barcode": parcel.get("barcode"),
        "sender": (parcel.get("sender") or {}).get("name"),
        "status": parcel.get("status"),
        "category": parcel.get("category"),
        "eta": (parcel.get("receivingTimeIndication") or {}).get("moment"),
    }


class DHLParcelsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage DHL data fetching and parsing."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: DHLClient,
        email: str,
        password: str,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
        categories: tuple[str, ...] = CATEGORIES,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="DHL Parcels Coordinator",
            update_interval=timedelta(seconds=update_interval),
        )
        self._client = client
        self._email = email
        self._password = password
        self._categories = frozenset(categories)
        self._previous_parcels: dict[str, dict[str, Any]] | None = None

    async def _async_login_if_needed(self) -> None:
        """Ensure we're authenticated; perform login in executor if not already."""
        def _login_blocking() -> None:
            self._client.login(self._email, self._password)

        await self.hass.async_add_executor_job(_login_blocking)

    async def _async_fetch(self) -> dict[str, Any]:
        """Fetch the raw parcels in executor."""
        def _fetch_blocking() -> dict[str, Any]:
            return self._client.fetch_parcels()

        return await self.hass.async_add_executor_job(_fetch_blocking)

    def _fire_parcel_events(self, all_parcels: list[dict[str, Any]]) -> None:
        """Compare current parcels against previous state and fire change events.

        Skipped on the first run to avoid flooding HA with events for parcels
        that were already in their current state before HA started.
        """
        if self._previous_parcels is None:
            return

        current: dict[str, dict[str, Any]] = {
            p["parcelId"]: p for p in all_parcels if p.get("parcelId")
        }

        for parcel_id, parcel in current.items():
            if parcel_id not in self._previous_parcels:
                if parcel.get("category") != "DELIVERED":
                    _LOGGER.debug("New parcel detected: %s", parcel.get("barcode"))
                    self.hass.bus.async_fire(
                        EVENT_PARCEL_NEW,
                        _parcel_event_data(parcel),
                    )

        for parcel_id, parcel in current.items():
            prev = self._previous_parcels.get(parcel_id)
            if prev is None:
                continue

            old_status = prev.get("status")
            new_status = parcel.get("status")
            old_category = prev.get("category")
            new_category = parcel.get("category")

            old_window_start = (prev.get("receivingTimeIndication") or {}).get("start") or (prev.get("receivingTimeIndication") or {}).get("moment")
            new_window_start = (parcel.get("receivingTimeIndication") or {}).get("start") or (parcel.get("receivingTimeIndication") or {}).get("moment")
            old_window_end = (prev.get("receivingTimeIndication") or {}).get("end")
            new_window_end = (parcel.get("receivingTimeIndication") or {}).get("end")

            window_changed = (
                old_window_start != new_window_start
                or old_window_end != new_window_end
            )

            if old_status == new_status and old_category == new_category and not window_changed:
                continue

            event_data = {
                **_parcel_event_data(parcel),
                "old_status": old_status,
                "new_status": new_status,
                "old_category": old_category,
                "new_category": new_category,
            }

            if new_category == "DELIVERED" and old_category != "DELIVERED":
                _LOGGER.debug("Parcel delivered: %s", parcel.get("barcode"))
                self.hass.bus.async_fire(EVENT_PARCEL_DELIVERED, event_data)
            elif window_changed and old_status == new_status and old_category == new_category:
                _LOGGER.debug(
                    "Parcel window updated: %s (%s–%s → %s–%s)",
                    parcel.get("barcode"),
                    old_window_start, old_window_end,
                    new_window_start, new_window_end,
                )
                self.hass.bus.async_fire(EVENT_PARCEL_WINDOW_UPDATED, {
                    **event_data,
                    "old_window_start": old_window_start,
                    "old_window_end": old_window_end,
                    "new_window_start": new_window_start,
                    "new_window_end": new_window_end,
                })
            else:
                _LOGGER.debug(
                    "Parcel status changed: %s (%s → %s)",
                    parcel.get("barcode"),
                    old_status,
                    new_status,
                )
                self.hass.bus.async_fire(EVENT_PARCEL_STATUS_CHANGED, {
                    **event_data,
                    "old_window_start": old_window_start,
                    "old_window_end": old_window_end,
                    "new_window_start": new_window_start,
                    "new_window_end": new_window_end,
                })

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch, filter, and shape the data for entities."""
        try:
            await self._async_login_if_needed()
        except DHLAuthError as err:
            raise ConfigEntryAuthFailed from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Login error: {err}") from err

        try:
            raw = await self._async_fetch()
        except DHLAuthError:
            _LOGGER.info("DHL session expired, attempting re-login")
            self._client.invalidate_session()
            try:
                await self._async_login_if_needed()
                raw = await self._async_fetch()
            except DHLAuthError as err2:
                raise ConfigEntryAuthFailed from err2
            except Exception as err2:  # noqa: BLE001
                raise UpdateFailed(f"Fetch after reauth failed: {err2}") from err2
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Fetch error: {err}") from err

        all_parcels: list[dict[str, Any]] = raw.get("parcels", []) or []

        self._fire_parcel_events(all_parcels)

        self._previous_parcels = {
            p["parcelId"]: p for p in all_parcels if p.get("parcelId")
        }

        parcels_filtered = [
            p for p in all_parcels if p.get("category") in self._categories
        ]

        return {
            ATTR_COUNT: len(parcels_filtered),
            ATTR_PARCELS: parcels_filtered,
        }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DHL Parcels from a config entry."""
    email: str = entry.data[CONF_EMAIL]
    password: str = entry.data[CONF_PASSWORD]

    options = entry.options or {}
    selected_categories = tuple(options.get(CONF_CATEGORIES, list(CATEGORIES)))

    client = DHLClient()
    coordinator = DHLParcelsCoordinator(
        hass=hass,
        client=client,
        email=email,
        password=password,
        update_interval=options.get("update_interval", DEFAULT_UPDATE_INTERVAL),
        categories=selected_categories,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        raise
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady(f"Unable to set up DHL Parcels: {err}") from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _handle_refresh(call) -> None:  # noqa: ANN001
        """Handle the refresh service call."""
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "refresh", _handle_refresh)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # Only remove the service when the last entry is unloaded
        if not hass.data.get(DOMAIN):
            hass.services.async_remove(DOMAIN, "refresh")
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options or credentials change."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry to the current version.

    This is called by HA when entry.version < ConfigFlow.VERSION.
    Each migration block should be an if/elif chain that upgrades
    one version at a time, updating entry.version as it goes.

    Example for a future v1 → v2 migration:

        if entry.version == 1:
            new_data = {**entry.data, "new_field": "default_value"}
            hass.config_entries.async_update_entry(
                entry, data=new_data, version=2
            )

    Always return True on success, False if migration is not possible
    (which will disable the entry and show an error to the user).
    """
    _LOGGER.debug(
        "Migrating DHL Parcels config entry from version %s to %s",
        entry.version,
        ConfigFlow.VERSION,
    )

    # No migrations needed yet — we are at version 1 and no older
    # entries exist. Add migration blocks here when VERSION is bumped.

    _LOGGER.info(
        "DHL Parcels config entry migration to version %s successful",
        entry.version,
    )
    return True
