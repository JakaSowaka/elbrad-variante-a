"""Builds both versions of the ELBRAD page.

  Version A  ->  index.html             (single file: fonts and images embedded)
  Version B  ->  version-b/index.html   (images and fonts in version-b/assets/)

The weather logic lives once in src/shared/weather.js and is inlined into both
pages, so A and B fetch, validate and format the weather data identically.

Usage: python3 build.py
"""
import base64
import pathlib
import shutil

root = pathlib.Path(__file__).parent
weather_js = (root / "src/shared/weather.js").read_text(encoding="utf-8")


def build_a():
    src = (root / "src/template.html").read_text(encoding="utf-8")
    src = src.replace("{{WEATHER_JS}}", weather_js)
    assets = {
        "FONT_BC800I": "src/fonts/barlow-condensed-latin-800-italic.woff2",
        "FONT_BC700": "src/fonts/barlow-condensed-latin-700-normal.woff2",
        "FONT_B400": "src/fonts/barlow-latin-400-normal.woff2",
        "FONT_B600": "src/fonts/barlow-latin-600-normal.woff2",
        "IMG_HERO": "src/img/hero.jpg",
        "IMG_CITY": "src/img/citybike.jpg",
        "IMG_EBIKE": "src/img/ebike.jpg",
        "IMG_TOUR": "src/img/tourenrad.jpg",
    }
    for key, rel in assets.items():
        path = root / rel
        mime = "font/woff2" if path.suffix == ".woff2" else "image/jpeg"
        uri = f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()
        src = src.replace("{{%s}}" % key, uri)
    assert "{{" not in src, "unreplaced placeholder in Version A"
    (root / "index.html").write_text(src, encoding="utf-8")
    print("index.html", len(src) // 1024, "KB")


def build_b():
    """Version B. Images are NOT generated or copied here: they live directly in
    version-b/assets/img/ so they can be replaced by uploading files with the same names."""
    src_dir = root / "src/version-b"
    out_dir = root / "version-b"
    html = (src_dir / "template.html").read_text(encoding="utf-8")
    html = html.replace("{{WEATHER_JS}}", weather_js)
    assert "{{" not in html, "unreplaced placeholder in Version B"
    fonts = out_dir / "assets/fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    for f in sorted((src_dir / "fonts").glob("*.woff2")):
        shutil.copy2(f, fonts / f.name)
    missing = [n for n in IMAGES_B if not (out_dir / "assets/img" / n).exists()]
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print("version-b/index.html", len(html) // 1024, "KB", "| missing images: " + ", ".join(missing) if missing else "")


IMAGES_B = ["citybike.jpg", "ebike.jpg", "tourenrad.jpg", "saddle.jpg", "handlebar.jpg", "waterfront.jpg"]


if __name__ == "__main__":
    build_a()
    build_b()
