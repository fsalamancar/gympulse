# GymPulse

Gym busyness in your Mac menu bar. A monochrome dumbbell **gauge that fills with
how busy the gym is right now**, and a dropdown with a Google-style live
histogram plus the best time to go today.

## How it works
```
launchd (every 15 min)
  └─ fetcher.py ── live scrape via your real Chrome (scrape/live.py)
        │            └─ falls back to the WEEKLY_CURVE forecast on any failure
        └─ writes ~/.gympulse/latest.json + histogram.png
                     ▲
        SwiftBar plugin (read-only, instant) → menu bar gauge + dropdown
```

- **Menu bar:** dumbbell outline fills 0→100% with live busyness (10% steps);
  a cracked glyph means a real error.
- **Dropdown:** `LIVE — Busier than usual` badge, Google-clone histogram (teal
  typical bars + red live bar, 6 a.m.-first axis), and
  `Best time to go: 9 p.m. today (~24%)` within your schedule.
- **Live data:** scraped from Google Popular Times with your installed Chrome —
  see `scrape/README.md`. No API keys, no paid services.

## Setup
```bash
brew install --cask swiftbar google-chrome   # once
./install.sh                                  # deploys runtime + daemon + plugin
```
`install.sh` puts everything the daemon/plugin touch under `~/.gympulse` (outside
macOS-protected folders, so no recurring permission prompts) and loads the
launchd agent. Re-run it after changing code. Dev workflow: `uv venv &&
uv pip install -e . --group dev && uv run pytest`.

## Tune it (all in `fetcher/config.py`)
- **Swap gyms:** `GYM_ADDRESS`, `GYM_NAME`, `GYM_SEARCH_QUERY` (what Google knows it as).
- **Your schedule:** `GO_START` / `GO_END` — "best time to go" only recommends these hours.
- **Fallback forecast:** `WEEKLY_CURVE` (0–100 per hour per day).
- **Thresholds:** `QUIET` / `MODERATE`.
- **Phase-3 widget hand-off:** `APP_GROUP_COPY` (leave off until the widget exists).

## Status
- [x] M1 fetcher writes valid latest.json
- [x] M2 SwiftBar gauge + Google-style dropdown
- [x] M3 launchd daemon + history log
- [x] Live Google Popular Times via real Chrome (fail-soft to forecast)
- [ ] M4 WidgetKit widgets (deferred — `GymPulse/README.md`)
