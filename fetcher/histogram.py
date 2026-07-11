"""Render a Google-style busyness histogram PNG via ImageMagick (no Python deps).

Clones Google's popular-times widget: a red "LIVE" badge + verdict text,
teal typical bars with the tall red live bar at the current hour, a baseline, and
hour labels on a 6 a.m.-first axis (overnight hours at the end) — exactly like
Google renders it. Written to ~/.gympulse/histogram.png each fetch so the SwiftBar
plugin can embed it instantly. Fail-soft: on any problem it just skips (returns False).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

# launchd runs daemons with PATH=/usr/bin:/bin:… — Homebrew is not on it, so
# shutil.which("magick") fails under the LaunchAgent even when ImageMagick is
# installed. Fall back to the standard install locations.
_MAGICK_FALLBACKS = [
    "/opt/homebrew/bin/magick",   # Apple Silicon Homebrew
    "/usr/local/bin/magick",      # Intel Homebrew
]


def _find_magick() -> str | None:
    found = shutil.which("magick")
    if found:
        return found
    for p in _MAGICK_FALLBACKS:
        if Path(p).exists():
            return p
    return None


# A real font FILE (ImageMagick can't resolve font names on some boxes). First that
# exists wins; if none, all text is skipped (bars still render).
_FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/SFNSMono.ttf",
]


def _font() -> str | None:
    for f in _FONT_CANDIDATES:
        if Path(f).exists():
            return f
    return None


# Canvas (physical px; tagged 144 DPI so it renders at half size, retina-crisp).
_W, _H = 660, 260
_PAD_L, _PAD_R = 12, 12
_HEADER_H = 52          # badge + verdict line
_PAD_B = 40             # baseline -> hour labels
_TEAL = "#5b8a9a"
_RED = "#d1553f"
_TICK = "#808080"       # mid-gray: readable on both light and dark dropdowns
_BASELINE = "#9a9a9a"
_BG = "none"            # transparent

_DAY_START = 6          # Google's popular-times axis starts at 6 a.m.

_VERDICT_TEXT = {
    "busier": "Busier than usual",
    "quieter": "Less busy than usual",
    "usual": "As busy as usual",
}


def _hour_label(h: int) -> str:
    hr12 = ((h - 1) % 12) + 1
    return f"{hr12}{'a' if h < 12 else 'p'}.m."


def _draw_ops(today: list[int], now_hour: int, live: int | None,
              verdict: str = "usual") -> list[str]:
    plot_w = _W - _PAD_L - _PAD_R
    plot_top = _HEADER_H
    plot_h = _H - _HEADER_H - _PAD_B
    slot = plot_w / 24.0
    bar_w = slot * 0.62
    y_base = plot_top + plot_h
    font = _font()
    ops: list[str] = []

    # --- Header: red LIVE badge + verdict (live), or gray forecast note ---
    if font:
        if live is not None:
            badge_txt = "LIVE"
            bx0, by0, by1 = _PAD_L, 8, 40
            bx1 = bx0 + 12 + len(badge_txt) * 12.2 + 12  # padded pill width
            ops += ["-fill", _RED,
                    "-draw", f"roundrectangle {bx0},{by0} {bx1:.0f},{by1} 8,8",
                    "-fill", "white", "-font", font, "-pointsize", "20",
                    "-draw", f"text {bx0 + 12},{by1 - 10} '{badge_txt}'",
                    "-fill", _TICK, "-pointsize", "22",
                    "-draw", f"text {bx1 + 14:.0f},{by1 - 9} "
                             f"'{_VERDICT_TEXT.get(verdict, _VERDICT_TEXT['usual'])}'"]
        else:
            ops += ["-fill", _TICK, "-font", font, "-pointsize", "22",
                    "-draw", f"text {_PAD_L},32 'Typical forecast'"]

    # --- Bars, on a 6 a.m.-first axis like Google (overnight at the end) ---
    def bar(x0: float, w: float, val: int, color: str) -> None:
        bh = max(2.0, max(0, min(100, val)) / 100 * plot_h)
        ops.extend(["-fill", color,
                    "-draw", f"roundrectangle {x0:.1f},{y_base - bh:.1f} "
                             f"{x0 + w:.1f},{y_base:.1f} 4,4"])

    for i in range(24):
        h = (_DAY_START + i) % 24
        slot_x = _PAD_L + i * slot
        if h == now_hour and live is not None:
            # Two bars like Google: typical (teal, left) + LIVE red bar (right).
            half = bar_w * 0.52
            bar(slot_x + (slot - bar_w) / 2, half, today[h], _TEAL)
            bar(slot_x + (slot - bar_w) / 2 + half + 1, half, live, _RED)
        else:
            bar(slot_x + (slot - bar_w) / 2, bar_w, today[h], _TEAL)

    # --- Vertical "now" marker at the current hour, on top of the bars so it
    # stays visible over a tall bar (the only current-time cue in forecast mode) ---
    now_i = (now_hour - _DAY_START) % 24
    now_x = _PAD_L + now_i * slot + slot / 2
    ops += ["-stroke", _RED, "-strokewidth", "2", "-fill", "none",
            "-draw", f"line {now_x:.1f},{plot_top + 6} {now_x:.1f},{y_base}",
            "-stroke", "none", "-fill", "none"]

    # --- Baseline under the bars ---
    ops += ["-stroke", _BASELINE, "-strokewidth", "2",
            "-draw", f"line {_PAD_L},{y_base + 1} {_W - _PAD_R},{y_base + 1}",
            "-stroke", "none"]

    # --- Hour labels every 3h ("6a.m." style), starting at the axis start ---
    if font:
        ops += ["-fill", _TICK, "-font", font, "-pointsize", "22"]
        for i in range(0, 24, 3):
            h = (_DAY_START + i) % 24
            x = _PAD_L + i * slot + slot / 2
            ops += ["-draw", f"text {x - 24:.0f},{_H - 10} '{_hour_label(h)}'"]
    return ops


def render(today: list[int], now_hour: int, out_path: Path,
           live: int | None = None, verdict: str = "usual") -> bool:
    """Draw the widget to out_path. Returns True on success, False on any failure.

    If `live` is given, the current hour shows two bars (teal typical + red live)
    plus the LIVE badge and verdict text, mirroring Google's widget."""
    magick = _find_magick()
    if not magick or not today or len(today) < 24:
        return False
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [magick, "-size", f"{_W}x{_H}", f"xc:{_BG}",
               *_draw_ops(today, now_hour, live, verdict),
               "-units", "PixelsPerInch", "-density", "144", str(out_path)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=15)
        return True
    except Exception:
        return False


if __name__ == "__main__":  # manual probe
    demo = [27, 14, 8, 3, 3, 11, 22, 32, 41, 46, 49, 49, 51, 54, 59, 65,
            81, 95, 100, 97, 92, 76, 59, 43]
    ok = render(demo, 9, Path.home() / ".gympulse" / "histogram.png",
                live=100, verdict="busier")
    print("rendered:", ok)
