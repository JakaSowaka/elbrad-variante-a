"""Builds index.html from src/template.html by embedding fonts and images as data URIs.
Usage: python3 build.py"""
import base64, pathlib

root = pathlib.Path(__file__).parent
src = (root / "src/template.html").read_text(encoding="utf-8")
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
assert "{{" not in src, "unreplaced placeholder"
(root / "index.html").write_text(src, encoding="utf-8")
print("index.html written,", len(src) // 1024, "KB")
