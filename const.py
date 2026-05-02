"""Constants for the DHL Parcels (NL) integration."""

DOMAIN = "dhl_parcels"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

LOGIN_URL = "https://my.dhlecommerce.nl/api/user/login"
PARCELS_URL = "https://my.dhlecommerce.nl/receiver-parcel-api/parcels"

# Categories from the original script considered "relevant"
CATEGORIES = (
    "PROBLEM",
    "CUSTOMS",
    "DATA_RECEIVED",
    "EXCEPTION",
    "INTERVENTION",
    "IN_DELIVERY",
    "LEG",
    "UNDERWAY",
    "UNKNOWN",
)

# Default update interval (in seconds)
DEFAULT_UPDATE_INTERVAL = 15 * 60  # 15 minutes

ATTR_COUNT = "count"
ATTR_PARCELS = "parcels"

# Events fired by the integration
EVENT_PARCEL_NEW = "dhl_parcels_new_parcel"
EVENT_PARCEL_STATUS_CHANGED = "dhl_parcels_status_changed"
EVENT_PARCEL_DELIVERED = "dhl_parcels_delivered"
