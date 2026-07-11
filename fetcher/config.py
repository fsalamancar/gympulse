"""Single source of truth for GymPulse. Swap gyms by editing GYM_ADDRESS + GYM_NAME."""
from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

# --- Swap gym here (address exactly as it appears on the Google Maps listing) ---
GYM_ADDRESS = "Fitness24Seven, Calle 24, Av. La Esperanza #43 A 90, Teusaquillo, Bogota"
GYM_NAME = "Fitness24Seven Quinta Paredes"
MAPS_URL = "https://www.google.com/maps/search/?api=1&query=" + GYM_ADDRESS.replace(" ", "+")

# --- Thresholds (percent full) ---
QUIET = 33      # <= QUIET  -> quiet (green)
MODERATE = 66   # <= MODERATE -> moderate (amber); above -> busy (red)

# --- Timezone (for "now" hour + fetched_at offset) ---
TZ = ZoneInfo("America/Bogota")

# --- Paths ---
CACHE_DIR = Path.home() / ".gympulse"
LATEST_JSON = CACHE_DIR / "latest.json"
HISTORY_CSV = CACHE_DIR / "history.csv"
APP_GROUP_JSON = (
    Path.home()
    / "Library/Group Containers/group.dev.francisco.gympulse/latest.json"
)
