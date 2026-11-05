# ELBRAD · Variante A (Urban)

Landing page for **ELBRAD**, a fictional bicycle rental service in Hamburg.
Studienprojekt der Kunstschule Wandsbek, keine offizielle Seite.

Open `index.html` in a browser. It is a single self-contained file: fonts and images are embedded, and the only external request is the weather data.

## Live weather

The "Hamburg heute" section loads current data from [Open-Meteo](https://open-meteo.com/) on every page load, in `loadWeather()` at the end of `src/template.html`:

```
https://api.open-meteo.com/v1/forecast?latitude=53.55&longitude=9.99&current=temperature_2m,wind_speed_10m&hourly=precipitation_probability&forecast_days=1&timezone=Europe%2FBerlin
```

- Temperature from `current.temperature_2m`, wind from `current.wind_speed_10m`, timestamp from `current.time` (Berlin local time).
- Precipitation probability comes from the `hourly.time` entry with the same date and hour as `current.time`, at the same index.
- Loading, error (with "Erneut versuchen"), 10-second timeout and "Nicht verfügbar" for missing fields. No sample or fallback values.

Weather data: Open-Meteo, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Files

| Path | Contents |
| --- | --- |
| `index.html` | Built page (generated, do not edit by hand) |
| `src/template.html` | Source: HTML, CSS and JavaScript |
| `src/img/` | Images cropped from the Version A mockup created for this project |
| `src/fonts/` | Barlow and Barlow Condensed (SIL Open Font License 1.1) |
| `build.py` | Embeds fonts and images into `index.html` |
| `tests/test_page.py` | Headless Chrome checks (Playwright): layout, navigation, dialog, weather states |
| `docs/screenshots/` | Test screenshots, including the live run on 5 Nov 2026 |

## Rebuild and test

```
python3 build.py
pip install playwright && python3 tests/test_page.py
```

The tests use mocked API responses only to cover edge cases (zero values, missing fields, HTTP errors, timeout). The page itself never uses mock data.
