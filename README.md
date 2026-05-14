# DHL Parcels (Netherlands)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that tracks your DHL eCommerce Netherlands parcels, exposing sensors, binary sensors, and firing events when parcel status changes.

## Features

- **Parcel count sensor** — number of active (non-delivered) parcels
- **Parcel details sensor** — full parcel data as state attributes
- **Next expected delivery sensor** — earliest delivery window start as a `datetime`; `window_end` attribute for the full window
- **Out for delivery binary sensor** — `on` when any parcel has `IN_DELIVERY` category
- **Needs action binary sensor** — `on` when a parcel requires intervention (customs, problem, exception)
- **HA events** on parcel status/window changes — drive automations without polling
- **Configurable categories** — choose which parcel categories to track via the options flow
- **`dhl_parcels.refresh` service** — trigger an immediate poll from a dashboard button or automation

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

Use the cogwheel to configure the update interval (default 15 minutes) and which parcel categories to track. Use **Reconfigure** in the three-dot menu to update credentials.

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.dhl_parcels_parcel_count` | Sensor | Number of active parcels |
| `sensor.dhl_parcels_parcel_details` | Sensor | Active parcel count; full parcel list as attributes |
| `sensor.dhl_parcels_next_expected_delivery` | Sensor | Earliest delivery window start (`datetime`); `window_end` attribute for window end |
| `binary_sensor.dhl_parcels_out_for_delivery` | Binary sensor | `on` when any parcel has `IN_DELIVERY` category |
| `binary_sensor.dhl_parcels_needs_action` | Binary sensor | `on` when any parcel needs action (INTERVENTION, CUSTOMS, PROBLEM, EXCEPTION) |

## Events

All events include: `parcel_id`, `barcode`, `sender`, `status`, `category`, `eta`.

| Event | Fired when |
|-------|-----------|
| `dhl_parcels_new_parcel` | A new parcel appears |
| `dhl_parcels_status_changed` | Status or category changes; also includes `old/new_status`, `old/new_category`, `old/new_window_start`, `old/new_window_end` |
| `dhl_parcels_window_updated` | Delivery window narrows without a status change; includes old and new window fields |
| `dhl_parcels_delivered` | A parcel transitions to `DELIVERED` |

## Example automations

```yaml
# Notify when parcel is out for delivery
automation:
  - alias: "DHL onderweg melding"
    trigger:
      - platform: event
        event_type: dhl_parcels_status_changed
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.new_category == 'IN_DELIVERY' }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Pakket onderweg"
          message: >
            Pakket van {{ trigger.event.data.sender }} wordt bezorgd tussen
            {{ as_timestamp(trigger.event.data.new_window_start) | timestamp_custom('%H:%M') }} en
            {{ as_timestamp(trigger.event.data.new_window_end) | timestamp_custom('%H:%M') }}.

# Notify when delivered
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
