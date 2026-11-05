"""Headless checks for dist/index.html. Mocked API responses are used ONLY here,
via request interception, to exercise edge cases. The page itself has no mock data."""
import json, time, pathlib, sys
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = (ROOT / "index.html").as_uri()
SHOTS = ROOT / "tests/output"; SHOTS.mkdir(exist_ok=True)
API = "https://api.open-meteo.com/v1/forecast?latitude=53.55&longitude=9.99&current=temperature_2m,wind_speed_10m&hourly=precipitation_probability&forecast_days=1&timezone=Europe%2FBerlin"
results = []

def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))

def payload(temp=10.3, wind=12.4, probs=None, cur_time="2026-11-05T15:45", day="2026-11-05", drop=()):
    probs = probs if probs is not None else [i * 3 + 1 for i in range(24)]  # index 15 -> 46
    d = {"latitude": 53.54, "longitude": 10.0, "utc_offset_seconds": 3600, "timezone": "Europe/Berlin",
         "timezone_abbreviation": "GMT+1",
         "current_units": {"time": "iso8601", "interval": "seconds", "temperature_2m": "°C", "wind_speed_10m": "km/h"},
         "current": {"time": cur_time, "interval": 900, "temperature_2m": temp, "wind_speed_10m": wind},
         "hourly_units": {"time": "iso8601", "precipitation_probability": "%"},
         "hourly": {"time": [f"{day}T{h:02d}:00" for h in range(24)], "precipitation_probability": probs}}
    for path in drop:
        obj = d
        *parents, last = path.split(".")
        for p in parents: obj = obj[p]
        obj.pop(last, None)
    return d

def texts(page):
    return page.evaluate("""() => ({
      status: document.getElementById('weather-status').textContent,
      statusVisible: !document.getElementById('weather-status').classList.contains('sr-only'),
      errorShown: !document.getElementById('weather-error').hidden,
      statsShown: !document.getElementById('weather-stats').hidden,
      temp: document.getElementById('w-temp').textContent,
      precip: document.getElementById('w-precip').textContent,
      hour: document.getElementById('w-precip-hour').textContent,
      wind: document.getElementById('w-wind').textContent,
      time: document.getElementById('w-time').textContent })""")

