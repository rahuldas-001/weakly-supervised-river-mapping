"""
Generate ten pilot annotation tiles for the braided river benchmark.

Run this in Colab. It selects tiles deliberately rather than randomly, so the
pilot covers the cases that are actually hard, and exports everything QGIS needs.

WHY STRATIFIED SELECTION
Ten random tiles from a braidplain would likely all be moderate cases. The point
of the pilot is to find where the class rules break, so tiles are chosen to span
vegetation cover, channel complexity, and braidplain edge conditions.

WHAT IS EXPORTED PER TILE
  <id>_rgb.tif        true colour, for digitising against
  <id>_falsecolour.tif NIR-red-green, vegetation stands out clearly
  <id>_stack.tif      all 9 bands, if you want to inspect SAR or indices
  <id>_braidplain.tif the fixed envelope, load as a boundary reference
  <id>_weaklabel.tif  the rule-based label

IMPORTANT: keep _weaklabel.tif SWITCHED OFF while you annotate. If you can see
the rule-based answer you will unconsciously agree with it, and the whole point
of the pilot is to measure how much the rules and a human differ. Annotate
blind, then turn it on and compare.

NOT TESTED AGAINST EARTH ENGINE FROM THIS ENVIRONMENT. Expect to fix small
things on the first run, particularly asset band names.
"""

import ee
import pandas as pd
from tqdm import tqdm

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION — edit these
# ─────────────────────────────────────────────────────────────────────────────
EE_PROJECT      = 'rahulds001'
BRAIDPLAIN_ASSET = 'projects/rahulds001/assets/braidplain_mask_v1'
DRIVE_FOLDER    = 'BRAHMA_MORPHO/pilot_tiles'

TILE_PX         = 512          # larger than training tiles: annotation needs context
RESOLUTION      = 10
TILE_M          = TILE_PX * RESOLUTION      # 5120 m
CRS             = 'EPSG:32646'

PILOT_YEAR      = '2024'
START, END      = f'{PILOT_YEAR}-02-01', f'{PILOT_YEAR}-03-31'

S2_BANDS        = ['B2', 'B3', 'B4', 'B8', 'B8A', 'B11', 'B12']
S1_BANDS        = ['VV', 'VH']
MAX_CLOUD       = 10
S1_PASS         = 'DESCENDING'

# Inference reach, Tezpur-Guwahati
AOI = ee.Geometry.Rectangle(
    [91.70033447265615, 26.080002725994902,
     92.8566455078124, 26.72086332207767], None, False
)

ee.Initialize(project=EE_PROJECT)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Build the composite (same logic as your existing pipeline)
# ─────────────────────────────────────────────────────────────────────────────
def mask_s2_clouds(image):
    scl = image.select('SCL')
    clear = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(7))
    return image.updateMask(clear)


def build_composite(aoi, start, end):
    s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
          .filterBounds(aoi).filterDate(start, end)
          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', MAX_CLOUD))
          .map(mask_s2_clouds).select(S2_BANDS))

    s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
          .filterBounds(aoi).filterDate(start, end)
          .filter(ee.Filter.eq('instrumentMode', 'IW'))
          .filter(ee.Filter.eq('orbitProperties_pass', S1_PASS))
          .select(S1_BANDS))

    return s2.median().addBands(s1.median()).clip(aoi)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Rule-based label, for comparison only
# ─────────────────────────────────────────────────────────────────────────────
def weak_label(img, braidplain):
    """Reproduce the existing four-class rules. Thresholds must match your
    pipeline exactly; if you change them there, change them here."""
    mndwi = img.normalizedDifference(['B3', 'B11']).rename('mndwi')
    ndvi  = img.normalizedDifference(['B8', 'B4']).rename('ndvi')

    nir, red, blue, swir = (img.select('B8'), img.select('B4'),
                            img.select('B2'), img.select('B11'))
    bsi = (swir.add(red).subtract(nir.add(blue))
           .divide(swir.add(red).add(nir).add(blue))).rename('bsi')

    msavi2 = (nir.multiply(2).add(1)
              .subtract(nir.multiply(2).add(1).pow(2)
                        .subtract(nir.subtract(red).multiply(8)).sqrt())
              .divide(2)).rename('msavi2')

    water = mndwi.gt(0)                                  # replace with your Otsu value
    bsi_thresh = ee.Number(bsi.updateMask(braidplain).reduceRegion(
        reducer=ee.Reducer.percentile([60]), geometry=AOI,
        scale=30, bestEffort=True, maxPixels=1e10).values().get(0))

    veg  = msavi2.gt(0.05).And(bsi.lt(bsi_thresh))
    bare = bsi.gte(bsi_thresh).And(ndvi.lt(0.15))

    label = (ee.Image(0)
             .where(braidplain.And(bare), 2)
             .where(braidplain.And(veg), 3)
             .where(braidplain.And(water), 1)
             .rename('label').toByte())
    return label


