"""
Data inventory for the data manual.

Run in Colab after mounting Drive. It does not change any file.
It writes data_inventory.txt into BASE. Send that file back.
"""

import os, json, glob
import numpy as np

BASE = '/content/drive/MyDrive/BRAHMA_MORPHO'      # edit if different
OUT  = os.path.join(BASE, 'data_inventory.txt')
lines = []
def p(*a):
    s = ' '.join(str(x) for x in a); print(s); lines.append(s)

# 1. Folder tree (3 levels), with file counts, skipping individual tile folders
p('=== FOLDER TREE ===')
for root, dirs, files in os.walk(BASE):
    depth = root[len(BASE):].count(os.sep)
    if depth > 3:
        continue
    name = os.path.basename(root)
    if 'tile_' in name:            # do not list thousands of tile folders
        dirs[:] = []
        continue
    n_tiles = sum(1 for d in dirs if 'tile_' in d)
    exts = {}
    for f in files:
        e = os.path.splitext(f)[1].lower() or '(none)'
        exts[e] = exts.get(e, 0) + 1
    size_mb = sum(os.path.getsize(os.path.join(root, f)) for f in files) / 1e6
    p('  ' * depth + f'{name}/  files={len(files)} {exts}  tile_dirs={n_tiles}  {size_mb:.0f} MB')

# 2. One tile from each tile folder: files, shapes, dtypes, value ranges
p('\n=== SAMPLE TILES ===')
tile_parents = sorted({os.path.dirname(d) for d in glob.glob(os.path.join(BASE, '**', '*tile_*'),
                                                               recursive=True) if os.path.isdir(d)})
for parent in tile_parents:
    tdirs = sorted(d for d in os.listdir(parent) if 'tile_' in d)
    p(f'\n{parent}  ({len(tdirs)} tiles)  first={tdirs[0]}  last={tdirs[-1]}')
    t = os.path.join(parent, tdirs[0])
    for f in sorted(os.listdir(t)):
        fp = os.path.join(t, f)
        if f.endswith('.npy'):
            a = np.load(fp)
            p(f'   {f}: shape={a.shape} dtype={a.dtype}')
            if a.ndim == 3:
                for b in range(a.shape[0]):
                    x = a[b][np.isfinite(a[b])]
                    p(f'      band {b}: min={x.min():.4f} max={x.max():.4f} mean={x.mean():.4f} nan={np.isnan(a[b]).sum()}')
            else:
                u, c = np.unique(a, return_counts=True)
                p(f'      values: {dict(zip(u.tolist(), c.tolist()))}')
        elif f.endswith('.json'):
            p(f'   {f}: {open(fp).read()[:300]}')
        else:
            p(f'   {f}')

# 3. JSON files outside tiles (splits, norm stats, manifests)
p('\n=== JSON FILES ===')
for fp in sorted(glob.glob(os.path.join(BASE, '**', '*.json'), recursive=True)):
    if 'tile_' in fp:
        continue
    try:
        d = json.load(open(fp))
        if isinstance(d, list):
            p(f'{fp}: list of {len(d)}, e.g. {d[:3]}')
        elif isinstance(d, dict):
            p(f'{fp}: keys={list(d)[:15]}')
            for k in list(d)[:15]:
                v = d[k]
                if isinstance(v, (list, int, float, str)) and len(str(v)) < 200:
                    p(f'      {k}: {v}')
    except Exception as e:
        p(f'{fp}: could not read ({e})')

# 4. Rasters and shapefiles
p('\n=== RASTERS ===')
try:
    import rasterio
    for fp in sorted(glob.glob(os.path.join(BASE, '**', '*.tif'), recursive=True)):
        with rasterio.open(fp) as s:
            p(f'{os.path.relpath(fp, BASE)}: bands={s.count} {s.width}x{s.height} '
              f'res={s.res[0]:.0f} crs={s.crs} dtype={s.dtypes[0]} nodata={s.nodata} '
              f'desc={s.descriptions}')
except ImportError:
    p('rasterio not installed: pip install rasterio')

p('\n=== SHAPEFILES ===')
try:
    import geopandas as gpd
    for fp in sorted(glob.glob(os.path.join(BASE, '**', '*.shp'), recursive=True)):
        g = gpd.read_file(fp)
        p(f'{os.path.relpath(fp, BASE)}: {len(g)} features, crs={g.crs}, fields={list(g.columns)}')
except ImportError:
    p('geopandas not installed')

# 5. Model checkpoints and notebooks
p('\n=== CHECKPOINTS AND NOTEBOOKS ===')
for pat in ('*.pth', '*.pt', '*.ckpt', '*.ipynb', '*.py', '*.csv'):
    for fp in sorted(glob.glob(os.path.join(BASE, '**', pat), recursive=True)):
        if 'tile_' in fp:
            continue
        p(f'{os.path.relpath(fp, BASE)}  {os.path.getsize(fp)/1e6:.1f} MB')

open(OUT, 'w').write('\n'.join(lines))
print(f'\nWritten {OUT}')
