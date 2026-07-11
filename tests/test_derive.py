from datetime import datetime
from zoneinfo import ZoneInfo

from fetcher import derive

TZ = ZoneInfo("America/Bogota")


def test_classify_boundaries():
    assert derive.classify(0) == "quiet"
    assert derive.classify(33) == "quiet"
    assert derive.classify(34) == "moderate"
    assert derive.classify(66) == "moderate"
    assert derive.classify(67) == "busy"
    assert derive.classify(100) == "busy"


def test_compute_verdict():
    assert derive.compute_verdict(61, 88) == "quieter"   # 27 below
    assert derive.compute_verdict(90, 70) == "busier"    # 20 above
    assert derive.compute_verdict(70, 65) == "usual"     # within +/-10


def test_find_best_windows_contiguous_and_open_ended():
    # quiet (<=33) at hours 10-13; hour 22 is quiet and closes the day window (6-22),
    # so it renders open-ended "22:00+" (hour 23 is outside the window, never read).
    data = [0]*10 + [30, 20, 25, 33] + [50]*8 + [10, 5]
    assert derive.find_best_windows(data) == ["10:00-14:00", "22:00+"]


def test_find_best_windows_closes_strictly_within_day():
    # A quiet run that starts and ENDS inside the day window (no open-ended tail).
    data = [50]*24
    for h in (8, 9, 10):
        data[h] = 20
    assert derive.find_best_windows(data) == ["08:00-11:00"]


def test_find_best_windows_none():
    data = [80]*24
    assert derive.find_best_windows(data) == []


def test_find_next_quiet():
    data = [50]*24
    data[21] = 20  # quiet at 21:00
    assert derive.find_next_quiet(data, now_hour=18) == "21:00"


def test_find_next_quiet_none_left_today():
    data = [90]*24
    assert derive.find_next_quiet(data, now_hour=18) is None


def test_build_payload_with_live():
    now = datetime(2026, 7, 10, 18, 0, tzinfo=TZ)  # Friday, hour 18
    week = [90]*24
    week[18] = 88
    populartimes = [{"name": "Friday", "data": week}]
    p = derive.build_payload(populartimes, live=61, now=now)
    assert p["live"] == 61
    assert p["typical_now"] == 88
    assert p["delta"] == -27
    assert p["verdict"] == "quieter"
    assert p["level"] == "moderate"      # 61 -> moderate
    assert p["source"] == "live"
    assert p["today"] == week
    assert p["week"]["Friday"] == week


def test_build_payload_forecast_colors_by_current_hour():
    # No live signal -> the forecast for this hour drives the level (not "nodata").
    now = datetime(2026, 7, 10, 18, 0, tzinfo=TZ)  # Friday, hour 18
    week = [10]*24
    week[18] = 88   # busy forecast at 18:00
    populartimes = [{"name": "Friday", "data": week}]
    p = derive.build_payload(populartimes, live=None, now=now)
    assert p["live"] is None
    assert p["source"] == "forecast"
    assert p["typical_now"] == 88
    assert p["level"] == "busy"          # 88 -> busy, colored by forecast
    assert p["delta"] == 0
    assert p["verdict"] == "usual"       # no live measurement -> neutral, not a false claim


def test_build_payload_forecast_quiet_hour_is_green():
    now = datetime(2026, 7, 10, 3, 0, tzinfo=TZ)  # Friday, hour 3 (overnight)
    week = [10]*24
    populartimes = [{"name": "Friday", "data": week}]
    p = derive.build_payload(populartimes, live=None, now=now)
    assert p["level"] == "quiet"         # 10 -> quiet (green), not grey
    assert p["source"] == "forecast"
