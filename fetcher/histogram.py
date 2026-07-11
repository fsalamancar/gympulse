"""Render a Google-style busyness histogram PNG via ImageMagick (no Python deps).

Teal bars for the day's curve, a red bar for the current hour (the "now"/live bar),
light hour ticks. Written to ~/.gympulse/histogram.png each fetch so the SwiftBar
plugin can embed it instantly. Fail-soft: on any problem it just skips (returns False).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

# A real font FILE (ImageMagick can't resolve font names on some boxes). First that
# exists wins; if none, hour labels are skipped (bars still render).
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
_W, _H = 660, 200
_PAD_L, _PAD_R, _PAD_T, _PAD_B = 10, 10, 12, 34
_TEAL = "#5b8a9a"
_RED = "#d1553f"
_TICK = "#808080"  # mid-gray: readable on both light and dark dropdown backgrounds
_BG = "none"  # transparent


def _draw_ops(today: list[int], now_hour: int, live: int | None) -> list[str]:
    plot_w = _W - _PAD_L - _PAD_R
    plot_h = _H - _PAD_T - _PAD_B
    slot = plot_w / 24.0
    bar_w = slot * 0.62
    ops: list[str] = []
    y_base = _PAD_T + plot_h

    def bar(x0: float, w: float, val: int, color: str) -> None:
        bh = max(2.0, max(0, min(100, val)) / 100 * plot_h)
        ops.extend(["-fill", color,
                    "-draw", f"roundrectangle {x0:.1f},{y_base - bh:.1f} "
                             f"{x0 + w:.1f},{y_base:.1f} 3,3"])

    for h in range(24):
        slot_x = _PAD_L + h * slot
        if h == now_hour and live is not None:
            # Two bars like Google: the typical (teal, thinner, left) and the LIVE
            # red bar (right) so you can see the gym is busier/quieter than usual.
            half = bar_w * 0.52
            bar(slot_x + (slot - bar_w) / 2, half, today[h], _TEAL)
            bar(slot_x + (slot - bar_w) / 2 + half + 1, half, live, _RED)
        else:
            bar(slot_x + (slot - bar_w) / 2, bar_w, today[h], _TEAL)

    # Hour labels under the axis (every 3h), only if a usable font file exists.
    font = _font()
    if font:
        ops += ["-fill", _TICK, "-font", font, "-pointsize", "24"]
        for h in range(0, 24, 3):
            hr12 = ((h - 1) % 12) + 1
            lab = f"{hr12}{'a' if h < 12 else 'p'}"
            x = _PAD_L + h * slot + slot / 2
            ops += ["-draw", f"text {x - 13:.0f},{_H - 8} '{lab}'"]
    return ops


def render(today: list[int], now_hour: int, out_path: Path, live: int | None = None) -> bool:
    """Draw the histogram to out_path. Returns True on success, False on any failure.

    If `live` is given, the current hour shows two bars (teal typical + red live),
    mirroring Google's live overlay; otherwise just the teal typical bar."""
    magick = shutil.which("magick")
    if not magick or not today or len(today) < 24:
        return False
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [magick, "-size", f"{_W}x{_H}", f"xc:{_BG}",
               *_draw_ops(today, now_hour, live),
               "-units", "PixelsPerInch", "-density", "144", str(out_path)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=15)
        return True
    except Exception:
        return False


if __name__ == "__main__":  # manual probe
    demo = [27, 14, 8, 3, 3, 11, 22, 32, 41, 46, 49, 49, 51, 54, 59, 65,
            81, 95, 100, 97, 92, 76, 59, 43]
    ok = render(demo, 9, Path.home() / ".gympulse" / "histogram.png", live=100)
    print("rendered:", ok)
