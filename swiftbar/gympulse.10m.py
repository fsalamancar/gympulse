#!/usr/bin/env python3
# <bitbar.title>GymPulse</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.desc>Gym busyness in the menu bar</bitbar.desc>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
"""Read-only SwiftBar plugin. Renders ~/.gympulse/latest.json. Never crashes the bar."""
from __future__ import annotations

import base64
import json
import time
from datetime import datetime
from pathlib import Path

HOME = Path.home()
REPO = Path(__file__).resolve().parent.parent
CACHE = HOME / ".gympulse" / "latest.json"
HISTOGRAM = HOME / ".gympulse" / "histogram.png"
ICONS = REPO / "assets" / "icons"
MAPS_FALLBACK = "https://www.google.com/maps"
BLOCKS = " ▁▂▃▄▅▆▇█"

def _read_b64(stem: str, icons_dir: Path) -> str:
    """Base64 an icon by file stem. Returns '' on any read problem so no caller —
    including the last-resort error handler — can be crashed by a bad icon file."""
    p = icons_dir / f"{stem}.png"
    try:
        return base64.b64encode(p.read_bytes()).decode()
    except OSError:
        return ""


def _hist_b64() -> str:
    """Base64 the histogram PNG (written by the fetcher). '' if absent (fail-soft)."""
    try:
        return base64.b64encode(HISTOGRAM.read_bytes()).decode()
    except OSError:
        return ""


def _menubar_stem(payload: dict) -> str:
    """Pick the monochrome menu-bar glyph. Normally a horizontal gauge that fills
    with busyness (live if present, else the forecast for this hour) in 10% steps:
    fill_0 (empty outline) .. fill_100 (solid). A real error shows the cracked glyph."""
    if not payload.get("ok", True):
        return "template_error"
    pct = payload.get("live")
    if pct is None:
        pct = payload.get("typical_now")
    if pct is None:
        return "fill_0"
    step = max(0, min(100, int(pct / 10.0 + 0.5) * 10))
    return f"fill_{step}"


def _bar(v: int) -> str:
    return BLOCKS[min(len(BLOCKS) - 1, round(v / 100 * (len(BLOCKS) - 1)))]


def render(payload: dict, icons_dir: Path, cache_age_min: float) -> str:
    live = payload.get("live")
    lines: list[str] = []

    # --- Menu bar: a monochrome dumbbell gauge that fills horizontally with
    #     busyness; no % text (detail is in the dropdown). Error = cracked glyph. ---
    img = _read_b64(_menubar_stem(payload), icons_dir)
    lines.append(f"| templateImage={img}" if img else "gym")
    lines.append("---")

    # --- Verdict / status ---
    if not payload.get("ok", False):
        lines.append("Fetch failed — showing last cached data")
    elif live is not None:
        typ = payload.get("typical_now")
        vmap = {"quieter": "quieter than usual", "busier": "busier than usual",
                "usual": "about as usual"}
        lines.append(f"{live}% — {vmap.get(payload['verdict'], '')} (typical: {typ}%)")
    else:
        lines.append(f"~{payload.get('typical_now')}% forecast — no live data right now")
    lines.append("---")

    # --- Today's histogram (Google-style image), else a compact text fallback ---
    hist_b64 = _hist_b64()
    lines.append(f"Today · {datetime.now():%A} | size=11")
    if hist_b64:
        lines.append(f"| image={hist_b64}")   # teal bars + red 'now' bar, like Google
    else:  # fail-soft: compact ascii sparkline if the PNG isn't there
        today = payload.get("today") or []
        spark = "".join(_bar(v) for v in today)
        lines.append(f"{spark} | font=Menlo size=13")
    nq = payload.get("next_quiet")
    if nq:
        lines.append(f"Next quiet window: {nq}")
    lines.append("---")

    # --- Actions ---
    maps_url = payload.get("maps_url") or MAPS_FALLBACK  # gym-specific link from config
    lines.append(f"Open in Google Maps | href={maps_url}")
    lines.append("Refresh now | refresh=true")
    stamp = payload.get("fetched_at", "")[11:16] or "?"
    if cache_age_min >= 60:
        lines.append(f"Updated {cache_age_min/60:.1f}h ago ({stamp}) | color=gray")
    else:
        lines.append(f"Updated {stamp} ({cache_age_min:.0f}m ago) | color=gray")
    return "\n".join(lines)


def _load() -> tuple[dict, float]:
    """Read-only: load the cache the launchd daemon maintains. The plugin NEVER
    scrapes/launches Chrome itself — that keeps clicking instant and avoids extra
    Google hits. If the daemon is down, we just show the (stale) cache honestly."""
    age_min = float("inf")
    if CACHE.exists():
        age_min = (time.time() - CACHE.stat().st_mtime) / 60
    try:
        return json.loads(CACHE.read_text()), age_min
    except Exception:
        return ({"level": "error", "live": None, "typical_now": None,
                 "today": [0]*24, "ok": False, "error": "no cache", "fetched_at": ""},
                age_min)


def main() -> None:
    try:
        payload, age = _load()
        print(render(payload, ICONS, age))
    except Exception as e:  # last-resort: never crash the menu bar
        img = _read_b64("template_error", ICONS)  # cracked monochrome glyph, never an emoji
        print(f"| templateImage={img}" if img else "gym")
        print("---")
        print(f"GymPulse error: {e}")


if __name__ == "__main__":
    main()
