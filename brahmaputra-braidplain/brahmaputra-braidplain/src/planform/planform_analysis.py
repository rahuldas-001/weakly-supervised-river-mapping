"""
Planform change analysis from the annual Attention U-Net maps (spatially split model).

Input : attention_unet_pred_{year}_braidplain_spatial.tif, 2019-2026
        classes 0 background, 1 water, 2 bare bar, 3 vegetated bar
Output: CSV tables and GeoTIFFs in OUT_DIR

What it computes
  1. Annual class areas (replaces the old annual_morphometrics.csv)
  2. Year-to-year class transitions (gross exchange between classes)
  3. Persistence over the record: how many years each pixel was water,
     bare bar or vegetated bar, and how often it changed class
  4. Along-reach profiles in fixed easting bins
  5. A noise check: one-year "flicker" (A -> B -> A)

Transitions are computed twice, on the raw maps and on maps with small
patches removed (sieve), so you can see how much of the change is pixel noise.

Run in Colab after mounting Drive. Edit the paths below.
"""

import os
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import sieve

# ── Settings ─────────────────────────────────────────────────────────────
PRED_DIR   = '/content/drive/MyDrive/BRAHMA_MORPHO/inference'     # edit
PATTERN    = 'attention_unet_pred_{year}_braidplain_spatial.tif'
YEARS      = list(range(2019, 2027))
OUT_DIR    = os.path.join(PRED_DIR, 'planform_analysis')

SIEVE_PX   = 10       # patches smaller than this many pixels are merged into neighbours
BIN_KM     = 2.0      # width of along-reach bins
STABLE_MIN = 7        # a pixel is "stable" if it holds one class in >= this many years

CLASSES = {1: 'water', 2: 'bare', 3: 'veg'}
os.makedirs(OUT_DIR, exist_ok=True)


# ── 1. Load and check the stack ──────────────────────────────────────────
stack, profile, transform = [], None, None
for y in YEARS:
    path = os.path.join(PRED_DIR, PATTERN.format(year=y))
    with rasterio.open(path) as src:
        a = src.read(1).astype(np.uint8)
        if profile is None:
            profile, transform, shape = src.profile, src.transform, a.shape
        elif a.shape != shape or src.transform != transform:
            raise ValueError(f'{y}: grid differs from {YEARS[0]}. Resample first.')
    stack.append(a)
stack = np.stack(stack)                       # (n_years, H, W)
n_years = len(YEARS)

px_km2 = abs(transform.a * transform.e) / 1e6
print(f'Grid {shape}, pixel {abs(transform.a):.0f} m, {n_years} years')

# Envelope: classified (non-zero) in every year. Report any mismatch.
env_any = (stack > 0).any(0)
env     = (stack > 0).all(0)
print(f'Envelope area (all years) : {env.sum() * px_km2:8.2f} km2')
print(f'Pixels classified in some years only: {(env_any & ~env).sum() * px_km2:.2f} km2 '
      f'(should be ~0 if the envelope is fixed)')

# Sieved copy
stack_sv = np.stack([sieve(s, size=SIEVE_PX, connectivity=8) for s in stack])
stack_sv[:, ~env] = 0


# ── 2. Annual areas ──────────────────────────────────────────────────────
rows = []
for i, y in enumerate(YEARS):
    s = stack[i][env]
    r = {'year': y}
    for c, name in CLASSES.items():
        r[f'{name}_km2'] = (s == c).sum() * px_km2
    r['envelope_km2'] = env.sum() * px_km2
    bar = r['bare_km2'] + r['veg_km2']
    r['veg_share_of_bar'] = r['veg_km2'] / bar if bar else np.nan
    rows.append(r)
areas = pd.DataFrame(rows).round(3)
areas.to_csv(os.path.join(OUT_DIR, 'annual_areas_spatial.csv'), index=False)
print('\nAnnual areas (km2)\n', areas.to_string(index=False))


# ── 3. Transitions ───────────────────────────────────────────────────────
def transitions(a, b):
    """3x3 matrix in km2, rows = from class, cols = to class (1..3)."""
    v = env & (a > 0) & (b > 0)
    code = (a[v].astype(int) - 1) * 3 + (b[v].astype(int) - 1)
    return np.bincount(code, minlength=9).reshape(3, 3) * px_km2

trans_rows = []
for label, stk in (('raw', stack), ('sieved', stack_sv)):
    pairs = [(i, i + 1) for i in range(n_years - 1)] + [(0, n_years - 1)]
    for i, j in pairs:
        m = transitions(stk[i], stk[j])
        for fi, fname in enumerate(CLASSES.values()):
            for ti, tname in enumerate(CLASSES.values()):
                trans_rows.append({'maps': label, 'from_year': YEARS[i], 'to_year': YEARS[j],
                                   'from': fname, 'to': tname, 'km2': m[fi, ti]})
trans = pd.DataFrame(trans_rows).round(3)
trans.to_csv(os.path.join(OUT_DIR, 'transitions.csv'), index=False)

