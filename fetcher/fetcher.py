"""Build latest.json from the self-tuned weekly forecast in config.WEEKLY_CURVE.

No network, no dependencies (stdlib only). The forecast for the current hour is
the busyness estimate. Run: python -m fetcher.fetcher
"""
from __future__ import annotations

import csv
import json
import os
import tempfile
from datetime import datetime

from fetcher import config
from fetcher.derive import build_payload


def _stamp() -> str:
    return datetime.now(config.TZ).isoformat(timespec="seconds")


def _week_from_forecast() -> list[dict]:
    week = [
        {"name": day, "data": config.WEEKLY_CURVE[day]}
        for day in ("Monday", "Tuesday", "Wednesday", "Thursday",
                    "Friday", "Saturday", "Sunday")
    ]
    for entry in week:  # guard against a hand-edited malformed curve
        if len(entry["data"]) != 24:
            raise ValueError(f"WEEKLY_CURVE['{entry['name']}'] must have 24 hourly values")
    return week


def _try_live(now: datetime) -> dict | None:
    """Best-effort live scrape via real Chrome. Returns a payload or None (fall back)."""
    if not getattr(config, "USE_LIVE_SCRAPE", False):
        return None
    try:
        from scrape.live import scrape_live
    except Exception:
        return None
    r = scrape_live(config.GYM_SEARCH_QUERY, config.TZ)
    if not r.get("ok") or not r.get("today"):
        return None
    today_name = now.strftime("%A")
    # today's curve comes from Google; other days keep the forecast for the week view
    week = _week_from_forecast()
    for d in week:
        if d["name"] == today_name:
            d["data"] = r["today"]
    payload = build_payload(week, live=r.get("live"), now=now)
    payload["source"] = "live"
    if r.get("verdict"):
        payload["verdict"] = r["verdict"]
    payload.update(fetched_at=now.isoformat(timespec="seconds"),
                   maps_url=config.MAPS_URL, ok=True, error=None)
    return payload


def fetch() -> dict:
    """Build a full payload. Try the live Google scrape, else the forecast curve.
    Never raises — any failure comes back soft (ok=False) or falls back to forecast."""
    try:
        now = datetime.now(config.TZ)  # one clock read for both fetched_at and the hour
        live_payload = _try_live(now)
        if live_payload is not None:
            return live_payload
        payload = build_payload(_week_from_forecast(), live=None, now=now)
        payload.update(
            fetched_at=now.isoformat(timespec="seconds"),
            maps_url=config.MAPS_URL,  # so the gym-specific Maps link swaps with config
            ok=True,
            error=None,
        )
        return payload
    except Exception as e:  # e.g. a malformed WEEKLY_CURVE
        return {
            "fetched_at": _stamp(),
            "live": None,
            "typical_now": None,
            "delta": 0,
            "verdict": "usual",
            "level": "error",
            "source": "forecast",
            "today": [0] * 24,
            "best_windows": [],
            "next_quiet": None,
            "week": {},
            "maps_url": config.MAPS_URL,
            "ok": False,
            "error": str(e),
        }


def write_json(payload: dict) -> None:
    """Atomic write to LATEST_JSON, plus best-effort App Group copy."""
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(payload, ensure_ascii=False, indent=2)
    _atomic_write(config.LATEST_JSON, blob)
    try:  # widget copy is best-effort; container may not exist yet
        config.APP_GROUP_JSON.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(config.APP_GROUP_JSON, blob)
    except OSError:
        pass


def _atomic_write(path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def append_history(payload: dict) -> None:
    if not payload.get("ok"):
        return
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    new = not config.HISTORY_CSV.exists()
    with config.HISTORY_CSV.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["fetched_at", "live", "typical_now"])
        w.writerow([payload["fetched_at"], payload["live"], payload["typical_now"]])


def main() -> None:
    payload = fetch()
    write_json(payload)
    append_history(payload)


if __name__ == "__main__":
    main()
