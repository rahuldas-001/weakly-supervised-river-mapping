"""
Export a lightweight optical composite from a 9-band inference scene.

WHY
The 9-band scene is heavy because it carries VV, VH and all seven Sentinel-2
bands at float32. For manual digitising you only need to see the imagery, so
this writes a small 8-bit file that opens instantly in QGIS.

WHAT IT WRITES
  <year>_rgb8.tif          true colour  (B4, B3, B2)
  <year>_falsecolour8.tif  NIR false colour (B8, B4, B3) - vegetation is red

The false colour is the one to digitise against. Vegetation is unmistakable in
it, which is exactly the boundary you are least sure about.

Byte scaling uses a 2-98 percentile stretch computed over the scene, so the
output is for visual interpretation only. Do not use these files for any
numerical work.

USAGE (Colab)
    from export_optical import export_optical
    export_optical(
        scene_path = f'{ROOT}/inference/scenes/inference_2019.tif',
        out_dir    = f'{ROOT}/validation/optical',
        year       = '2019',
    )
"""

from __future__ import annotations

import os

import numpy as np
import rasterio

# Band order in the 9-band stack. CHECK THIS against your BAND_NAMES before use.
BAND_INDEX = {
    "B2": 1, "B3": 2, "B4": 3, "B8": 4,
    "B8A": 5, "B11": 6, "B12": 7,
    "VV": 8, "VH": 9,
}


def _stretch_to_byte(arr, lo_pct=2, hi_pct=98, nodata_mask=None):
    """Percentile stretch to 0-255. Visual only."""
    valid = arr[np.isfinite(arr)]
    if nodata_mask is not None:
        valid = arr[np.isfinite(arr) & ~nodata_mask]
    if valid.size == 0:
        return np.zeros(arr.shape, dtype=np.uint8)

    lo, hi = np.percentile(valid, [lo_pct, hi_pct])
    if hi <= lo:
        hi = lo + 1.0

    out = np.clip((arr - lo) / (hi - lo), 0, 1) * 255
    out = np.nan_to_num(out, nan=0.0)
    return out.astype(np.uint8)


def _write_composite(scene_path, out_path, bands, lo_pct=2, hi_pct=98):
    with rasterio.open(scene_path) as src:
        idx = [BAND_INDEX[b] for b in bands]
        stack = []
        nodata_mask = None

        for i in idx:
            a = src.read(i).astype("float32")
            if src.nodata is not None:
                m = a == src.nodata
                nodata_mask = m if nodata_mask is None else (nodata_mask | m)
                a[m] = np.nan
            stack.append(a)

        byte_bands = [_stretch_to_byte(a, lo_pct, hi_pct, nodata_mask)
                      for a in stack]

        profile = src.profile.copy()
        profile.update(
            count=len(bands),
            dtype="uint8",
            nodata=0,
            compress="deflate",
            predictor=2,
            tiled=True,
            blockxsize=512,
            blockysize=512,
            photometric="RGB",
        )
        # drop float-only keys if present
        for k in ("scales", "offsets"):
            profile.pop(k, None)

        with rasterio.open(out_path, "w", **profile) as dst:
            for n, b in enumerate(byte_bands, start=1):
                dst.write(b, n)
            dst.build_overviews([2, 4, 8, 16], rasterio.enums.Resampling.average)
            dst.update_tags(ns="rio_overview", resampling="average")

    size_mb = os.path.getsize(out_path) / 1e6
    print(f"  {os.path.basename(out_path):32s} {size_mb:8.1f} MB  bands={bands}")


def export_optical(scene_path, out_dir, year, lo_pct=2, hi_pct=98):
    """Write true colour and false colour 8-bit composites for one scene."""
    os.makedirs(out_dir, exist_ok=True)

    with rasterio.open(scene_path) as src:
        orig_mb = os.path.getsize(scene_path) / 1e6
        print(f"Source: {os.path.basename(scene_path)}")
        print(f"  {src.count} bands, {src.dtypes[0]}, "
              f"{src.width} x {src.height}, {orig_mb:.1f} MB")
        if src.count < 9:
            print(f"  WARNING: expected 9 bands, found {src.count}. "
                  f"Check BAND_INDEX matches this file.")

    print("\nWriting:")
    _write_composite(scene_path,
                     os.path.join(out_dir, f"{year}_rgb8.tif"),
                     ["B4", "B3", "B2"], lo_pct, hi_pct)
    _write_composite(scene_path,
                     os.path.join(out_dir, f"{year}_falsecolour8.tif"),
                     ["B8", "B4", "B3"], lo_pct, hi_pct)

    print("\nDigitise against the false colour. Vegetation is red, sand is pale "
          "cyan or white, water is dark.")
    print("These files are 8-bit and stretched. Visual interpretation only.")


def export_all_years(scene_dir, out_dir, years, pattern="inference_{year}.tif"):
    """Convenience wrapper for several years at once."""
    for y in years:
        p = os.path.join(scene_dir, pattern.format(year=y))
        if not os.path.exists(p):
            print(f"skip {y}: {p} not found")
            continue
        print(f"\n{'='*60}\n{y}\n{'='*60}")
        export_optical(p, out_dir, y)