# Gross vs net change per year pair
summ = []
for (label, fy, ty), g in trans.groupby(['maps', 'from_year', 'to_year']):
    changed = g.loc[g['from'] != g['to'], 'km2'].sum()
    total = g['km2'].sum()
    get = lambda f, t: g.loc[(g['from'] == f) & (g['to'] == t), 'km2'].iat[0]
    veg_net = (g.loc[g['to'] == 'veg', 'km2'].sum() - g.loc[g['from'] == 'veg', 'km2'].sum())
    summ.append({'maps': label, 'from_year': fy, 'to_year': ty,
                 'changed_km2': changed, 'changed_frac': changed / total,
                 'veg_to_water_km2': get('veg', 'water'),      # vegetated bar eroded
                 'bare_to_veg_km2': get('bare', 'veg'),         # vegetation established
                 'veg_to_bare_km2': get('veg', 'bare'),         # vegetation lost on bar
                 'water_to_veg_km2': get('water', 'veg'),
                 'veg_net_km2': veg_net})
summ = pd.DataFrame(summ).round(3)
summ.to_csv(os.path.join(OUT_DIR, 'transition_summary.csv'), index=False)
print('\nTransition summary\n', summ.to_string(index=False))


# ── 4. Persistence over the record ───────────────────────────────────────
def write(name, arr, nodata=255):
    p = profile.copy()
    p.update(dtype='uint8', count=1, nodata=nodata, compress='lzw')
    out = arr.astype(np.uint8)
    out[~env] = nodata
    with rasterio.open(os.path.join(OUT_DIR, name), 'w', **p) as dst:
        dst.write(out, 1)

freq = {name: (stack_sv == c).sum(0) for c, name in CLASSES.items()}
n_changes = (stack_sv[1:] != stack_sv[:-1]).sum(0)

# 1 stable water, 2 stable bare, 3 stable veg, 4 active
persist = np.full(shape, 4, np.uint8)
for c, name in CLASSES.items():
    persist[freq[name] >= STABLE_MIN] = c

for name in CLASSES.values():
    write(f'{name}_frequency.tif', freq[name])
write('n_changes.tif', n_changes)
write('persistence.tif', persist)

labels = {1: 'stable water', 2: 'stable bare bar', 3: 'stable vegetated bar', 4: 'active'}
pers = pd.DataFrame([{'category': labels[k], 'km2': (persist[env] == k).sum() * px_km2}
                     for k in labels])
pers['frac'] = pers['km2'] / pers['km2'].sum()
pers.round(3).to_csv(os.path.join(OUT_DIR, 'persistence_summary.csv'), index=False)
print(f'\nPersistence (stable = same class in >= {STABLE_MIN} of {n_years} years)\n',
      pers.round(3).to_string(index=False))


# ── 5. Along-reach bins ──────────────────────────────────────────────────
# Distance is measured along easting from the upstream (eastern) end.
# This approximates along-channel distance for a roughly east-west reach.
xs = transform.c + (np.arange(shape[1]) + 0.5) * transform.a
dist_km = (xs.max() - xs) / 1000.0
bin_idx = (dist_km // BIN_KM).astype(int)
nb = bin_idx.max() + 1

def per_bin(mask2d):
    return np.bincount(bin_idx, weights=mask2d.sum(0), minlength=nb) * px_km2

env_bin = per_bin(env)
bins = []
for i, y in enumerate(YEARS):
    for c, name in CLASSES.items():
        a = per_bin(env & (stack_sv[i] == c))
        for b in range(nb):
            bins.append({'year': y, 'bin_start_km': b * BIN_KM, 'class': name,
                         'km2': a[b], 'envelope_km2': env_bin[b]})
bins = pd.DataFrame(bins)
bins['frac'] = bins['km2'] / bins['envelope_km2'].replace(0, np.nan)
bins.round(4).to_csv(os.path.join(OUT_DIR, 'along_reach_bins.csv'), index=False)

act_bin = per_bin(env & (persist == 4))
mchg = np.bincount(bin_idx, weights=np.where(env, n_changes, 0).sum(0), minlength=nb)
reach = pd.DataFrame({'bin_start_km': np.arange(nb) * BIN_KM,
                      'envelope_km2': env_bin,
                      'active_frac': act_bin / np.where(env_bin > 0, env_bin, np.nan),
                      'mean_changes': mchg * px_km2 / np.where(env_bin > 0, env_bin, np.nan)})
reach.round(4).to_csv(os.path.join(OUT_DIR, 'along_reach_activity.csv'), index=False)


# ── 6. Noise check: one-year flicker ─────────────────────────────────────
# A pixel flickers in year i if it is A in i-1, B in i, and A again in i+1.
# Real morphological change rarely reverses in one year, so a high flicker
# share means much of the apparent change is classification noise
# (or a stage difference in that year's image).
fl = []
for label, stk in (('raw', stack), ('sieved', stack_sv)):
    for i in range(1, n_years - 1):
        f = env & (stk[i - 1] == stk[i + 1]) & (stk[i] != stk[i - 1])
        ch = env & (stk[i] != stk[i - 1])
        fl.append({'maps': label, 'year': YEARS[i],
                   'flicker_km2': f.sum() * px_km2,
                   'changed_from_prev_km2': ch.sum() * px_km2,
                   'flicker_share_of_change': f.sum() / max(ch.sum(), 1)})
fl = pd.DataFrame(fl).round(3)
fl.to_csv(os.path.join(OUT_DIR, 'flicker_check.csv'), index=False)
print('\nOne-year flicker\n', fl.to_string(index=False))

print(f'\nAll outputs written to {OUT_DIR}')
