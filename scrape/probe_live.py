"""Experiment: can real Chrome (persistent profile) read Google's live busyness?

Launches your installed Chrome via Playwright with a dedicated persistent profile
(~/.gympulse/chrome-profile) so Google treats it as a normal browser. Opens the
gym's Google Maps page, waits, and reports whether the live 'popular times' data
is present in the DOM.
"""
from __future__ import annotations
import sys, re
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE = Path.home() / ".gympulse" / "chrome-profile"
PROFILE.mkdir(parents=True, exist_ok=True)
QUERY = "Fitness24Seven Quinta Paredes Bogota"
URL = "https://www.google.com/maps/search/" + QUERY.replace(" ", "+")
HEADLESS = "--headless" in sys.argv
WAIT_MS = 90000 if "--login" in sys.argv else 8000

MARKERS = ["concurrencia", "Datos actuales", "Más concurrido", "menos concurrido",
           "ocupado", "Popular times", "usually", "En vivo", "Live"]

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE),
        channel="chrome",                 # REAL Chrome, not bundled Chromium
        headless=HEADLESS,
        locale="es-CO",
        viewport={"width": 1200, "height": 900},
        args=["--disable-blink-features=AutomationControlled", "--lang=es-CO"],
    )
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    print("navigating…", URL)
    pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
    if "--login" in sys.argv:
        print(">>> Log into Google + open the gym if needed. You have 90s. <<<")
    pg.wait_for_timeout(WAIT_MS)
    html = pg.content()
    print("final url:", pg.url[:90])
    print("title:", pg.title()[:60])
    print("captcha:", "/sorry/" in pg.url or "unusual traffic" in html.lower())
    hits = {m: html.count(m) for m in MARKERS if html.count(m)}
    print("MARKER HITS:", hits if hits else "NONE")
    labs = pg.eval_on_selector_all(
        "[aria-label*='concurrido'],[aria-label*='ocupad'],[aria-label*='concurrencia'],[aria-label*='busy']",
        "els=>els.map(e=>e.getAttribute('aria-label')).slice(0,8)")
    print("LIVE aria-labels:", labs)
    m = re.search(r'(\d{1,3})\s*%[^<]{0,30}(concurrido|ocupad|busy)', html, re.I)
    print("percent-ish match:", m.group(0) if m else None)
    ctx.close()
