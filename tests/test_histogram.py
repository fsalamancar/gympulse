"""Tests for the ImageMagick histogram renderer (skips if magick is unavailable)."""
import shutil

import pytest

from fetcher import histogram


_TODAY = [27, 14, 8, 3, 3, 11, 22, 32, 41, 46, 49, 49, 51, 54, 59, 65,
          81, 95, 100, 97, 92, 76, 59, 43]


@pytest.mark.skipif(shutil.which("magick") is None, reason="ImageMagick not installed")
def test_render_writes_a_png(tmp_path):
    out = tmp_path / "histogram.png"
    assert histogram.render(_TODAY, now_hour=18, out_path=out) is True
    assert out.exists() and out.stat().st_size > 0
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes


@pytest.mark.skipif(shutil.which("magick") is None, reason="ImageMagick not installed")
def test_render_with_live_overlay_draws_two_bars_and_badge(tmp_path):
    base = histogram._draw_ops(_TODAY, now_hour=9, live=None)
    withlive = histogram._draw_ops(_TODAY, now_hour=9, live=100, verdict="busier")
    # live mode adds the red bar + the EN TIEMPO REAL badge; forecast mode shows a note
    n_bars = lambda ops: sum("roundrectangle" in o for o in ops)
    assert n_bars(withlive) == n_bars(base) + 2      # +1 live bar, +1 badge pill
    joined = " ".join(withlive)
    assert "EN TIEMPO REAL" in joined
    assert "concurrido de lo habitual" in joined      # verdict text rendered
    assert "Pronóstico" in " ".join(base)             # forecast note without live
    out = tmp_path / "h.png"
    assert histogram.render(_TODAY, now_hour=9, out_path=out,
                            live=100, verdict="busier") is True


def test_axis_starts_at_6am_like_google():
    ops = histogram._draw_ops(_TODAY, now_hour=9, live=None)
    labels = [o for o in ops if o.startswith("text ") and o.endswith(".m.'")]
    assert labels and labels[0].endswith("'6a.m.'")   # first tick is 6 a.m.
    assert labels[-1].endswith("'3a.m.'")             # overnight wraps to the end


def test_render_rejects_bad_input(tmp_path):
    out = tmp_path / "histogram.png"
    assert histogram.render([], now_hour=0, out_path=out) is False
    assert histogram.render([10, 20, 30], now_hour=0, out_path=out) is False  # not 24
    assert not out.exists()
