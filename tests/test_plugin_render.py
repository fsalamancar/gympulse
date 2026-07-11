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


def test_menu_bar_title_is_monochrome_icon_only_no_percent():
    out = plugin.render(_payload(), ICONS, cache_age_min=2.0)
    title = out.split("\n---\n")[0]
    assert "templateImage=" in title   # monochrome menu-bar glyph
    assert "%" not in title            # the percentage lives in the dropdown, not the bar
    assert "\n---\n" in out


def test_dropdown_still_shows_percent_and_actions():
    out = plugin.render(_payload(), ICONS, cache_age_min=2.0)
    dropdown = out.split("\n---\n", 1)[1]
    assert "28%" in dropdown            # busyness detail is in the dropdown
    assert "Open in Google Maps" in out
    assert "href=" in out


def test_render_error_state_uses_cracked_template():
    out = plugin.render(
        _payload(ok=False, error="boom", level="error", live=None),
        ICONS, cache_age_min=125.0,
    )
    title = out.split("\n---\n")[0]
    # cracked monochrome glyph + staleness note, never a crash
    assert "templateImage=" in title
    assert plugin._template_b64(False, ICONS) in title   # specifically the error glyph
    assert "updated" in out.lower()


def test_render_forecast_no_live_still_icon_only():
    out = plugin.render(_payload(level="nodata", live=None), ICONS, cache_age_min=5.0)
    title = out.split("\n---\n")[0]
    assert "templateImage=" in title
    assert "%" not in title
    # forecast detail still surfaces in the dropdown
    assert "~" in out or "no live" in out.lower()


def test_template_b64_selects_clean_vs_error_glyph():
    assert plugin._template_b64(True, ICONS) != ""
    assert plugin._template_b64(False, ICONS) != ""
    assert plugin._template_b64(True, ICONS) != plugin._template_b64(False, ICONS)


def test_template_b64_missing_icon_dir_returns_empty_not_crash():
    # A bad icons dir must not raise — the last-resort handler depends on this.
    assert plugin._template_b64(True, Path("/nonexistent/icons")) == ""
