# GymPulse — Design

**Date:** 2026-07-10
**Goal:** Glance at the Mac menu bar and instantly know whether Fitness24Seven (Bogotá / Teusaquillo) is worth going to right now. One colored pixel-dumbbell icon + live %, a dropdown with today's forecast, plus a widget-ready data layer.

**Source of truth for requirements:** `~/Downloads/gympulse-plan.md`. This doc records the decisions and deltas layered on top of that plan.

---

## Scope (this build)

- **Phases 1 & 2:** built to a fully working, verified state.
- **Phase 3 (widget):** code-scaffold only. Widget approach (SwiftBar-only vs MenuBarExtra vs Übersicht) is **deferred — decided at Phase 3**. `latest.json` is the stable contract that makes any of them possible.
- **Notifications:** dropped (user opted out). Phase 2 = daemon + history log only.

---

## Foundational decisions

| Decision | Choice | Why |
|---|---|---|
| Repo home | `/Users/fjosesala/Documents/GitHub/gympulse`, `git init` | Empty dir already open; matches plan layout |
| Python env | `uv` venv at `.venv/`, `livepopulartimes` pinned | launchd needs a stable interpreter path; anaconda base is fragile; matches `uv` preference |
| Config | Single `fetcher/config.py` (address, thresholds, quiet cutoff) | Keeps the gym address/thresholds out of 3 files |
| Menu-bar icon | Sliced pixel dumbbells as base64 via SwiftBar `\| image=`, `%` as text beside it | Full-color icon = the signal. **No emoji.** |
| Icon rendering | Full color (NOT SwiftBar template mode) | The green/amber/red carries meaning; template mode would monochrome it |
| Icon pipeline | One-time `assets/build_icons.sh`: slice 3×2 sheet → strip checkerboard → resize for retina bar → commit PNGs | Runtime never re-processes; plugin reads a PNG + base64-encodes |
| State → icon | quiet=green(s_0) · moderate=amber(s_1) · busy=red(s_2) · no-data=grey(s_4) · error=cracked(s_5); s_3 spare | Matches the sprite-sheet mapping in the plan |
| Gym display name | Set to match the real address (Bogotá / Teusaquillo) | Code's address is the Bogotá gym, not "Quinta Paredes" |

### Checkerboard-strip plan (risk mitigation)

The sprite sheet has a baked-in checkerboard (RGB, no alpha). The icons themselves **contain grey** (no-data dumbbell, metal parts), so a naive grey color-key could eat them.

1. Inspect the sheet's actual pixel colors first.
2. Prefer a **deterministic ImageMagick color-key** on the two exact checkerboard greys (fast, zero deps).
3. Fall back to **`uvx rembg`** (ephemeral, never installed into the venv) only if the color-key eats the grey icons.

The plan's permanent `rembg` install is dropped — poor ROI for stripping a fixed pattern.

---

## Architecture — one rule

**Python owns the data; everything else just reads a JSON file.** All fragile scraping is isolated in `fetcher.py`.

```
launchd (every 15 min, Phase 2)
   └─> fetcher.py ──scrape──> Google Maps (livepopulartimes)
            └─> writes ~/.gympulse/latest.json   (+ App Group copy, Phase 3)
                       ▲                ▲
              SwiftBar plugin      WidgetKit widget (future)
              (menu bar, read-only) (reads JSON)
```

### Data contract — `~/.gympulse/latest.json`

Schema from the plan. Derived fields computed **once** in Python so the UI stays dumb:

```json
{
  "fetched_at": "2026-07-10T18:12:00-05:00",
  "live": 61,
  "typical_now": 88,
  "delta": -27,
  "verdict": "quieter",
  "level": "moderate",
  "today": [24 ints, hourly 0..23],
  "best_windows": ["10:00-14:00", "22:00+"],
  "next_quiet": "21:30",
  "week": { "Monday": [...], ... },
  "ok": true,
  "error": null
}
```

