# DHL Parcels (Netherlands)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that tracks your DHL eCommerce Netherlands parcels, exposing sensors, a binary sensor, and firing events when parcel status changes.

## Features

- **Parcel count sensor** — number of active (non-delivered) parcels
- **Parcel details sensor** — full parcel data as state attributes
- **Out for delivery binary sensor** — `on` when at least one parcel is in `IN_DELIVERY` state, with per-parcel details as attributes
- **HA events** on parcel status changes — drive automations without polling template sensors

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → click the three dots (top right) → **Custom repositories**
3. Add `https://github.com/vinceke44/home-assistant-dhl-parcels` as category **Integration**
4. Search for **DHL Parcels** and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/dhl_parcels` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

Go to **Settings → Devices & Services → Add Integration** and search for **DHL Parcels**. Enter your DHL eCommerce Netherlands account email and password.

The update interval defaults to 15 minutes and can be changed via the integration's options.

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.dhl_parcels_parcel_count` | Sensor | Number of active parcels |
| `sensor.dhl_parcels_parcel_details` | Sensor | Active parcel count; full parcel list as attributes |
| `binary_sensor.dhl_parcels_out_for_delivery` | Binary sensor | `on` when any parcel has `IN_DELIVERY` category |

## Events

The integration fires events on the HA event bus when parcel state changes. All events include: `parcel_id`, `barcode`, `sender`, `status`, `category`, `eta`.

| Event | Fired when |
|-------|-----------|
| `dhl_parcels_new_parcel` | A new parcel appears that is not yet delivered |
| `dhl_parcels_status_changed` | An existing parcel changes status or category |
| `dhl_parcels_delivered` | A parcel transitions to `DELIVERED` |

`dhl_parcels_status_changed` and `dhl_parcels_delivered` also include `old_status`, `new_status`, `old_category`, `new_category`.

### Example automation

```yaml
automation:
  - alias: "DHL pakket bezorgd"
    trigger:
      - platform: event
        event_type: dhl_parcels_delivered
    action:
      - service: notify.mobile_app
        data:
          title: "Pakket bezorgd"
          message: "Pakket van {{ trigger.event.data.sender }} is bezorgd."
```
