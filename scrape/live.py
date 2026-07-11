"""Scrape Google's live Popular Times for the gym using the user's real Chrome.

Google serves Popular Times to a normal logged-in browser but strips it from the
bundled/headless Chromium that automation usually uses. So we drive the user's
installed Chrome (channel="chrome") with a dedicated persistent profile at
~/.gympulse/chrome-profile — Google treats it as a real browser.

Returns a dict {today: [24 ints], live: int|None, verdict: str, ok: bool, ...}
or a soft failure (ok=False) — NEVER raises. The caller falls back to the forecast.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

PROFILE = Path.home() / ".gympulse" / "chrome-profile"

# JS run in the page: pull the popular-times widget's hourly bars + live verdict.
# Bars render as (empty, fill) height-div pairs summing to a constant; the fill
# fraction is the busyness. Hour labels ("4 a. m." ..) give the starting hour.
_EXTRACT_JS = r"""() => {
  const cont = document.querySelector('.OYzgjc');
  if (!cont) return {ok:false, error:'popular-times widget not found'};
  // hourly bar fills, in render order: bars are (empty, fill) height-div pairs;
  // busyness = fill/(empty+fill). Google renders >1 day-tab separated by a 0 bar.
  const hs = [...cont.querySelectorAll('div[style*="height"]')]
    .map(d => parseInt((d.getAttribute('style').match(/height:\s*(\d+)/)||[])[1]||0));
  const fills = [];
  for (let i = 0; i + 1 < hs.length; i += 2) {
    const empty = hs[i], fill = hs[i+1], tot = empty + fill;
    fills.push(tot > 0 ? Math.round(fill / tot * 100) : 0);
  }
  const hourLabels = [...cont.querySelectorAll('[aria-label]')]
    .map(e => e.getAttribute('aria-label'))
    .filter(a => a && /\b\d{1,2}\s*[ap]\.?\s*m\.?/i.test(a) && a.length < 12);
  const leaf = [...cont.querySelectorAll('*')]
    .filter(e => e.children.length === 0 && /de lo habitual/i.test(e.textContent||''));
  const verdictText = leaf.length ? leaf[0].textContent.trim() : '';
  return {ok:true, fills, hourLabels, verdictText};
}"""


def _longest_run(fills: list[int]) -> tuple[list[int], int]:
    """Google renders multiple day-tabs separated by a 0 bar. Return the longest
    non-zero run (the selected day's curve) and its start index in `fills`."""
    best: list[int] = []
    best_start = 0
    cur: list[int] = []
    start = 0
    for i, v in enumerate(fills + [0]):
        if v > 0:
            if not cur:
                start = i
            cur.append(v)
        else:
            if len(cur) > len(best):
                best, best_start = cur, start
            cur = []
    return best, best_start


def _first_hour(label: str) -> int:
    """Parse '4 a. m.' -> 4, '12 p. m.' -> 12, '1 p. m.' -> 13, '12 a. m.' -> 0."""
    m = re.search(r"(\d{1,2})\s*([ap])", label.lower().replace(" ", " "))
    if not m:
        return 6  # sensible default; Google's graph usually starts ~6am
    h, ap = int(m.group(1)), m.group(2)
    if ap == "a":
        return 0 if h == 12 else h
    return 12 if h == 12 else h + 12


def _verdict(text: str) -> str:
    t = text.lower()
    if "más concurrido" in t or "mas concurrido" in t:
        return "busier"
    if "menos concurrido" in t:
        return "quieter"
    return "usual"


def _to_24h(fills: list[int], first_hour: int) -> list[int]:
    """Reindex the render-order fills (starting at first_hour) into a 0..23 array."""
    today = [0] * 24
    for i, v in enumerate(fills[:24]):
        today[(first_hour + i) % 24] = max(0, min(100, v))
    return today


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
            finally:
                ctx.close()
    except Exception as e:
        return {"ok": False, "error": f"scrape failed: {e}"}

    if not r.get("ok") or not r.get("fills"):
        return {"ok": False, "error": r.get("error", "no popular-times data in page")}

    day, start = _longest_run(r["fills"])
    if not day:
        return {"ok": False, "error": "no non-empty day curve"}
    # Anchor: the Nth hour-label lines up with the Nth bar of the selected day.
    labels = r.get("hourLabels", [])
    first_hour = _first_hour(labels[start]) if start < len(labels) else _first_hour(
        labels[0] if labels else ""
    )
    today = _to_24h(day, first_hour)
    now_hour = datetime.now(tz).hour
    live = today[now_hour] or None
    return {
        "ok": True,
        "today": today,
        "live": live,
        "verdict": _verdict(r.get("verdictText", "")),
        "verdict_text": r.get("verdictText", ""),
    }


if __name__ == "__main__":  # manual probe
    from zoneinfo import ZoneInfo
    import json
    out = scrape_live("Fitness24Seven Quinta Paredes Bogota", ZoneInfo("America/Bogota"))
    print(json.dumps(out, ensure_ascii=False, indent=2))
