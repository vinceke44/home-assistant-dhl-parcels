# Changelog

## [0.1.1] - 2025-08-28
### Fixed
- Prevented blocking I/O during startup by deferring `cloudscraper.create_scraper()` initialization until first login.
- Eliminated warnings about `open`, `load_default_certs`, and `set_default_verify_paths` running in the event loop.

## [0.1.0] - 2025-08-26
### Added
- Initial release of DHL Parcels (Netherlands) integration.
- Login via Config Flow (email/password).
- Sensor for parcel count.
- Sensor exposing full parcel details as attributes.
- Options flow to adjust update interval.