def norm(s): return s.replace(" ", " ")

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])

    def new_page(width=1440, height=900, route=None, reduced=False):
        ctx = browser.new_context(viewport={"width": width, "height": height}, locale="de-DE",
                                  timezone_id="Europe/Berlin", reduced_motion="reduce" if reduced else "no-preference")
        page = ctx.new_page()
        page.console_errors = []
        page.requests = []
        page.on("console", lambda m: page.console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: page.console_errors.append(str(e)))
        page.on("request", lambda r: page.requests.append(r.url) if "open-meteo" in r.url else None)
        if route: page.route("**/api.open-meteo.com/**", route)
        return page

    def fulfill_json(data, status=200, delay=0):
        def h(route):
            if delay: time.sleep(delay)
            route.fulfill(status=status, content_type="application/json", body=json.dumps(data),
                          headers={"Access-Control-Allow-Origin": "*"})
        return h

    # 1. Real request without mocks: this sandbox's proxy blocks open-meteo, so this is a genuine network failure.
    p = new_page()
    p.goto(PAGE); p.wait_for_function("!document.getElementById('weather-error').hidden", timeout=15000)
    t = texts(p)
    check("real network failure -> error state", t["errorShown"] and t["status"] == "Wetterdaten gerade nicht erreichbar.", t["status"])
    check("request goes to the exact endpoint", p.requests and p.requests[0] == API, p.requests[:1])
    check("no fake values shown on failure", not t["statsShown"] and norm(t["time"]) == "Nicht verfügbar")
    p.screenshot(path=str(SHOTS / "weather-error.png"), clip={"x": 0, "y": p.evaluate("document.getElementById('wetter').offsetTop"), "width": 1440, "height": 260})
    p.context.close()

    # 2. Loading state: hold the request open, inspect, then answer it
    held = []
    p = new_page(route=lambda r: held.append(r))
    p.goto(PAGE)
    p.wait_for_function("document.querySelector('.weather-body').getAttribute('aria-busy') === 'true'", timeout=3000)
    t = texts(p)
    check("loading text shown while request pending", t["status"] == "Wetterdaten werden geladen …" and t["statusVisible"] and not t["statsShown"], t["status"])
    check("aria-busy during loading", True)
    p.screenshot(path=str(SHOTS / "weather-loading.png"), clip={"x": 0, "y": p.evaluate("document.getElementById('wetter').offsetTop"), "width": 1440, "height": 260})
    held[0].fulfill(status=200, content_type="application/json", body=json.dumps(payload()), headers={"Access-Control-Allow-Origin": "*"})
    p.wait_for_function("!document.getElementById('weather-stats').hidden", timeout=5000)
    check("loading -> loaded after response", norm(texts(p)["temp"]) == "10,3 °C")
    p.context.close()

    # 3. Normal response, desktop + screenshots
    p = new_page(route=fulfill_json(payload()))
    p.goto(PAGE); p.wait_for_function("!document.getElementById('weather-stats').hidden")
    t = texts(p)
    check("temperature formatted", norm(t["temp"]) == "10,3 °C", t["temp"])
    check("wind formatted", norm(t["wind"]) == "12,4 km/h", t["wind"])
    check("precip uses matching hour index 15 (not index 0)", norm(t["precip"]) == "46 %", t["precip"])
    check("precip hour label", norm(t["hour"]) == "Stundenwert 15:00 Uhr", t["hour"])
    check("Stand timestamp", norm(t["time"]) == "05.11.2026, 15:45 Uhr", t["time"])
    check("success announced in live region", "Wetterdaten geladen" in t["status"] and not t["statusVisible"], norm(t["status"]))
    check("live region is polite status", p.evaluate("[document.getElementById('weather-status').getAttribute('role'), document.getElementById('weather-status').getAttribute('aria-live')]") == ["status", "polite"])
    p.wait_for_timeout(300)
    p.screenshot(path=str(SHOTS / "desktop-full.png"), full_page=True)
    p.screenshot(path=str(SHOTS / "desktop-fold.png"))
    check("no console errors (desktop)", not p.console_errors, p.console_errors)

    # Navigation
    for label, target in [("Räder", "raeder"), ("So geht’s", "so-gehts"), ("Preise", "preise")]:
        p.evaluate("window.scrollTo(0,0)"); p.wait_for_timeout(100)
        p.get_by_role("link", name=label, exact=True).click(); p.wait_for_timeout(1200)
        top = p.evaluate(f"document.getElementById('{target}').getBoundingClientRect().top")
        maxed = p.evaluate("Math.ceil(scrollY + innerHeight) >= document.documentElement.scrollHeight")
        check(f"nav '{label}' scrolls to #{target}", abs(top) < 40 or (maxed and top > 0), f"top={top:.0f}, at bottom={maxed}")

    # Booking dialog via keyboard
    p.evaluate("window.scrollTo(0,0)")
    hero_btn = p.get_by_role("button", name="Jetzt Rad buchen")
    hero_btn.focus(); p.keyboard.press("Enter"); p.wait_for_timeout(200)
    check("dialog opens from hero button", p.evaluate("document.getElementById('booking').open"))
    check("focus moves into dialog", p.evaluate("document.getElementById('booking').contains(document.activeElement)"),
          p.evaluate("document.activeElement.id"))
    check("dialog has accessible name", p.get_by_role("dialog", name="Rad buchen").count() == 1)
    check("dialog has no text/email/payment inputs", p.evaluate("document.querySelectorAll('#booking input:not([type=radio]), #booking select, #booking textarea').length") == 0)
    p.keyboard.press("ArrowDown"); p.keyboard.press("Enter"); p.wait_for_timeout(200)
    res = norm(p.text_content("#booking-result"))
    check("keyboard selection + Enter confirms E-Bike", res.startswith("Deine Wahl: E-Bike (25 € / Tag)"), res)
    p.screenshot(path=str(SHOTS / "dialog-desktop.png"))
    p.keyboard.press("Escape"); p.wait_for_timeout(200)
    check("Escape closes dialog", not p.evaluate("document.getElementById('booking').open"))
    check("focus returns to trigger", p.evaluate("document.activeElement.textContent.trim()") == "Jetzt Rad buchen")
    p.get_by_role("button", name="Rad buchen", exact=True).click(); p.wait_for_timeout(150)
    p.evaluate("document.querySelectorAll('#booking input').forEach(i => i.checked = false)")
    p.get_by_role("button", name="Auswahl bestätigen").click()
    check("confirm without choice asks to pick", "Bitte wähle" in p.text_content("#booking-result"))
    p.get_by_role("button", name="Dialog schließen").click()
    check("close (X) button works", not p.evaluate("document.getElementById('booking').open"))
    p.get_by_role("button", name="Rad buchen", exact=True).click(); p.wait_for_timeout(150)
    p.mouse.click(5, 5)
    check("backdrop click closes", not p.evaluate("document.getElementById('booking').open"))

    # Focus ring visible
    p.goto(PAGE); p.wait_for_timeout(300); p.keyboard.press("Tab")
    check("skip link first in tab order", p.evaluate("document.activeElement.className") == "skip-link")
    p.keyboard.press("Tab"); p.keyboard.press("Tab")
    oc = p.evaluate("getComputedStyle(document.activeElement).outlineStyle + ' ' + getComputedStyle(document.activeElement).outlineWidth")
    check("visible focus outline on nav link", oc.startswith("solid 3px"), oc)
    p.screenshot(path=str(SHOTS / "focus-nav.png"), clip={"x": 0, "y": 0, "width": 1440, "height": 140})
    p.context.close()

    # 4. Zero values, and first array entry is NOT the matching hour
    probs = [77] + [5] * 23; probs[9] = 0
    p = new_page(route=fulfill_json(payload(temp=0, wind=0, probs=probs, cur_time="2026-11-05T09:00")))
    p.goto(PAGE); p.wait_for_function("!document.getElementById('weather-stats').hidden")
    t = texts(p)
    check("zero temperature", norm(t["temp"]) == "0,0 °C", t["temp"])
    check("zero wind", norm(t["wind"]) == "0,0 km/h", t["wind"])
    check("zero precip at matching hour (first entry is 77)", norm(t["precip"]) == "0 %" and norm(t["hour"]) == "Stundenwert 09:00 Uhr", f'{t["precip"]} / {t["hour"]}')
    p.context.close()

    p = new_page(route=fulfill_json(payload(temp=-0.04)))
    p.goto(PAGE); p.wait_for_function("!document.getElementById('weather-stats').hidden")
    check("-0.04 shows 0,0 not -0,0", norm(texts(p)["temp"]) == "0,0 °C", texts(p)["temp"])
    p.context.close()

    p = new_page(route=fulfill_json(payload(temp=-3.25)))
    p.goto(PAGE); p.wait_for_function("!document.getElementById('weather-stats').hidden")
    check("negative temperature", norm(texts(p)["temp"]) in ("-3,2 °C", "-3,3 °C"), texts(p)["temp"])
    p.context.close()

    # 5. Missing / invalid fields
    probs = [10] * 24; probs[15] = None
    p = new_page(route=fulfill_json(payload(wind="12", probs=probs, drop=("current.temperature_2m",))))
    p.goto(PAGE); p.wait_for_function("!document.getElementById('weather-stats').hidden")
    t = texts(p)
    check("missing temperature -> Nicht verfügbar", t["temp"] == "Nicht verfügbar", t["temp"])
    check("string wind -> Nicht verfügbar", t["wind"] == "Nicht verfügbar", t["wind"])
    check("null precip at hour -> Nicht verfügbar", t["precip"] == "Nicht verfügbar", t["precip"])
    check("valid Stand still shown", norm(t["time"]) == "05.11.2026, 15:45 Uhr", t["time"])
    p.screenshot(path=str(SHOTS / "weather-missing.png"), clip={"x": 0, "y": p.evaluate("document.getElementById('wetter').offsetTop"), "width": 1440, "height": 260})
    p.context.close()

    p = new_page(route=fulfill_json(payload(day="2026-11-04")))
    p.goto(PAGE); p.wait_for_function("!document.getElementById('weather-stats').hidden")
    check("no matching hour -> precip Nicht verfügbar", texts(p)["precip"] == "Nicht verfügbar")
    p.context.close()

    p = new_page(route=fulfill_json(payload(drop=("current",))))
    p.goto(PAGE); p.wait_for_function("!document.getElementById('weather-stats').hidden")
    t = texts(p)
    check("no 'current' object -> all Nicht verfügbar", all(t[k] == "Nicht verfügbar" for k in ("temp", "wind", "precip", "time")), t)
    p.context.close()

    # 6. HTTP error, then retry succeeds
    state = {"fail": True}
    def flaky(route):
        if state["fail"]:
            route.fulfill(status=503, body="Service Unavailable", headers={"Access-Control-Allow-Origin": "*"})
        else:
            fulfill_json(payload())(route)
    p = new_page(route=flaky)
    p.goto(PAGE); p.wait_for_function("!document.getElementById('weather-error').hidden")
    check("HTTP 503 -> error state", texts(p)["status"] == "Wetterdaten gerade nicht erreichbar.")
    state["fail"] = False
    p.get_by_role("button", name="Erneut versuchen").click()
    p.wait_for_function("!document.getElementById('weather-stats').hidden")
    check("retry loads data", norm(texts(p)["temp"]) == "10,3 °C")
    check("focus kept in weather section after retry", p.evaluate("document.activeElement.id") == "weather-title")
    check("two requests made (initial + retry)", len(p.requests) == 2, len(p.requests))
    p.context.close()

    # 7. Invalid JSON
    p = new_page(route=lambda r: r.fulfill(status=200, content_type="application/json", body="<html>oops", headers={"Access-Control-Allow-Origin": "*"}))
    p.goto(PAGE); p.wait_for_function("!document.getElementById('weather-error').hidden")
    check("invalid JSON -> error state", True)
    p.context.close()

    # 8. Timeout: server never answers
    p = new_page(route=lambda r: None)
    t0 = time.time(); p.goto(PAGE)
    p.wait_for_function("!document.getElementById('weather-error').hidden", timeout=20000)
    el = time.time() - t0
    check("timeout -> error state after ~10 s", 9 <= el <= 14, f"{el:.1f}s")
    p.context.close()

    # 9. Responsive: no horizontal scroll, mobile screenshots
    for w in (320, 375, 390, 768, 1024, 1280, 1920):
        p = new_page(width=w, height=900, route=fulfill_json(payload()))
        p.goto(PAGE); p.wait_for_function("!document.getElementById('weather-stats').hidden"); p.wait_for_timeout(200)
        sw = p.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        check(f"no horizontal scroll at {w}px", sw[0] <= sw[1], sw)
        small = p.evaluate("""() => [...document.querySelectorAll('p,a,button,h1,h2,h3,span,label,legend')]
            .filter(e => e.offsetParent && e.textContent.trim() && !e.closest('.sr-only'))
            .map(e => parseFloat(getComputedStyle(e).fontSize)).filter(s => s < 14).length""")
        check(f"no visible text under 14px at {w}px", small == 0, small)
        if w in (390, 1024, 1920):
            p.screenshot(path=str(SHOTS / f"full-{w}.png"), full_page=True)
        if w == 390:
            p.get_by_role("button", name="Rad buchen", exact=True).click(); p.wait_for_timeout(200)
            p.screenshot(path=str(SHOTS / "dialog-390.png"))
            sw = p.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
            check("dialog fits at 390px", sw[0] <= sw[1], sw)
        p.context.close()

    # 10. Reduced motion
    p = new_page(route=fulfill_json(payload()), reduced=True)
    p.goto(PAGE)
    check("reduced motion: no smooth scroll", p.evaluate("getComputedStyle(document.documentElement).scrollBehavior") == "auto")
    p.context.close()
    p = new_page(route=fulfill_json(payload()))
    p.goto(PAGE)
    check("default: smooth scroll", p.evaluate("getComputedStyle(document.documentElement).scrollBehavior") == "smooth")
    meta = p.evaluate("document.querySelector('meta[name=robots]').content")
    check("robots meta", meta == "noindex, nofollow", meta)
    foot = p.evaluate("document.querySelector('.site-footer p').textContent")
    check("footer notice exact", foot == "Studienprojekt der Kunstschule Wandsbek, keine offizielle Seite", foot)
    att = p.evaluate("[...document.querySelectorAll('.weather-meta a')].map(a => [a.textContent.trim(), a.href])")
    check("attribution link", att[0] == ["Wetterdaten: Open-Meteo", "https://open-meteo.com/"], att)
    imgs = p.evaluate("[...document.images].map(i => [i.alt.length, i.naturalWidth])")
    check("all images have alt text and load", all(a > 20 and w > 0 for a, w in imgs), imgs)
    fonts = p.evaluate("document.fonts.ready.then(() => [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + ' ' + f.weight + ' ' + f.style))")
    check("embedded fonts load", len(fonts) >= 3, fonts)
    p.context.close()
    browser.close()

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
