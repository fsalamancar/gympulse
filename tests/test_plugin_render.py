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


def test_render_shows_live_percent_and_menu_separator():
    out = plugin.render(_payload(), ICONS, cache_age_min=2.0)
    assert "28%" in out
    assert "\n---\n" in out
    assert "image=" in out.split("\n---\n")[0]      # icon in the title line
    assert "Open in Google Maps" in out
    assert "href=" in out


def test_render_error_state_is_soft():
    out = plugin.render(
        _payload(ok=False, error="boom", level="error", live=None),
        ICONS, cache_age_min=125.0,
    )
    # cracked icon + staleness note, never a crash
    assert "image=" in out.split("\n---\n")[0]
    assert "updated" in out.lower()


def test_render_nodata_uses_grey_icon_and_no_percent_crash():
    out = plugin.render(_payload(level="nodata", live=None), ICONS, cache_age_min=5.0)
    assert "image=" in out.split("\n---\n")[0]
    assert "~" in out or "no live" in out.lower()   # shows forecast, not a bare None
