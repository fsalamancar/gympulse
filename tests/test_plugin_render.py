import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "gympulse_plugin", Path("swiftbar/gympulse.10m.py")
)
plugin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plugin)

ICONS = Path("assets/icons")


def _payload(**over):
    base = {"live": 28, "typical_now": 45, "delta": -17, "verdict": "quieter",
            "level": "quiet", "today": [0]*16 + [52, 74, 88] + [40]*5,
            "best_windows": ["10:00-14:00"], "next_quiet": "21:00",
            "fetched_at": "2026-07-10T18:12:00-05:00", "ok": True, "error": None}
    base.update(over)
    return base


def test_menu_bar_title_is_gauge_icon_only_no_percent():
    out = plugin.render(_payload(), ICONS, cache_age_min=2.0)
    title = out.split("\n---\n")[0]
    assert "templateImage=" in title   # monochrome gauge glyph
    assert "%" not in title            # the percentage lives in the dropdown, not the bar
    assert "\n---\n" in out


def test_dropdown_shows_summary_histogram_and_actions():
    out = plugin.render(_payload(), ICONS, cache_age_min=2.0)
    body = out.split("\n---\n", 1)[1]
    assert "28%" in body                 # one-line busyness summary
    # histogram: either the embedded PNG (if built) or the ascii fallback line
    assert ("| image=" in body) or ("▁" in out or "█" in out or "▇" in out)
    assert "Open in Google Maps" in out
    assert "href=" in out
    # the old verbose hour-by-hour text list is gone
    assert "  06:00" not in out and "  18:00" not in out


def test_gauge_stem_fills_with_busyness():
    # live drives the gauge, rounded to the nearest 10%
    assert plugin._menubar_stem(_payload(live=28)) == "fill_30"
    assert plugin._menubar_stem(_payload(live=0)) == "fill_0"
    assert plugin._menubar_stem(_payload(live=88)) == "fill_90"
    assert plugin._menubar_stem(_payload(live=100)) == "fill_100"


def test_gauge_uses_forecast_when_no_live():
    # no live measurement -> the forecast for this hour fills the gauge
    assert plugin._menubar_stem(_payload(live=None, typical_now=45)) == "fill_50"
    assert plugin._menubar_stem(_payload(live=None, typical_now=None)) == "fill_0"


def test_error_uses_cracked_glyph():
    stem = plugin._menubar_stem(_payload(ok=False, error="boom", live=None))
    assert stem == "template_error"
    out = plugin.render(_payload(ok=False, error="boom", level="error", live=None),
                        ICONS, cache_age_min=125.0)
    title = out.split("\n---\n")[0]
    assert plugin._read_b64("template_error", ICONS) in title
    assert "updated" in out.lower()


def test_all_gauge_levels_and_error_glyph_exist_and_load():
    for p in range(0, 101, 10):
        assert plugin._read_b64(f"fill_{p}", ICONS) != "", f"missing fill_{p}"
    assert plugin._read_b64("template_error", ICONS) != ""


def test_read_b64_missing_icon_dir_returns_empty_not_crash():
    # A bad icons dir must not raise — the last-resort handler depends on this.
    assert plugin._read_b64("template_error", Path("/nonexistent/icons")) == ""
