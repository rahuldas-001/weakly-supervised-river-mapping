"""
Automated morphological measurement along cross-sections.

Reads a shapefile of cross-section lines and a classified prediction GeoTIFF,
samples the classes along each line, and returns the same measurements you
currently make by hand.

WHY THIS IS AUTOMATABLE
-----------------------
Measuring from an RGB image needs human judgement: you decide where the water
ends and the sand begins. Measuring from a classified raster does not. Every
pixel already carries a class label, so a measurement along a line is just
counting runs of pixel values.

Keep the RGB measurements manual. That is your reference and it should be human.
Everything read off a classified raster should not be.

USAGE
-----
    from crosssection_measure import measure_sections, compare_with_manual

    auto = measure_sections(
        sections_shp = '/path/cross_sections.shp',
        raster_path  = '/path/attention_unet_pred_2025_braidplain.tif',
    )
    print(auto)

    compare_with_manual(auto, manual_df)     # R2 per variable

REQUIRES: geopandas, rasterio, numpy, pandas, shapely, scipy
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Class codes. Change here if your raster uses different values.
CLASS_BACKGROUND = 0
CLASS_WATER = 1
CLASS_BARE_BAR = 2
CLASS_VEG_BAR = 3

# A run shorter than this is treated as speckle, not a real feature.
# 3 pixels at 10 m = 30 m. Raise it if predictions are noisy.
MIN_FEATURE_PX = 3


# ─────────────────────────────────────────────────────────────────────────────
def sample_along_line(line, raster, n_samples=None):
    """Read raster class values at evenly spaced points along a line.

    Sampling interval defaults to one pixel width, which is the finest spacing
    that carries information.
    """
    res = abs(raster.transform.a)
    if n_samples is None:
        n_samples = max(int(np.ceil(line.length / res)), 2)

    distances = np.linspace(0, line.length, n_samples)
    points = [line.interpolate(d) for d in distances]
    coords = [(p.x, p.y) for p in points]

    values = np.array([v[0] for v in raster.sample(coords)], dtype=np.int16)
    return values, distances, res


def runs_of(values, target_classes, min_px=MIN_FEATURE_PX):
    """Find contiguous runs of the given classes.

    Returns a list of (start_index, length_in_pixels). Runs shorter than
    `min_px` are discarded so that single stray pixels do not inflate counts.
    """
    mask = np.isin(values, target_classes)
    runs, start = [], None

    for i, m in enumerate(mask):
        if m and start is None:
            start = i
        elif not m and start is not None:
            if i - start >= min_px:
                runs.append((start, i - start))
            start = None
    if start is not None and len(mask) - start >= min_px:
        runs.append((start, len(mask) - start))

    return runs


def measure_one_section(values, res_m, min_px=MIN_FEATURE_PX):
    """Compute all morphological variables for a single sampled line."""
    to_km = res_m / 1000.0

    n_water = int(np.sum(values == CLASS_WATER))
    n_bare = int(np.sum(values == CLASS_BARE_BAR))
    n_veg = int(np.sum(values == CLASS_VEG_BAR))
    n_bar = n_bare + n_veg
    n_braidplain = n_water + n_bar

    water_runs = runs_of(values, [CLASS_WATER], min_px)
    bar_runs = runs_of(values, [CLASS_BARE_BAR, CLASS_VEG_BAR], min_px)

    return {
        # widths: total across the section, not contiguous
        "channel_width_km": n_water * to_km,
        "bare_bar_width_km": n_bare * to_km,
        "veg_bar_width_km": n_veg * to_km,
        "total_bar_width_km": n_bar * to_km,
        "braidplain_width_km": n_braidplain * to_km,
        # counts
        "n_threads": len(water_runs),
        "n_bar_units": len(bar_runs),
        # useful extras
        "widest_thread_km": (max((l for _, l in water_runs), default=0) * to_km),
        "veg_fraction_of_bar": (n_veg / n_bar) if n_bar else np.nan,
        "n_samples": int(len(values)),
    }


# ─────────────────────────────────────────────────────────────────────────────
def measure_sections(sections_shp, raster_path, id_field=None,
                     min_px=MIN_FEATURE_PX, return_profiles=False):
    """Measure every cross-section in a shapefile against one prediction raster.

    Parameters
    ----------
    sections_shp : path to a line shapefile (or GeoPackage)
    raster_path  : path to a classified GeoTIFF, single band, values 0-3
    id_field     : column holding the section name. If None, uses the row index.
    min_px       : minimum run length, in pixels, to count as a feature
    return_profiles : also return the raw class values per section, for QC plots
    """
    import geopandas as gpd
    import rasterio

    gdf = gpd.read_file(sections_shp)

    with rasterio.open(raster_path) as src:
        if gdf.crs is None:
            raise ValueError("Cross-section shapefile has no CRS defined.")
        if gdf.crs != src.crs:
            print(f"  reprojecting sections: {gdf.crs} -> {src.crs}")
            gdf = gdf.to_crs(src.crs)

        rows, profiles = [], {}
        for idx, row in gdf.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            if geom.geom_type == "MultiLineString":
                geom = max(geom.geoms, key=lambda g: g.length)
            if geom.geom_type != "LineString":
                print(f"  skipping row {idx}: geometry is {geom.geom_type}")
                continue

            values, distances, res = sample_along_line(geom, src)

            name = str(row[id_field]) if id_field else f"XS_{idx + 1:02d}"
            rec = {"section": name, "length_km": geom.length / 1000.0}
            rec.update(measure_one_section(values, res, min_px))
            rows.append(rec)

            if return_profiles:
                profiles[name] = (values, distances)

    df = pd.DataFrame(rows).set_index("section")
    print(f"  measured {len(df)} sections from {raster_path.split('/')[-1]}")
    return (df, profiles) if return_profiles else df


# ─────────────────────────────────────────────────────────────────────────────
def compare_with_manual(auto_df, manual_df, pairs=None):
    """Compare automated measurements against manual ones.

    `pairs` maps manual column names to automated column names. Adjust it to
    match whatever your manual spreadsheet calls things.
    """
    from scipy import stats

    if pairs is None:
        pairs = {
            "ch": "channel_width_km",
            "bar": "total_bar_width_km",
            "veg": "veg_bar_width_km",
            "thr": "n_threads",
            "units": "n_bar_units",
        }

    print(f"\n{'variable':22s} {'r2':>7s} {'bias':>9s} {'MAE':>8s}  n")
    print("-" * 54)
    out = {}
    for man_col, auto_col in pairs.items():
        if man_col not in manual_df.columns or auto_col not in auto_df.columns:
            print(f"  {man_col} / {auto_col}: column missing, skipped")
            continue
        m = np.asarray(manual_df[man_col], dtype=float)
        a = np.asarray(auto_df[auto_col], dtype=float)[: len(m)]
        ok = ~(np.isnan(m) | np.isnan(a))
        if ok.sum() < 3:
            continue
        r, _ = stats.pearsonr(m[ok], a[ok])
        bias = float(np.mean(a[ok] - m[ok]))
        mae = float(np.mean(np.abs(a[ok] - m[ok])))
        out[auto_col] = {"r2": r ** 2, "bias": bias, "mae": mae, "n": int(ok.sum())}
        print(f"{auto_col:22s} {r**2:7.3f} {bias:+9.3f} {mae:8.3f}  {ok.sum()}")
    return pd.DataFrame(out).T


def plot_profiles(profiles, save_path=None, max_sections=7):
    """Draw the class sequence along each section. Use this for QC.

    If a measurement looks wrong, the profile shows why: a stray run of water
    inflating the thread count, or a bar split by a one-pixel gap.
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    names = list(profiles)[:max_sections]
    cmap = ListedColormap(["#2b2b2b", "#2b7bba", "#e8d4a0", "#4a8a3f"])

    fig, axes = plt.subplots(len(names), 1, figsize=(11, 1.1 * len(names)),
                             sharex=False)
    if len(names) == 1:
        axes = [axes]

    for ax, name in zip(axes, names):
        values, distances = profiles[name]
        ax.imshow(values[np.newaxis, :], aspect="auto", cmap=cmap,
                  vmin=0, vmax=3,
                  extent=[0, distances[-1] / 1000, 0, 1])
        ax.set_yticks([])
        ax.set_ylabel(name, rotation=0, ha="right", va="center", fontsize=8)
        ax.set_xlabel("distance along section (km)", fontsize=7)
        ax.tick_params(labelsize=7)

    fig.suptitle("Class profile along cross-sections "
                 "(dark = background, blue = water, sand = bare bar, "
                 "green = vegetated bar)", fontsize=9)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.show()


# ─────────────────────────────────────────────────────────────────────────────
def measure_multiple_rasters(sections_shp, raster_paths, id_field=None):
    """Measure the same sections against several rasters at once.

    Useful for comparing Attention U-Net, SegFormer, and the weak-label mask
    side by side, or for running every year of the series.
    """
    frames = {}
    for label, path in raster_paths.items():
        print(f"\n{label}:")
        frames[label] = measure_sections(sections_shp, path, id_field)
    return pd.concat(frames, names=["model", "section"])


if __name__ == "__main__":
    # Self-test on a synthetic profile: 3 threads, 2 bar units
    synth = np.array(
        [0] * 20 + [1] * 15 + [2] * 40 + [3] * 25 + [1] * 8 +
        [2] * 30 + [1] * 12 + [0] * 20, dtype=np.int16
    )
    r = measure_one_section(synth, res_m=10)
    print("Self-test on synthetic section:")
    for k, v in r.items():
        print(f"  {k:24s} {v}")
    assert r["n_threads"] == 3, "thread counting failed"
    assert r["n_bar_units"] == 2, "bar unit counting failed"
    print("\nPASS")
