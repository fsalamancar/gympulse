"""Pure percentage -> meaning logic. No I/O, no network — fully unit-testable."""
from __future__ import annotations

from datetime import datetime

from datetime import timedelta

from fetcher.config import GO_END, GO_START, MODERATE, QUIET

_DAY_START, _DAY_END = 6, 22  # hours considered for "best windows"


def classify(v: int) -> str:
    if v <= QUIET:
        return "quiet"
    if v <= MODERATE:
        return "moderate"
    return "busy"


def compute_verdict(live: int, typical: int) -> str:
    diff = live - typical
    if diff > 10:
        return "busier"
    if diff < -10:
        return "quieter"
    return "usual"


def find_best_windows(data: list[int]) -> list[str]:
    """Contiguous runs of quiet (<=QUIET) hours within the day window.

    Returns ranges like "10:00-14:00" (end-exclusive hour). A run touching
    the end of the day window renders open-ended, e.g. "22:00+".
    """
    windows: list[str] = []
    start: int | None = None
    for h in range(_DAY_START, _DAY_END + 1):
        quiet = 0 < data[h] <= QUIET  # 0 means "closed", not "quiet"
        if quiet and start is None:
            start = h
        elif not quiet and start is not None:
            windows.append(f"{start:02d}:00-{h:02d}:00")
            start = None
    if start is not None:
        windows.append(f"{start:02d}:00+")
    return windows


def find_next_quiet(data: list[int], now_hour: int) -> str | None:
    """First upcoming hour today (after now) that is quiet."""
    for h in range(now_hour + 1, 24):
        if 0 < data[h] <= QUIET:
            return f"{h:02d}:00"
    return None


def _least_busy(data: list[int], first_hour: int) -> tuple[int, int] | None:
    """(hour, pct) of the least busy open hour in [first_hour, GO_END); ties -> earliest."""
    candidates = [(data[h], h) for h in range(max(first_hour, GO_START), GO_END)
                  if data[h] > 0]  # 0 = closed/no data, not a recommendation
    if not candidates:
        return None
    pct, hour = min(candidates)
    return hour, pct


def best_go_time(today: list[int], week: dict[str, list[int]],
                 now: datetime) -> dict | None:
    """Recommend when to hit the gym within the user's schedule (GO_START..GO_END).

    Picks the least busy upcoming hour today; if the schedulable day is over,
    falls to tomorrow's least busy hour from the weekly curve."""
    pick = _least_busy(today, now.hour + 1)
    if pick is not None:
        return {"day": "today", "hour": pick[0], "pct": pick[1]}
    tomorrow_name = (now + timedelta(days=1)).strftime("%A")
    tomorrow = week.get(tomorrow_name)
    if tomorrow:
        pick = _least_busy(tomorrow, GO_START)
        if pick is not None:
            return {"day": "tomorrow", "hour": pick[0], "pct": pick[1]}
    return None


def build_payload(
    populartimes: list[dict], live: int | None, now: datetime
) -> dict:
    today_name = now.strftime("%A")
    today = next(
        (d["data"] for d in populartimes if d["name"] == today_name),
        populartimes[0]["data"],
    )
    typical_now = today[now.hour]

    if live is not None:
        # A real live measurement: it drives the color and the "vs usual" verdict.
        source = "live"
        level = classify(live)
        verdict = compute_verdict(live, typical_now)
        delta = live - typical_now
    else:
        # No live signal: the forecast for this hour IS our estimate and drives
        # the color. "nodata" grey is reserved for genuinely-missing forecast.
        source = "forecast"
        level = classify(typical_now) if typical_now is not None else "nodata"
        verdict = "usual"
        delta = 0

    week = {d["name"]: d["data"] for d in populartimes}
    return {
        "live": live,
        "typical_now": typical_now,
        "delta": delta,
        "verdict": verdict,
        "level": level,
        "source": source,
        "today": today,
        "best_windows": find_best_windows(today),
        "next_quiet": find_next_quiet(today, now.hour),
        "go_at": best_go_time(today, week, now),
        "week": week,
    }
