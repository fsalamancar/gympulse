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
    # live mode adds the red bar + the LIVE badge; forecast mode shows a note
    n_bars = lambda ops: sum("roundrectangle" in o for o in ops)
    assert n_bars(withlive) == n_bars(base) + 2      # +1 live bar, +1 badge pill
    joined = " ".join(withlive)
    assert "LIVE" in joined
    assert "than usual" in joined                     # verdict text rendered
    assert "Typical forecast" in " ".join(base)       # forecast note without live
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


def test_find_magick_falls_back_to_homebrew_path(monkeypatch, tmp_path):
    """launchd runs with a bare PATH; render must still find the magick binary."""
    from fetcher import histogram

    fake = tmp_path / "magick"
    fake.write_text("#!/bin/sh\n")
    monkeypatch.setattr(shutil, "which", lambda _: None)
    monkeypatch.setattr(histogram, "_MAGICK_FALLBACKS", [str(fake)])
    assert histogram._find_magick() == str(fake)


def test_find_magick_returns_none_when_absent(monkeypatch):
    from fetcher import histogram

    monkeypatch.setattr(shutil, "which", lambda _: None)
    monkeypatch.setattr(histogram, "_MAGICK_FALLBACKS", ["/nonexistent/magick"])
    assert histogram._find_magick() is None


def test_now_marker_vertical_line_at_current_hour():
    """A vertical line marks the current hour (the only 'now' cue in forecast mode)."""
    ops = histogram._draw_ops(_TODAY, now_hour=18, live=None)
    i = (18 - histogram._DAY_START) % 24
    slot = (histogram._W - histogram._PAD_L - histogram._PAD_R) / 24.0
    x = histogram._PAD_L + i * slot + slot / 2
    vlines = [o for o in ops if o.startswith("line ") and f"line {x:.1f}," in o
              and o.count(f"{x:.1f},") == 2]  # same x twice = vertical
    assert len(vlines) == 1
    # present in live mode too
    ops_live = histogram._draw_ops(_TODAY, now_hour=18, live=90)
    assert any(o.startswith("line ") and o.count(f"{x:.1f},") == 2 for o in ops_live)
