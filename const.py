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
