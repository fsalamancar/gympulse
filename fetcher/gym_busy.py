"""Human-readable CLI over the fetcher payload. No separate scraping path.

Usage: python -m fetcher.gym_busy [--week]
"""
from __future__ import annotations

import sys
from datetime import datetime

from fetcher import config
from fetcher.derive import classify
from fetcher.fetcher import fetch

BLOCKS = " ▁▂▃▄▅▆▇█"


def bar(v: int) -> str:
    return BLOCKS[min(len(BLOCKS) - 1, round(v / 100 * (len(BLOCKS) - 1)))]


def _label(v: int) -> str:
    return "closed/no data" if v == 0 else classify(v)


def _show_day(name: str, data: list[int], now_hour: int | None, live: int | None) -> None:
    print(f"\n{name}")
    for h, v in enumerate(data):
        if v == 0 and not (6 <= h <= 23):
            continue
        marker = ""
        if now_hour is not None and h == now_hour:
            marker = f"  <- now (live: {live}%)" if live is not None else "  <- now"
        print(f"  {h:02d}:00  {bar(v)}{bar(v)}  {v:3d}%  {_label(v)}{marker}")


def main() -> None:
    print(f"Fetching popular times for:\n  {config.PLACE_NAME}\n")
    p = fetch()
    if not p["ok"]:
        sys.exit(f"Could not fetch data ({p['error']}).")

    live = p["live"]
    now = datetime.now(config.TZ)
    if live is not None:
        verdict = {"busier": " - busier than usual",
                   "quieter": " - quieter than usual",
                   "usual": " - about as usual"}[p["verdict"]]
        print(f"RIGHT NOW: {live}% full ({classify(live)}){verdict}")
    else:
        print("RIGHT NOW: no live data (Google only shows it with enough visitors)")

    if "--week" in sys.argv:
        for name, data in p["week"].items():
            nh = now.hour if name == now.strftime("%A") else None
            _show_day(name, data, nh, live)
    else:
        _show_day(now.strftime("%A"), p["today"], now.hour, live)
        print("\nTip: run with --week for the full weekly heatmap.")


if __name__ == "__main__":
    main()
