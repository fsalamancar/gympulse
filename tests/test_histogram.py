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
def test_render_with_live_overlay_draws_two_bars(tmp_path):
    # live at the current hour -> an extra (red) bar is drawn, so the op list is longer
    base = histogram._draw_ops(_TODAY, now_hour=9, live=None)
    withlive = histogram._draw_ops(_TODAY, now_hour=9, live=100)
    assert withlive.count("-draw") == base.count("-draw") + 1  # one extra (red) bar
    out = tmp_path / "h.png"
    assert histogram.render(_TODAY, now_hour=9, out_path=out, live=100) is True


def test_render_rejects_bad_input(tmp_path):
    out = tmp_path / "histogram.png"
    assert histogram.render([], now_hour=0, out_path=out) is False
    assert histogram.render([10, 20, 30], now_hour=0, out_path=out) is False  # not 24
    assert not out.exists()
