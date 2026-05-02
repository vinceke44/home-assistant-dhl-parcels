# Changelog

## [0.1.3] - 2026-05-02
### Added
- Fire HA events on parcel status changes: `dhl_parcels_new_parcel`, `dhl_parcels_status_changed`, `dhl_parcels_delivered`
- Events include parcel_id, barcode, sender, status, category, eta, and old/new values for change events
- First-run protection: no events fired on initial load to prevent flooding

## [0.1.2] - 2026-05-02
### Added
- Binary sensor `out_for_delivery`: on when any parcel has category `IN_DELIVERY`
- Binary sensor exposes count, barcode, sender, status, and eta per in-delivery parcel as attributes
- Shared `helpers.py` with `device_info()` used by all entity platforms

## [0.1.1] - 2026-05-02
### Fixed
- Removed duplicate top-level `cloudscraper` import
- Login now skips re-authentication when session is already active (`_logged_in` guard)
- Session flag correctly reset on 401/403 in both `login()` and `fetch_parcels()`
- `async_get_options_flow` moved inside `ConfigFlow` as `@staticmethod @callback` (was broken as module-level function)
- Fixed reauth flow fallthrough that could silently create a duplicate config entry
- Added `vol.Range(min=60)` validation on update interval option
- Added `DeviceInfo` to all sensors so entities appear under a single device
- Replaced `SensorDeviceClass.ENUM` with `SensorStateClass.MEASUREMENT` on count sensor

## [0.1.0] - 2025-08-26
### Added
- Initial release of DHL Parcels (Netherlands) integration
- Login via Config Flow (email/password)
- Sensor for parcel count
- Sensor exposing full parcel details as attributes
- Options flow to adjust update interval
