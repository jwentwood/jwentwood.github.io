"""Build the resized copies in images/sizes/ from the originals in images/.

Every images/<name>.webp gets images/sizes/<name>-<width>.webp for each
width in WIDTHS that is not wider than the original (never upscaled).
ICON_SOURCE also gets a square icon-192.webp for the browser tab.

images/sizes/sources.json records a hash of each original, so a copy is
only rebuilt when its original changes or the copy is missing. Copies of
originals that no longer exist are deleted.
"""

import hashlib
import json
from pathlib import Path

from PIL import Image

SRC = Path("images")
OUT = SRC / "sizes"
MANIFEST = OUT / "sources.json"

WIDTHS = (320, 480, 640, 960, 1440, 1920)
QUALITY = 92
ICON_SOURCE = "jwentwood"
ICON_SIZE = 192


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outputs_for(name, width):
    files = [OUT / f"{name}-{w}.webp" for w in WIDTHS if w <= width]
    if name == ICON_SOURCE:
        files.append(OUT / f"icon-{ICON_SIZE}.webp")
    return files


def build(src, name):
    im = Image.open(src)
    im = im.convert("RGBA" if im.has_transparency_data else "RGB")
    for w in WIDTHS:
        if w > im.width:
            continue
        h = round(im.height * w / im.width)
        im.resize((w, h), Image.LANCZOS).save(
            OUT / f"{name}-{w}.webp", quality=QUALITY, method=6
        )
    if name == ICON_SOURCE:
        s = min(im.size)
        left, top = (im.width - s) // 2, (im.height - s) // 2
        icon = im.crop((left, top, left + s, top + s))
        icon.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS).save(
            OUT / f"icon-{ICON_SIZE}.webp", quality=90, method=6
        )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        manifest = json.loads(MANIFEST.read_text())
    except FileNotFoundError:
        manifest = {}

    keep = set()
    new_manifest = {}
    for src in sorted(SRC.glob("*.webp")):
        name = src.stem
        digest = sha256(src)
        with Image.open(src) as im:
            expected = outputs_for(name, im.width)
        keep.update(expected)
        new_manifest[name] = digest
        if manifest.get(name) != digest or not all(p.exists() for p in expected):
            print(f"Building copies of {src}")
            build(src, name)

    for f in OUT.glob("*.webp"):
        if f not in keep:
            print(f"Removing stale {f}")
            f.unlink()

    MANIFEST.write_text(json.dumps(new_manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
