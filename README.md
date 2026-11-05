# ELBRAD

Landing page for **ELBRAD**, a fictional bicycle rental service in Hamburg, in two design versions.
Studienprojekt der Kunstschule Wandsbek, keine offizielle Seite.

| Version | File | Address on GitHub Pages |
| --- | --- | --- |
| A · Urban | `index.html` (single file, fonts and images embedded) | `/elbrad-variante-a/` |
| B · Industrial | `version-b/index.html` (images and fonts in `version-b/assets/`) | `/elbrad-variante-a/version-b/` |

## Live weather (both versions)

The "Hamburg heute" section loads current data from [Open-Meteo](https://open-meteo.com/) on every page load. The logic exists once, in `src/shared/weather.js` (function `loadWeather()`), and `build.py` inlines it into both pages, so both versions behave the same:

```
https://api.open-meteo.com/v1/forecast?latitude=53.55&longitude=9.99&current=temperature_2m,wind_speed_10m&hourly=precipitation_probability&forecast_days=1&timezone=Europe%2FBerlin
```

- Temperature from `current.temperature_2m`, wind from `current.wind_speed_10m`, timestamp from `current.time`, read as Berlin time without converting to the visitor's timezone.
- Precipitation probability from the `hourly.time` entry with the same date and hour as `current.time`, at the same index.
- Loading and error messages, "Erneut versuchen", a 10-second timeout and "Nicht verfügbar" for each missing or invalid field. No sample or fallback values.

Weather data: Open-Meteo, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Replacing the Version B images

Upload six JPEG files with exactly these names to `version-b/assets/img/` (on GitHub: open the folder, **Add file → Upload files**, commit). Files with the same name replace the placeholders. No build step is needed.

| File | Subject | Ratio |
| --- | --- | --- |
| `citybike.jpg` | city bike with basket, side view, light grey studio floor (used in hero, Citybike card and mosaic) | 3:2 |
| `ebike.jpg` | e-bike, same style | 3:2 |
| `tourenrad.jpg` | touring bike, same style | 3:2 |
| `saddle.jpg` | saddle close-up | 4:3 |
| `handlebar.jpg` | handlebar close-up | 4:3 |
| `waterfront.jpg` | cyclist by the Hamburg waterfront | 4:3 |

Then record the source and rights in `docs/BILDQUELLEN.md`, and check that the image descriptions (`alt` texts in `src/version-b/template.html` and `version-b/index.html`) still match your pictures.

## Files

| Path | Contents |
| --- | --- |
| `src/template.html` | Version A source |
| `src/version-b/template.html` | Version B source |
| `src/shared/weather.js` | Weather logic shared by both versions |
| `build.py` | Builds `index.html` and `version-b/index.html` |
| `tests/test_page.py`, `tests/test_version_b.py` | Headless Chrome checks (Playwright) |
| `docs/BILDQUELLEN.md` | Image sources and licences |
| `docs/screenshots/` | Test screenshots |

## Rebuild and test

```
python3 build.py
pip install playwright
python3 tests/test_page.py
python3 tests/test_version_b.py
```

The tests use intercepted, mocked API responses only to cover edge cases (zero values, missing fields, HTTP errors, timeout). The pages themselves never use mock data.
