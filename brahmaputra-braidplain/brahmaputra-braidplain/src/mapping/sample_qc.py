"""
Diagnostic: export the exact points the measurement code sampled, with the class
value read at each one, so you can see in QGIS whether sampling is hitting the
pixels you expect.

If the exported points labelled 3 sit on vegetation and those labelled 2 sit on
sand, the sampling is correct and the disagreement is in the manual measurement
or in which line was measured. If they do not, the sampling is at fault.

USAGE
    from sample_qc import export_samples

    export_samples(
        sections_shp = f'{ROOT}/validation/cross_sections.shp',
        raster_path  = f'{ROOT}/models/attention_unet/attention_unet_pred_2025_braidplain.tif',
        out_path     = f'{ROOT}/validation/sample_points.gpkg',
        section_filter = None,     # or e.g. 'XS_16' / 16 to export just one
    )

Load the result in QGIS, style by the `class_val` column, and drop it over the
false colour composite.
"""

from __future__ import annotations

import numpy as np


def export_samples(sections_shp, raster_path, out_path,
                   id_field=None, section_filter=None):
    import geopandas as gpd
    import rasterio
    from shapely.geometry import Point

    gdf = gpd.read_file(sections_shp)
    print(f"Shapefile: {len(gdf)} features")
    print(f"  CRS      : {gdf.crs}")
    print(f"  columns  : {list(gdf.columns)}")
    print(f"  geom type: {gdf.geometry.geom_type.unique()}")

    with rasterio.open(raster_path) as src:
        print(f"\nRaster: {raster_path.split('/')[-1]}")
        print(f"  CRS       : {src.crs}")
        print(f"  resolution: {abs(src.transform.a)} m")
        print(f"  bounds    : {src.bounds}")

        if gdf.crs != src.crs:
            print(f"  reprojecting sections {gdf.crs} -> {src.crs}")
            gdf = gdf.to_crs(src.crs)

        # Does every line actually fall inside the raster?
        b = src.bounds
        for idx, row in gdf.iterrows():
            minx, miny, maxx, maxy = row.geometry.bounds
            inside = (minx >= b.left and maxx <= b.right and
                      miny >= b.bottom and maxy <= b.top)
            if not inside:
                print(f"  WARNING: feature {idx} extends outside the raster")

        records = []
        res = abs(src.transform.a)

        for idx, row in gdf.iterrows():
            name = str(row[id_field]) if id_field else f"XS_{idx + 1:02d}"
            if section_filter is not None and str(section_filter) not in (name, str(idx)):
                continue

            geom = row.geometry
            if geom.geom_type == "MultiLineString":
                geom = max(geom.geoms, key=lambda g: g.length)

            n = max(int(np.ceil(geom.length / res)), 2)
            dists = np.linspace(0, geom.length, n)
            pts = [geom.interpolate(d) for d in dists]
            vals = [v[0] for v in src.sample([(p.x, p.y) for p in pts])]

            print(f"\n  {name}: length {geom.length/1000:.3f} km, {n} samples")
            print(f"    start {pts[0].x:.1f}, {pts[0].y:.1f}")
            print(f"    end   {pts[-1].x:.1f}, {pts[-1].y:.1f}")
            uniq, counts = np.unique(vals, return_counts=True)
            for u, c in zip(uniq, counts):
                print(f"    class {u}: {c:4d} px = {c*res/1000:.3f} km")

            for i, (p, d, v) in enumerate(zip(pts, dists, vals)):
                records.append({
                    "geometry": Point(p.x, p.y),
                    "section": name,
                    "sample_i": i,
                    "dist_m": float(d),
                    "class_val": int(v),
                })

    out = gpd.GeoDataFrame(records, crs=src.crs)
    driver = "GPKG" if str(out_path).endswith(".gpkg") else "GeoJSON"
    out.to_file(out_path, driver=driver)
    print(f"\nWrote {len(out)} sample points to {out_path}")
    print("Load in QGIS, style by class_val, overlay on the false colour.")
    return out


def compare_line_to_manual(sections_shp, raster_path, id_field=None):
    """Print every section's totals so you can find which one you measured.

    If your manual notes are labelled differently from the shapefile row order,
    the numbers will tell you which feature actually corresponds.
    """
    import geopandas as gpd
    import rasterio
    import pandas as pd

    gdf = gpd.read_file(sections_shp)
    rows = []
    with rasterio.open(raster_path) as src:
        if gdf.crs != src.crs:
            gdf = gdf.to_crs(src.crs)
        res = abs(src.transform.a)
        for idx, row in gdf.iterrows():
            geom = row.geometry
            if geom.geom_type == "MultiLineString":
                geom = max(geom.geoms, key=lambda g: g.length)
            n = max(int(np.ceil(geom.length / res)), 2)
            pts = [geom.interpolate(d) for d in np.linspace(0, geom.length, n)]
            v = np.array([x[0] for x in src.sample([(p.x, p.y) for p in pts])])
            rows.append({
                "row": idx,
                "name": str(row[id_field]) if id_field else f"XS_{idx+1:02d}",
                "len_km": geom.length / 1000,
                "water_km": (v == 1).sum() * res / 1000,
                "bare_km": (v == 2).sum() * res / 1000,
                "veg_km": (v == 3).sum() * res / 1000,
                "bg_km": (v == 0).sum() * res / 1000,
            })
    df = pd.DataFrame(rows).set_index("row")
    print(df.round(3).to_string())
    return df