- Written **atomically** (tmp file + rename) so readers never see a half-written file.
- `ok`/`error` + `fetched_at` let the UI show honest staleness instead of lying.
- Thresholds: quiet ≤ 33, moderate 34–66, busy > 66. `level` derived from `live` (or `typical_now` when no live data → no-data state).

---

## Repo layout

```
gympulse/
├── fetcher/
│   ├── config.py         # address, thresholds, quiet cutoff
│   ├── fetcher.py         # scrape -> compute derived -> write latest.json (all logic)
│   └── gym_busy.py        # existing CLI, refactored to call fetcher (thin wrapper)
├── assets/
│   ├── gympulse-icons-sheet.png   # original sprite sheet
│   ├── build_icons.sh             # one-time slice + strip + resize
│   └── icons/                     # committed transparent PNGs (quiet/moderate/busy/nodata/error)
├── swiftbar/gympulse.10m.py       # read-only menu-bar plugin
├── launchd/dev.francisco.gympulse.plist
├── GymPulse/              # Phase 3 scaffold (Xcode notes + TimelineProvider sketch)
├── docs/superpowers/specs/
├── pyproject.toml         # uv project, pinned livepopulartimes
└── README.md
```

---

## Phase 1 — SwiftBar MVP

1. `brew install swiftbar`; `uv venv` + install `livepopulartimes`.
2. `assets/build_icons.sh` → transparent PNGs committed to `assets/icons/`.
3. `swiftbar/gympulse.10m.py` — **reads cache; does NOT fetch on the UI thread.** Shells to `fetcher.py` (venv python) only if cache is missing/stale. Prints:
   - Line 1: icon via `| image=<base64>` + `NN%` text.
   - `---`, then dropdown: today's hourly bars (`| font=Menlo`), "next quiet window", "Open in Google Maps" `| href=`, "Refresh now" `| refresh=true`, "Updated HH:MM".
4. Fail-soft: any exception → cracked-bar icon + last cached data + "updated Xh ago". Never crashes the bar.

**Done when:** icon sits in the menu bar all day and survives Google hiccups.

**Verify:** icon visible; `latest.json` validates against schema.

---

## Phase 2 — daemon + history

1. `launchd/dev.francisco.gympulse.plist` → `StartInterval 900`, `RunAtLoad true`, invokes venv python + `fetcher.py`. SwiftBar plugin is now purely read-only (no network on UI path).
2. Politeness: ±60s jitter, hard 10-min floor between hits (single fetcher process).
3. Every fetch appends to `~/.gympulse/history.csv` (timestamp, live, typical) → real gym curve over time; enables later "Google forecast vs reality" analysis.

**Verify:** `launchctl list` shows the agent; `history.csv` grows on schedule.

---

## Phase 3 — scaffold only (deferred decision)

- `fetcher.py` also writes the App-Group copy to
  `~/Library/Group Containers/group.dev.francisco.gympulse/latest.json`
  so the data side is widget-ready regardless of chosen UI.
- Scaffold `GymPulse/` with Xcode setup notes + a `TimelineProvider` sketch (reload `.after(15 min)`; small = gauge + %, medium = sparkline + verdict + next quiet window). Icons reused, no emoji.
- **User** performs Xcode create / App Group enable / sign / build. Not automatable this session.

**Verify:** data written to the Group Container path.

---

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Scraper breaks (Google markup change) | All scraping in `fetcher.py`; cracked-bar state + stale cache; pin `livepopulartimes` |
| No live data off-peak | Fall back to forecast (no-data grey state) — still useful |
| Rate limiting | 15-min cadence, jitter, single fetcher process |
| Mac asleep | launchd fires on wake; `fetched_at` surfaces staleness honestly |
| Checkerboard strip eats grey icons | Inspect colors first; deterministic color-key, `uvx rembg` fallback |
| Widget can't see `~/.gympulse` | App Group container copy (Phase 3) |

---

## Milestones

- [ ] M1 `fetcher.py` writes valid `latest.json`
- [ ] M2 SwiftBar icon live with color states + dropdown
- [ ] M3 launchd daemon + history log (no notifications)
- [ ] M4 (deferred) WidgetKit small + medium widgets
