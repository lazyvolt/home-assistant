"""Constants for the LazyVolt integration."""

DOMAIN = "lazyvolt"
DEFAULT_CLOUD_URL = "http://host.docker.internal:80"
DEFAULT_EDGE_NAME = "Home Assistant"
UPDATE_INTERVAL = 30  # seconds

# Peblar integration domain
PEBLAR_DOMAIN = "peblar"

# Peblar entity translation keys
PEBLAR_SELECT_SMART_CHARGING = "smart_charging"
PEBLAR_SENSOR_ENERGY_TOTAL = "energy_total"
PEBLAR_SENSOR_ENERGY_SESSION = "energy_session"
PEBLAR_SENSOR_POWER_PHASE1 = "power_phase_1"
PEBLAR_SENSOR_POWER_PHASE2 = "power_phase_2"
PEBLAR_SENSOR_POWER_PHASE3 = "power_phase_3"
PEBLAR_SENSOR_CURRENT_PHASE1 = "current_phase_1"
PEBLAR_SENSOR_CURRENT_PHASE2 = "current_phase_2"
PEBLAR_SENSOR_CURRENT_PHASE3 = "current_phase_3"
PEBLAR_SENSOR_CP_STATE = "cp_state"
PEBLAR_SWITCH_CHARGE = "charge"
PEBLAR_SWITCH_FORCE_SINGLE_PHASE = "force_single_phase"

# Cloud mode → Peblar smart charging select option
CLOUD_MODE_TO_PEBLAR: dict[str, str] = {
    "SOLAR": "smart_solar",
    "MAX": "default",
}

# Peblar cp_state → Cloud charger_status enum value
PEBLAR_CP_STATE_TO_CLOUD_STATUS: dict[str, str] = {
    "charging": "charging",
    "suspended": "connected",
    "no_ev_connected": "no_vehicle",
    "error": "fault",
    "fault": "fault",
    "invalid": "fault",
}

# Config entry data keys
CONF_CLOUD_TOKEN = "cloud_token"
CONF_PEBLAR_ENTRY_ID = "peblar_entry_id"
