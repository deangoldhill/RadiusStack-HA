"""Constants for the RadiusStack-HA integration."""

DOMAIN = "radiusstack"
DEFAULT_PORT = 3000
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 5

CONF_API_KEY = "api_key"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"

# Coordinator data keys
DATA_OVERVIEW = "overview"
DATA_LIVE = "live"
DATA_FAILED_AUTH = "failed_auth"
DATA_ACTIVE_SESSIONS = "active_sessions"
