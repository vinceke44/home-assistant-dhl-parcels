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

from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    LOGIN_URL,
    PARCELS_URL,
    CATEGORIES,
    DEFAULT_UPDATE_INTERVAL,
    ATTR_COUNT,
    ATTR_PARCELS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


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
            return  # Already have an active session, skip re-login

        if self._scraper is None:
            self._scraper = cloudscraper.create_scraper()

        resp = self._scraper.post(
            LOGIN_URL,
            json={"email": email, "password": password},
            timeout=30,
        )

        if resp.status_code in (401, 403):
            self._logged_in = False
            raise DHLAuthError("Invalid email or password")

        if resp.status_code != 200:
            raise DHLApiError(f"Login failed: HTTP {resp.status_code}")

        self._logged_in = True

    def invalidate_session(self) -> None:
        """Mark session as expired so next login() call will re-authenticate."""
        self._logged_in = False

    def fetch_parcels(self) -> dict[str, Any]:
        """Fetch parcels JSON. Assumes session is authenticated."""
        if self._scraper is None:
            raise DHLAuthError("Not logged in, scraper not initialized")

        resp = self._scraper.get(PARCELS_URL, timeout=30)

        if resp.status_code in (401, 403):
            self._logged_in = False
            raise DHLAuthError("Session expired or unauthorized")

        if resp.status_code != 200:
            raise DHLApiError(f"Parcel fetch failed: HTTP {resp.status_code}")

        return resp.json()


class DHLParcelsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage DHL data fetching and parsing."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: DHLClient,
        email: str,
        password: str,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
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
            # Session may have expired server-side; invalidate and retry once
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

        parcels_all = raw.get("parcels", []) or []
        parcels_filtered = [p for p in parcels_all if p.get("category") in CATEGORIES]

        return {
            ATTR_COUNT: len(parcels_filtered),
            ATTR_PARCELS: parcels_filtered,
        }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DHL Parcels from a config entry."""
    email: str = entry.data[CONF_EMAIL]
    password: str = entry.data[CONF_PASSWORD]

    client = DHLClient()
    coordinator = DHLParcelsCoordinator(
        hass=hass,
        client=client,
        email=email,
        password=password,
        update_interval=(
            entry.options.get("update_interval", DEFAULT_UPDATE_INTERVAL)
            if entry.options
            else DEFAULT_UPDATE_INTERVAL
        ),
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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options or credentials change."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
