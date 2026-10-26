#!/usr/bin/env python3
"""Render the actual research TIFF as a labelled, non-interpolated preview asset."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
import numpy as np
from PIL import Image, ImageDraw
import rasterio
from rasterio.enums import Resampling


def main():
    card = json.loads((ROOT / "registry/run_card.json").read_text())
    with rasterio.open(ROOT / card["artifact"]) as src:
        height, width = 690, 610
        width_m = src.bounds.right - src.bounds.left
        a = src.read(1, out_shape=(height, width), resampling=Resampling.nearest)
    with rasterio.open(ROOT / "data/sample_submission.tif") as src:
        fp = np.isfinite(src.read(1, out_shape=(height, width), resampling=Resampling.nearest))
    stops = np.array([0, .2, .4, .6, .9])
    colors = np.array([[228, 237, 230], [188, 212, 195], [105, 159, 144], [28, 100, 98], [9, 49, 61]])
    rgb = np.stack([np.interp(a, stops, colors[:, c]) for c in range(3)], axis=-1).astype(np.uint8)
    rgb[~fp] = [245, 245, 239]
    image = Image.fromarray(rgb).convert("RGBA")
    # Geographic grid is a cartographic guide, not a predictive feature.
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for x in range(0, width, 122):
        draw.line((x, 0, x, height), fill=(92, 120, 114, 35))
    for y in range(0, height, 115):
        draw.line((0, y, width, y), fill=(92, 120, 114, 35))
    draw.polygon([(width - 42, 23), (width - 48, 40), (width - 36, 40)], fill=(18, 63, 68, 255))
    draw.text((width - 45, 44), "N", fill=(18, 63, 68, 255))
    draw.line((28, height - 38, 28 + round(width * 100000 / width_m), height - 38), fill=(18, 63, 68, 255), width=3)
    draw.text((28, height - 29), "100 km", fill=(18, 63, 68, 255))
    result = Image.alpha_composite(image, overlay).convert("RGB")
    path = ROOT / "docs/assets/research-field.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    result.save(path, optimize=True)
    print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
