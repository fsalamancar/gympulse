"""Unit tests for the pure parse layer of the live scraper (no browser needed)."""
from scrape.live import _first_hour, _verdict, parse_rows


def test_first_hour_spanish_labels():
    assert _first_hour("9 a. m.") == 9
    assert _first_hour("12 p. m.") == 12
    assert _first_hour("1 p. m.") == 13
    assert _first_hour("12 a. m.") == 0
    assert _first_hour("nonsense") == -1


def test_verdict_from_html():
    assert _verdict("... Más concurrido de lo habitual ...") == "busier"
    assert _verdict("... menos concurrido de lo habitual ...") == "quieter"
    assert _verdict("no phrase here") == "usual"


def _rows():
    # Mirrors the real DOM at 9am: one typical bar per hour, plus a LIVE (ycghLd)
    # overlay at 9am that is much taller than the typical 9am bar (busier than usual).
    rows = []
    typ = {6: 6, 7: 9, 8: 11, 9: 13, 10: 15, 11: 17, 12: 18, 13: 23,
           14: 26, 15: 28, 16: 27, 17: 26, 18: 21}  # peak 28 at 15:00
    for hr, h in typ.items():
        label = f"{hr if hr <= 12 else hr-12} {'a' if hr < 12 else 'p'}. m."
        rows.append({"h": float(h), "live": False, "hour": label})
    rows.append({"h": 52.0, "live": True, "hour": "9 a. m."})  # tall live overlay
    return rows


def test_live_overlay_drives_live_not_typical():
    p = parse_rows(_rows(), now_hour=9)
    assert p["ok"] is True
    # live must reflect the TALL overlay (52 vs peak 28 -> capped 100), NOT typical 9am
    assert p["live"] == 100
    # the typical 9am value is low; the bug set live to this (~46). Ensure it did NOT.
    assert p["today"][9] == round(13 / 28 * 100)  # 46
    assert p["live"] != p["today"][9]


def test_curve_normalized_to_peak():
    p = parse_rows(_rows(), now_hour=9)
    assert p["today"][15] == 100        # the typical peak
    assert p["today"][6] == round(6 / 28 * 100)


def test_no_live_overlay_falls_back_to_typical_hour():
    rows = [{"h": 20.0, "live": False, "hour": "3 p. m."}]  # only 15:00
    p = parse_rows(rows, now_hour=15)
    assert p["live"] == 100             # single bar is its own peak
    assert p["today"][15] == 100
