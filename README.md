# GymPulse

Gym busyness in your Mac menu bar. One colored pixel-dumbbell icon + current %,
a dropdown with today's forecast, backed by a Python data layer.

## How it works
`fetcher.py` reads a self-tuned weekly forecast (`WEEKLY_CURVE` in `fetcher/config.py`)
and writes `~/.gympulse/latest.json`. Everything else just reads that file.

The forecast is based on your gym's actual rhythm—not live scraping. Edit `WEEKLY_CURVE`
in `fetcher/config.py` to match your gym's busy hours (0–100 per hour of day).

- **Swap gyms:** edit `GYM_ADDRESS` + `GYM_NAME` in `fetcher/config.py`.
- **Tune forecast:** edit `WEEKLY_CURVE` daily/hourly values in `fetcher/config.py`.
- **Menu bar:** SwiftBar plugin `swiftbar/gympulse.10m.py` (read-only).
- **Daemon:** launchd agent fetches every 15 min (`launchd/README.md`).
- **Widget:** Phase 3, deferred (`GymPulse/README.md`).

## Setup
```bash
uv venv && uv pip install -e . --group dev
bash assets/build_icons.sh
uv run python -m fetcher.fetcher      # writes latest.json
ln -sf "$(pwd)/swiftbar/gympulse.10m.py" ~/SwiftBar/gympulse.10m.py
```

## Status
- [x] M1 fetcher writes valid latest.json
- [x] M2 SwiftBar icon + dropdown
- [x] M3 launchd daemon + history log
- [ ] M4 WidgetKit widgets (deferred)
