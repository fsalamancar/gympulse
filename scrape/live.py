"""Scrape Google's live Popular Times for the gym using the user's real Chrome.

Google serves Popular Times to a normal logged-in browser but strips it from the
bundled/headless Chromium that automation usually uses. So we drive the user's
installed Chrome (channel="chrome") with a dedicated persistent profile at
~/.gympulse/chrome-profile -- Google treats it as a real browser.

Returns {today: [24 ints], live: int|None, verdict: str, ok: bool, ...} or a soft
failure (ok=False) -- NEVER raises. The caller falls back to the forecast.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

PROFILE = Path.home() / ".gympulse" / "chrome-profile"

# Each hourly bar is a `div.hIqKNb` whose pixel height encodes busyness; it sits
# under a parent carrying an hour aria-label ("9 a. m."). At the CURRENT hour Google
# adds a second bar with class `ycghLd` = the LIVE (red) value overlaying the typical
# one. We read each bar's height + hour + whether it's the live overlay.
_EXTRACT_JS = r"""() => {
  const bars = [...document.querySelectorAll('div.hIqKNb')];
  if (!bars.length) return {ok:false, error:'no popular-times bars (div.hIqKNb)'};
  const rows = bars.map(b => {
    let hour = '';
    for (let n = b, i = 0; n && i < 4; n = n.parentElement, i++) {
      const a = n.getAttribute && n.getAttribute('aria-label');
      if (a && /\b\d{1,2}\s*[ap]\.?\s*m\.?/i.test(a)) { hour = a; break; }
    }
    const styleH = (b.getAttribute('style')||'').match(/height:\s*([\d.]+)/);
    return {
      h: styleH ? parseFloat(styleH[1]) : (b.offsetHeight || 0),
      live: /\bycghLd\b/.test(b.className),   // the live red overlay bar
      hour,
    };
  });
  return {ok:true, rows};
}"""

# Verdict phrase lives in the raw page HTML; regex is more reliable than DOM walking.
_VERDICT_RE = re.compile(r"(m[aá]s|menos)\s+concurrido\s+de\s+lo\s+habitual", re.I)


def _first_hour(label: str) -> int:
    """Parse '9 a. m.' -> 9, '12 p. m.' -> 12, '1 p. m.' -> 13, '12 a. m.' -> 0."""
    m = re.search(r"(\d{1,2})\s*([ap])", label.lower())
    if not m:
        return -1
    h, ap = int(m.group(1)), m.group(2)
    if ap == "a":
        return 0 if h == 12 else h
    return 12 if h == 12 else h + 12


def _verdict(html: str) -> str:
    m = _VERDICT_RE.search(html)
    if not m:
        return "usual"
    return "quieter" if m.group(1).lower() == "menos" else "busier"


def parse_rows(rows: list[dict], now_hour: int) -> dict:
    """Turn the raw bar rows into {today[24], live}. Pure -- unit-testable.

    today[hour] = typical busyness 0..100 (normalized to the typical peak).
    live = the ycghLd overlay value for the current hour, 0..100 (capped)."""
    typical: dict[int, float] = {}
    live_raw: float | None = None
    for r in rows:
        hr = _first_hour(r.get("hour", ""))
        if hr < 0:
            continue
        if r.get("live"):
            live_raw = r["h"]
        else:
            typical[hr] = max(typical.get(hr, 0.0), r["h"])
    if not typical:
        return {"ok": False, "error": "no typical bars parsed"}
    peak = max(typical.values()) or 1.0
    today = [0] * 24
    for hr, h in typical.items():
        today[hr] = max(0, min(100, round(h / peak * 100)))
    live: int | None = None
    if live_raw is not None:
        live = max(0, min(100, round(live_raw / peak * 100)))
    elif today[now_hour]:
        live = today[now_hour]  # no live overlay -> fall back to the hour's typical
    return {"ok": True, "today": today, "live": live}


def scrape_live(query: str, tz) -> dict:
    """Scrape Google popular times. Never raises; returns ok=False on any problem."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:  # playwright not installed
        return {"ok": False, "error": f"playwright unavailable: {e}"}

    url = "https://www.google.com/search?hl=es&q=" + query.replace(" ", "+")
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE),
                channel="chrome",
                headless=True,
                locale="es-CO",
                viewport={"width": 1300, "height": 950},
                args=["--disable-blink-features=AutomationControlled", "--lang=es-CO"],
            )
            try:
                pg = ctx.pages[0] if ctx.pages else ctx.new_page()
                pg.add_init_script(
                    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
                )
                pg.goto(url, wait_until="domcontentloaded", timeout=60000)
                if "/sorry/" in pg.url:
                    return {"ok": False, "error": "google captcha (rate-limited)"}
                pg.wait_for_timeout(4500)
                r = pg.evaluate(_EXTRACT_JS)
                html = pg.content()
            finally:
                ctx.close()
    except Exception as e:
        return {"ok": False, "error": f"scrape failed: {e}"}

    if not r.get("ok") or not r.get("rows"):
        return {"ok": False, "error": r.get("error", "no popular-times data in page")}

    now_hour = datetime.now(tz).hour
    parsed = parse_rows(r["rows"], now_hour)
    if not parsed.get("ok"):
        return parsed
    return {
        "ok": True,
        "today": parsed["today"],
        "live": parsed["live"],
        "verdict": _verdict(html),
    }


if __name__ == "__main__":  # manual probe
    from zoneinfo import ZoneInfo
    import json
    out = scrape_live("Fitness24Seven Quinta Paredes Bogota", ZoneInfo("America/Bogota"))
    print(json.dumps(out, ensure_ascii=False, indent=2))
