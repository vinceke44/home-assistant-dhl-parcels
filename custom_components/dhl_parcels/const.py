"""Constants for the DHL Parcels (NL) integration."""

DOMAIN = "dhl_parcels"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_CATEGORIES = "categories"

LOGIN_URL = "https://my.dhlecommerce.nl/api/user/login"
PARCELS_URL = "https://my.dhlecommerce.nl/receiver-parcel-api/parcels"

# Default active categories (excludes DELIVERED intentionally)
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

# All known categories with human-readable labels (for the options UI)
ALL_CATEGORIES: dict[str, str] = {
    "DATA_RECEIVED": "Data received (label created)",
    "UNDERWAY": "Underway",
    "LEG": "In transit (leg)",
    "IN_DELIVERY": "Out for delivery",
    "INTERVENTION": "Intervention required",
    "CUSTOMS": "Customs",
    "EXCEPTION": "Exception",
    "PROBLEM": "Problem",
    "UNKNOWN": "Unknown",
    "DELIVERED": "Delivered (off by default)",
}

# Default update interval (in seconds)
DEFAULT_UPDATE_INTERVAL = 15 * 60  # 15 minutes

ATTR_COUNT = "count"
ATTR_PARCELS = "parcels"

# Events fired by the integration
EVENT_PARCEL_NEW = "dhl_parcels_new_parcel"
EVENT_PARCEL_STATUS_CHANGED = "dhl_parcels_status_changed"
EVENT_PARCEL_DELIVERED = "dhl_parcels_delivered"
EVENT_PARCEL_WINDOW_UPDATED = "dhl_parcels_window_updated"
