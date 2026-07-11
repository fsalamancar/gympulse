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
_W, _H = 660, 190
_PAD_L, _PAD_R, _PAD_T, _PAD_B = 10, 10, 12, 26
_TEAL = "#5b8a9a"
_RED = "#d1553f"
_TICK = "#b8c2c6"
_BG = "none"  # transparent


def _draw_ops(today: list[int], now_hour: int) -> list[str]:
    plot_w = _W - _PAD_L - _PAD_R
    plot_h = _H - _PAD_T - _PAD_B
    slot = plot_w / 24.0
    bar_w = slot * 0.66
    peak = max(today) or 1
    ops: list[str] = []
    for h in range(24):
        val = max(0, min(100, today[h]))
        bh = max(2.0, val / 100 * plot_h)  # min 2px so empty hours still show a nub
        x0 = _PAD_L + h * slot + (slot - bar_w) / 2
        x1 = x0 + bar_w
        y1 = _PAD_T + plot_h
        y0 = y1 - bh
        color = _RED if h == now_hour else _TEAL
        ops += ["-fill", color,
                "-draw", f"roundrectangle {x0:.1f},{y0:.1f} {x1:.1f},{y1:.1f} 3,3"]
    # hour ticks at 6a / 12p / 6p / 12a — only if a usable font file exists
    font = _font()
    if font:
        ops += ["-fill", _TICK, "-font", font, "-pointsize", "20"]
        for h, lab in [(6, "6a"), (12, "12p"), (18, "6p"), (0, "12a")]:
            x = _PAD_L + h * slot + slot / 2
            ops += ["-draw", f"text {x - 12:.0f},{_H - 6} '{lab}'"]
    return ops


def render(today: list[int], now_hour: int, out_path: Path) -> bool:
    """Draw the histogram to out_path. Returns True on success, False on any failure."""
    magick = shutil.which("magick")
    if not magick or not today or len(today) < 24:
        return False
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [magick, "-size", f"{_W}x{_H}", f"xc:{_BG}",
               *_draw_ops(today, now_hour),
               "-units", "PixelsPerInch", "-density", "144", str(out_path)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=15)
        return True
    except Exception:
        return False


if __name__ == "__main__":  # manual probe
    demo = [27, 14, 8, 3, 3, 11, 22, 32, 41, 46, 49, 49, 51, 54, 59, 65,
            81, 95, 100, 97, 92, 76, 59, 43]
    ok = render(demo, 18, Path.home() / ".gympulse" / "histogram.png")
    print("rendered:", ok)
