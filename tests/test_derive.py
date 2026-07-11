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


def test_best_go_time_picks_least_busy_upcoming_hour_in_schedule():
    # now=9am Friday; quietest remaining schedulable hour (7..22) is 14:00 (20%)
    today = [50]*24
    today[14] = 20
    today[3] = 1          # quieter, but outside the 7-23 schedule -> ignored
    week = {"Friday": today, "Saturday": [40]*24}
    now = datetime(2026, 7, 10, 9, 0, tzinfo=TZ)  # Friday 9am
    g = derive.best_go_time(today, week, now)
    assert g == {"day": "today", "hour": 14, "pct": 20}


def test_best_go_time_tie_prefers_earliest_hour():
    today = [50]*24
    today[10] = 30
    today[20] = 30
    week = {"Friday": today}
    now = datetime(2026, 7, 10, 8, 0, tzinfo=TZ)
    assert derive.best_go_time(today, week, now)["hour"] == 10


def test_best_go_time_rolls_to_tomorrow_when_day_is_over():
    today = [50]*24
    tomorrow = [60]*24
    tomorrow[8] = 15      # tomorrow's quietest schedulable hour
    week = {"Friday": today, "Saturday": tomorrow}
    now = datetime(2026, 7, 10, 22, 30, tzinfo=TZ)  # Friday 10:30pm -> nothing left
    g = derive.best_go_time(today, week, now)
    assert g == {"day": "tomorrow", "hour": 8, "pct": 15}


def test_best_go_time_none_when_no_data_at_all():
    now = datetime(2026, 7, 10, 22, 30, tzinfo=TZ)
    assert derive.best_go_time([0]*24, {}, now) is None


def test_build_payload_includes_go_at():
    now = datetime(2026, 7, 10, 9, 0, tzinfo=TZ)  # Friday
    week = [30]*24
    week[15] = 10
    populartimes = [{"name": "Friday", "data": week}]
    p = derive.build_payload(populartimes, live=None, now=now)
    assert p["go_at"] == {"day": "today", "hour": 15, "pct": 10}


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
