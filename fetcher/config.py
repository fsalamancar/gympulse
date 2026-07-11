"""Single source of truth for GymPulse. Swap gyms by editing GYM_ADDRESS + GYM_NAME.

Tune busyness by editing WEEKLY_CURVE to match how your gym actually feels.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

# --- Swap gym here (address is used only for the "Open in Google Maps" link) ---
GYM_ADDRESS = "Fitness24Seven, Calle 24, Av. La Esperanza #43 A 90, Teusaquillo, Bogota"
GYM_NAME = "Fitness24Seven Quinta Paredes"

# --- Live data (optional): scrape Google's Popular Times via your real Chrome. ---
# When True, fetcher tries the live scrape first and falls back to WEEKLY_CURVE if it
# fails. Needs Google Chrome installed + a one-time login (see scrape/README.md).
# GYM_SEARCH_QUERY is what gets typed into Google — the name Google knows the gym by.
USE_LIVE_SCRAPE = True
GYM_SEARCH_QUERY = "Fitness24Seven Quinta Paredes Bogota"
# quote_plus so special chars (e.g. the '#' in the address) don't break the URL.
MAPS_URL = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(GYM_ADDRESS)

# --- Thresholds (percent full) ---
QUIET = 33      # <= QUIET  -> quiet (green)
MODERATE = 66   # <= MODERATE -> moderate (amber); above -> busy (red)

# --- Your availability: hours you'd realistically START a workout ---
# "Best time to go" only recommends hours in [GO_START, GO_END). 7..22 means
# 7:00 a.m. through a 10:00 p.m. start (you're done by ~11 p.m.).
GO_START = 7
GO_END = 23

# --- Your gym's weekly busyness, 0-100 per hour, index 0..23 = hour of day ---
# This IS the data source (Google/paid APIs don't offer this for free). Edit each
# day to match your gym: 0 = empty, 100 = packed. You go there — you know the rhythm.
# Defaults model a 24/7 gym: morning + evening peaks, quiet mid-afternoon, dead overnight.
_WEEKDAY = [10, 6, 4, 4, 8, 22, 48, 62, 52, 38, 30, 33, 46, 42, 28, 30, 52, 74, 88, 84, 66, 48, 28, 16]
_SATURDAY = [14, 8, 5, 4, 6, 12, 22, 30, 45, 62, 78, 80, 72, 55, 45, 40, 42, 44, 40, 34, 28, 24, 20, 16]
_SUNDAY = [12, 7, 5, 4, 6, 10, 20, 28, 40, 55, 70, 74, 66, 50, 40, 36, 38, 40, 36, 30, 25, 22, 18, 14]
WEEKLY_CURVE: dict[str, list[int]] = {
    "Monday": _WEEKDAY,
    "Tuesday": _WEEKDAY,
    "Wednesday": _WEEKDAY,
    "Thursday": _WEEKDAY,
    "Friday": _WEEKDAY,
    "Saturday": _SATURDAY,
    "Sunday": _SUNDAY,
}

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
