"""
Topology QA for annotated tiles.

Run this on every tile before accepting it. Catches the errors that vector
digitising produces and that only become visible once rasterised:

  1. Unlabelled pixels   — gaps between polygons
  2. Overlaps            — a pixel claimed by two classes
  3. Slivers             — tiny polygons, usually accidental
  4. Speckle             — isolated single pixels, usually a stray click
  5. Extent mismatch     — annotation not covering the full tile

Usage
-----
    python qa_topology.py --vector tile_0042.gpkg --reference tile_0042_rgb.tif
    python qa_topology.py --batch /path/to/annotations --reference-dir /path/to/tiles

Requires: geopandas, rasterio, numpy, shapely, scipy
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

CLASS_FIELD = "class"
VALID_CLASSES = {0, 1, 2, 3, 255}
UNCERTAIN = 255

# Thresholds. Tune after the pilot.
MAX_UNLABELLED_FRAC = 0.001      # 0.1% of tile
MIN_POLYGON_AREA_M2 = 400.0      # 4 pixels at 10 m
MIN_BLOB_PIXELS = 4              # isolated blobs smaller than this are speckle
MAX_UNCERTAIN_FRAC = 0.05        # 5% flagged uncertain triggers review


def rasterise(vector_path: Path, reference_path: Path) -> tuple[np.ndarray, dict]:
    """Burn polygons onto the reference grid. Unlabelled pixels become -1."""
    import geopandas as gpd
    import rasterio
    from rasterio.features import rasterize

    gdf = gpd.read_file(vector_path)
    with rasterio.open(reference_path) as src:
        meta = src.meta.copy()
        shape, transform, crs = (src.height, src.width), src.transform, src.crs

    if gdf.crs != crs:
        gdf = gdf.to_crs(crs)

    shapes = [(geom, int(val)) for geom, val in zip(gdf.geometry, gdf[CLASS_FIELD])]
    arr = rasterize(shapes, out_shape=shape, transform=transform,
                    fill=-1, dtype="int16", all_touched=False)
    meta.update(count=1, dtype="int16", nodata=-1)
    return arr, {"meta": meta, "gdf": gdf, "transform": transform}


def check_unlabelled(arr: np.ndarray) -> dict:
    n = int((arr == -1).sum())
    frac = n / arr.size
    return {
        "unlabelled_px": n,
        "unlabelled_frac": frac,
        "pass": frac <= MAX_UNLABELLED_FRAC,
    }


def check_overlaps(gdf) -> dict:
    """Any pair of polygons whose intersection has non-trivial area."""
    overlaps = []
    sindex = gdf.sindex
    for i, geom in enumerate(gdf.geometry):
        for j in sindex.query(geom):
            if j <= i:
                continue
            inter = geom.intersection(gdf.geometry.iloc[j])
            if not inter.is_empty and inter.area > 1.0:
                overlaps.append((i, int(j), float(inter.area)))
    return {"n_overlaps": len(overlaps), "overlaps": overlaps[:20],
            "pass": len(overlaps) == 0}


def check_slivers(gdf) -> dict:
    """Very small polygons, and very thin ones (high perimeter for their area)."""
    areas = gdf.geometry.area
    small = gdf[areas < MIN_POLYGON_AREA_M2]

    thinness = gdf.geometry.length ** 2 / gdf.geometry.area.replace(0, np.nan)
    thin = gdf[thinness > 200]      # a square scores 16; 200 is very elongated

    return {
        "n_small": int(len(small)),
        "n_thin": int(len(thin)),
        "small_ids": small.index.tolist()[:20],
        "thin_ids": thin.index.tolist()[:20],
        "pass": len(small) == 0 and len(thin) == 0,
    }


def check_speckle(arr: np.ndarray) -> dict:
    """Isolated blobs of a few pixels, usually stray clicks."""
    from scipy import ndimage

    speckle_total = 0
    per_class = {}
    for cls in sorted(VALID_CLASSES - {UNCERTAIN}):
        mask = arr == cls
        if not mask.any():
            continue
        lab, n = ndimage.label(mask)
        if n == 0:
            continue
        sizes = ndimage.sum(mask, lab, range(1, n + 1))
        small = int((sizes < MIN_BLOB_PIXELS).sum())
        per_class[cls] = small
        speckle_total += small
    return {"speckle_blobs": speckle_total, "per_class": per_class,
            "pass": speckle_total == 0}


def check_classes(arr: np.ndarray) -> dict:
    present = set(np.unique(arr).tolist()) - {-1}
    invalid = present - VALID_CLASSES
    unc = int((arr == UNCERTAIN).sum())
    unc_frac = unc / arr.size
    return {
        "classes_present": sorted(present),
        "invalid_classes": sorted(invalid),
        "uncertain_frac": unc_frac,
        "pass": not invalid and unc_frac <= MAX_UNCERTAIN_FRAC,
    }


def qa_tile(vector_path: Path, reference_path: Path, verbose: bool = True) -> dict:
    arr, ctx = rasterise(vector_path, reference_path)
    gdf = ctx["gdf"]

    result = {
        "tile": vector_path.stem,
        "unlabelled": check_unlabelled(arr),
        "overlaps": check_overlaps(gdf),
        "slivers": check_slivers(gdf),
        "speckle": check_speckle(arr),
        "classes": check_classes(arr),
    }
    result["pass"] = all(v["pass"] for k, v in result.items()
                         if isinstance(v, dict) and "pass" in v)

    if verbose:
        report(result)
    return result


def report(r: dict) -> None:
    status = "PASS" if r["pass"] else "FAIL"
    print(f"\n{'='*58}\n{r['tile']}  [{status}]\n{'='*58}")

    u = r["unlabelled"]
    print(f"  unlabelled pixels : {u['unlabelled_px']:6d} "
          f"({u['unlabelled_frac']*100:.3f}%)  {'ok' if u['pass'] else 'FAIL — gaps between polygons'}")

    o = r["overlaps"]
    print(f"  overlapping polys : {o['n_overlaps']:6d}  "
          f"{'ok' if o['pass'] else 'FAIL — run Difference or enable Avoid Overlap'}")

    s = r["slivers"]
    print(f"  small polygons    : {s['n_small']:6d}")
    print(f"  thin polygons     : {s['n_thin']:6d}  "
          f"{'ok' if s['pass'] else 'FAIL — check ids ' + str(s['small_ids'] + s['thin_ids'])}")

    sp = r["speckle"]
    print(f"  speckle blobs     : {sp['speckle_blobs']:6d}  {sp['per_class']}")

    c = r["classes"]
    print(f"  classes present   : {c['classes_present']}")
    print(f"  uncertain         : {c['uncertain_frac']*100:.2f}%")
    if c["invalid_classes"]:
        print(f"  INVALID CLASSES   : {c['invalid_classes']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vector", type=Path)
    ap.add_argument("--reference", type=Path)
    ap.add_argument("--batch", type=Path, help="directory of annotation files")
    ap.add_argument("--reference-dir", type=Path)
    ap.add_argument("--suffix", default="_rgb.tif")
    args = ap.parse_args()

    if args.batch:
        results = []
        for vec in sorted(args.batch.glob("*.gpkg")):
            ref = args.reference_dir / f"{vec.stem}{args.suffix}"
            if not ref.exists():
                print(f"  skip {vec.stem}: no reference raster")
                continue
            results.append(qa_tile(vec, ref))
        n_pass = sum(r["pass"] for r in results)
        print(f"\n{'='*58}\nSUMMARY: {n_pass}/{len(results)} tiles pass\n{'='*58}")
        for r in results:
            if not r["pass"]:
                print(f"  needs fixing: {r['tile']}")
    else:
        qa_tile(args.vector, args.reference)


if __name__ == "__main__":
    main()
