# Live Google data (how it works & one-time setup)

`scrape/live.py` reads Google's **live** Popular Times for the gym — the same
"LIVE · Busier than usual" red bar you see on Google. Google strips this data
from ordinary automated browsers (headless Chromium, fresh profiles get nothing,
sometimes a CAPTCHA), but serves it to a **real Chrome** with a persistent
profile. So the daemon drives your installed Google Chrome (`channel="chrome"`,
headless) with a dedicated profile at:

```
~/.gympulse/chrome-profile/
```

## One-time setup
1. Google Chrome must be installed (`brew install --cask google-chrome`).
2. Normally nothing else — the profile works logged-out today.
3. **If live data ever stops** (payload shows `source: "forecast"` for days, or
   the error mentions `captcha`), warm the profile up once by hand:

   ```bash
   ~/.gympulse/app/.venv/bin/python - <<'PY'
   from playwright.sync_api import sync_playwright
   from pathlib import Path
   with sync_playwright() as p:
       ctx = p.chromium.launch_persistent_context(
           str(Path.home()/".gympulse"/"chrome-profile"),
           channel="chrome", headless=False)
       pg = ctx.pages[0] if ctx.pages else ctx.new_page()
       pg.goto("https://www.google.com")
       input("Solve any CAPTCHA / log into Google, then press Enter...")
       ctx.close()
   PY
   ```

## What gets extracted
- Hourly bars: `div.hIqKNb` heights = the typical curve (normalized to its peak).
- The current hour carries a second bar (`ycghLd` class) = the **live** value.
- Verdict: the "más/menos concurrido de lo habitual" phrase in the page HTML
  (the scrape requests `hl=es`; the UI translates to English).

## Fail-soft contract
`scrape_live()` **never raises.** On any failure (no Chrome, CAPTCHA, Google
markup change) it returns `ok=False` and `fetcher.py` silently falls back to the
self-tuned `WEEKLY_CURVE` forecast — the menu bar keeps working.

## Politeness / block-risk
Only the launchd daemon scrapes: once per 15 minutes, one page load. The
SwiftBar plugin never touches the network. If Google changes its markup, fix
`_EXTRACT_JS` in `scrape/live.py` (the class names above are the fragile part).
