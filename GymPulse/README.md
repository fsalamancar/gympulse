# GymPulse Widget (Phase 3 — deferred)

The data side is ready: `fetcher.py` already writes a copy to the App Group
container. Building the widget is a manual Xcode step.

## Setup
1. Xcode → new macOS App "GymPulse" (SwiftUI) + a **Widget Extension** target.
2. On BOTH targets: Signing & Capabilities → **+ App Group** →
   `group.dev.francisco.gympulse`.
3. Paste `WidgetProvider.swift.sketch` into the widget target; wire small
   (gauge + %) and medium (sparkline + verdict + next quiet) views.
4. Reload policy `.after(15 min)`. Sign with your free personal team.

## Decision still open
Whether this app also becomes a `MenuBarExtra` that replaces SwiftBar, or
stays widget-only, is deferred (see the design spec). The JSON contract makes
either path work without changing the Python side.