# ─────────────────────────────────────────────────────────────────────────────
# 3. Tile grid over the braidplain
# ─────────────────────────────────────────────────────────────────────────────
def tile_grid(aoi, tile_m, crs):
    b = aoi.bounds(1, crs).coordinates().get(0).getInfo()
    xs, ys = [c[0] for c in b], [c[1] for c in b]
    tiles, x = [], min(xs)
    while x < max(xs):
        y = min(ys)
        while y < max(ys):
            tiles.append(ee.Geometry.Rectangle(
                [x, y, x + tile_m, y + tile_m], proj=crs, geodesic=False))
            y += tile_m          # no overlap: overlapping tiles cause split leakage
        x += tile_m
    return tiles


# ─────────────────────────────────────────────────────────────────────────────
# 4. Characterise each tile so selection can be deliberate
# ─────────────────────────────────────────────────────────────────────────────
def profile_tiles(tiles, label, braidplain):
    """For each tile, compute class fractions and braidplain coverage."""
    rows = []
    for i, geom in enumerate(tqdm(tiles, desc='Profiling tiles')):
        try:
            hist = label.reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(), geometry=geom,
                scale=30, bestEffort=True, maxPixels=1e9).getInfo().get('label', {})
            total = sum(hist.values()) or 1
            bp = braidplain.reduceRegion(
                reducer=ee.Reducer.mean(), geometry=geom,
                scale=30, bestEffort=True, maxPixels=1e9).values().get(0).getInfo() or 0

            rows.append({
                'idx': i,
                'bp_frac':   bp,
                'f_water':   hist.get('1', 0) / total,
                'f_bare':    hist.get('2', 0) / total,
                'f_veg':     hist.get('3', 0) / total,
            })
        except Exception as e:
            print(f'  tile {i} failed: {e}')
    return pd.DataFrame(rows)


def select_pilot(df, n_per_stratum=2):
    """Pick tiles spanning the conditions that make annotation hard.

    Strata:
      1. High vegetation      — tests the bare/vegetated boundary
      2. Low vegetation       — mostly bare, tests wet sand and sparse cover
      3. High channel density — many threads, tests waterline and topology
      4. Braidplain edge      — partial coverage, tests the envelope boundary
      5. Mixed                — all three classes well represented
    """
    core = df[df.bp_frac > 0.5].copy()
    edge = df[(df.bp_frac > 0.15) & (df.bp_frac < 0.5)].copy()
    core['mix'] = core[['f_water', 'f_bare', 'f_veg']].min(axis=1)

    picks = {
        'high_veg':     core.nlargest(n_per_stratum, 'f_veg'),
        'low_veg':      core.nsmallest(n_per_stratum, 'f_veg'),
        'high_channel': core.nlargest(n_per_stratum, 'f_water'),
        'edge':         edge.nlargest(n_per_stratum, 'bp_frac'),
        'mixed':        core.nlargest(n_per_stratum, 'mix'),
    }
    out = []
    seen = set()
    for stratum, sub in picks.items():
        for _, r in sub.iterrows():
            if r.idx in seen:
                continue
            seen.add(r.idx)
            out.append({**r.to_dict(), 'stratum': stratum})
    return pd.DataFrame(out)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Export
# ─────────────────────────────────────────────────────────────────────────────
def export_tile(img, label, braidplain, geom, tile_id):
    tasks = []
    exports = {
        'rgb':         (img.select(['B4', 'B3', 'B2']), 'float'),
        'falsecolour': (img.select(['B8', 'B4', 'B3']), 'float'),
        'stack':       (img.select(S2_BANDS + S1_BANDS), 'float'),
        'braidplain':  (braidplain.toByte(), 'byte'),
        'weaklabel':   (label, 'byte'),
    }
    for suffix, (image, _) in exports.items():
        t = ee.batch.Export.image.toDrive(
            image=image.clip(geom), description=f'{tile_id}_{suffix}',
            folder=DRIVE_FOLDER, fileNamePrefix=f'{tile_id}_{suffix}',
            region=geom, scale=RESOLUTION, crs=CRS, maxPixels=1e9)
        t.start()
        tasks.append(t)
    return tasks


def run():
    print('Building composite...')
    img = build_composite(AOI, START, END)

    braidplain = ee.Image(BRAIDPLAIN_ASSET).select(0).eq(1)
    label = weak_label(img, braidplain)

    print('Generating tile grid...')
    tiles = tile_grid(AOI, TILE_M, CRS)
    print(f'  {len(tiles)} candidate tiles at {TILE_PX}px ({TILE_M/1000:.2f} km)')

    df = profile_tiles(tiles, label, braidplain)
    picks = select_pilot(df)
    print(f'\nSelected {len(picks)} pilot tiles:')
    print(picks[['idx', 'stratum', 'bp_frac', 'f_water', 'f_bare', 'f_veg']]
          .round(3).to_string(index=False))

    all_tasks = []
    for _, r in picks.iterrows():
        tid = f"pilot_{PILOT_YEAR}_{int(r.idx):04d}_{r.stratum}"
        all_tasks += export_tile(img, label, braidplain, tiles[int(r.idx)], tid)

    picks.to_csv('/content/pilot_manifest.csv', index=False)
    print(f'\n{len(all_tasks)} export tasks submitted. '
          f'Monitor in the GEE Tasks tab.')
    print('Manifest saved to /content/pilot_manifest.csv — '
          'copy it to Drive alongside the tiles.')
    return picks, all_tasks


if __name__ == '__main__':
    picks, tasks = run()
