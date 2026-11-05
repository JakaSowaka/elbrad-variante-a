"""Turns the generated originals in src/version-b/originals/ into the web sizes used by Version B.

  citybike, ebike, tourenrad  ->  <name>-800.jpg (and citybike-1600.jpg), 3:2
  saddle, handlebar, waterfront ->  <name>-800.jpg and <name>-1200.jpg, 4:3

Only resizing, centre-cropping to the target ratio and JPEG compression happen here.
Usage: python3 tools/prepare_images.py
"""
import pathlib
from PIL import Image

root = pathlib.Path(__file__).resolve().parent.parent
src = root / "src/version-b/originals"
out = root / "src/version-b/img"
out.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "citybike": ((3, 2), [800, 1600]),
    "ebike": ((3, 2), [800]),
    "tourenrad": ((3, 2), [800]),
    "saddle": ((4, 3), [800, 1200]),
    "handlebar": ((4, 3), [800, 1200]),
    "waterfront": ((4, 3), [800, 1200]),
}


def crop_to_ratio(im, rw, rh):
    w, h = im.size
    target = rw / rh
    if abs(w / h - target) < 0.005:
        return im
    if w / h > target:
        nw = round(h * target)
        left = (w - nw) // 2
        return im.crop((left, 0, left + nw, h))
    nh = round(w / target)
    top = (h - nh) // 2
    return im.crop((0, top, w, top + nh))


for name, ((rw, rh), widths) in TARGETS.items():
    files = sorted(src.glob(name + ".*"))
    if not files:
        print("missing original:", name)
        continue
    im = crop_to_ratio(Image.open(files[0]).convert("RGB"), rw, rh)
    for w in widths:
        h = round(w * rh / rw)
        im.resize((w, h), Image.LANCZOS).save(out / f"{name}-{w}.jpg", quality=82, optimize=True, progressive=True)
        print(f"{name}-{w}.jpg", (w, h))
