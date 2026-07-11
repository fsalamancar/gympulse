#!/usr/bin/env python3
# <bitbar.title>GymPulse</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.desc>Gym busyness in the menu bar</bitbar.desc>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
"""Read-only SwiftBar plugin. Renders ~/.gympulse/latest.json. Never crashes the bar."""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HOME = Path.home()
REPO = Path(__file__).resolve().parent.parent
CACHE = HOME / ".gympulse" / "latest.json"
ICONS = REPO / "assets" / "icons"
VENV_PY = REPO / ".venv" / "bin" / "python"
MAPS_FALLBACK = "https://www.google.com/maps"
STALE_MIN = 10.0          # refresh cache if older than this
BLOCKS = " ▁▂▃▄▅▆▇█"

_ICON_FOR = {"quiet": "quiet", "moderate": "moderate", "busy": "busy",
             "nodata": "nodata", "error": "error"}


def _b64(level: str, icons_dir: Path) -> str:
    p = icons_dir / f"{_ICON_FOR.get(level, 'error')}.png"
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


def _bar(v: int) -> str:
    return BLOCKS[min(len(BLOCKS) - 1, round(v / 100 * (len(BLOCKS) - 1)))]


def render(payload: dict, icons_dir: Path, cache_age_min: float) -> str:
    level = payload.get("level", "error")
    live = payload.get("live")
    img = _b64(level, icons_dir)
    lines: list[str] = []

    # --- Menu bar title line: icon + percent (or ~forecast when no live) ---
    if live is not None:
        title = f"{live}%"
    elif payload.get("typical_now") is not None:
        title = f"~{payload['typical_now']}%"
    else:
        title = "gym"
    lines.append(f"{title} | image={img}" if img else title)
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

    # --- Today's hourly bars ---
    now_hour = datetime.now().hour
    today = payload.get("today") or []
    lines.append(f"Today · {datetime.now():%A} | size=11")
    for h, v in enumerate(today):
        if v == 0 and not (6 <= h <= 23):
            continue
        marker = "   <- now" if h == now_hour else ""
        lines.append(f"  {h:02d}:00  {_bar(v)}{_bar(v)}  {v:3d}%{marker} | font=Menlo size=12")
    nq = payload.get("next_quiet")
    if nq:
        lines.append(f"Next quiet window: {nq}")
    lines.append("---")

    # --- Actions ---
    lines.append(f"Open in Google Maps | href={MAPS_FALLBACK}")
    lines.append("Refresh now | refresh=true")
    stamp = payload.get("fetched_at", "")[11:16] or "?"
    if cache_age_min >= 60:
        lines.append(f"Updated {cache_age_min/60:.1f}h ago ({stamp}) | color=gray")
    else:
        lines.append(f"Updated {stamp} ({cache_age_min:.0f}m ago) | color=gray")
    return "\n".join(lines)


def _load_or_fetch() -> tuple[dict, float]:
    age_min = float("inf")
    if CACHE.exists():
        age_min = (time.time() - CACHE.stat().st_mtime) / 60
    if age_min > STALE_MIN and VENV_PY.exists():
        try:  # cache missing/stale: refresh once, off the render path's error budget
            subprocess.run([str(VENV_PY), "-m", "fetcher.fetcher"],
                           cwd=str(REPO), timeout=30, check=False)
            age_min = (time.time() - CACHE.stat().st_mtime) / 60
        except Exception:
            pass
    try:
        return json.loads(CACHE.read_text()), age_min
    except Exception:
        return ({"level": "error", "live": None, "typical_now": None,
                 "today": [0]*24, "ok": False, "error": "no cache", "fetched_at": ""},
                age_min)


def main() -> None:
    try:
        payload, age = _load_or_fetch()
        print(render(payload, ICONS, age))
    except Exception as e:  # last-resort: never crash the menu bar
        img = _b64("error", ICONS)  # cracked-bar icon, never an emoji
        print(f"gym | image={img}" if img else "gym")
        print("---")
        print(f"GymPulse error: {e}")


if __name__ == "__main__":
    main()
