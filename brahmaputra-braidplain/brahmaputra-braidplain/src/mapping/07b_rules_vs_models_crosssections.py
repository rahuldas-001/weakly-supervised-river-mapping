# =============================================================================
# 07b_rules_vs_models_crosssections.py
# Purpose : Compare the rules-only map with the three deep learning models,
#           all judged against the same 8 manual cross-sections (2019).
#           Question: does deep learning do better than the rules it was
#           trained on?
# Where   : VS Code or Colab. Needs crosssection_measure.py in the same folder
#           (or on the Python path).
# Inputs  : edit the PATHS block below.
# Output  : outputs/07_rules_vs_models.csv  (R2 and bias for every method)
# =============================================================================

# %% Cell 1 - Paths (edit these to your folders)
# The cross-section lines, the rules-only map from script 07a, and the three
# model predictions for 2019.
SECTIONS = 'data/CS/CS_seven.shp'
MAPS = {
    'Rules only':                'data/maps/rules_2019_mask.tif',
    'Attention U-Net, 9 bands':  'data/maps/attention_unet_pred_2019_braidplain_spatial.tif',
    'SegFormer-B2, 9 bands':     'data/maps/segformer_pred_2019_braidplain_spatial.tif',
    'Attention U-Net, 6 bands':  'data/maps/attention_unet_pred_2019_braidplain_spatial_ablation.tif',
}
OUT_CSV = 'outputs/07_rules_vs_models.csv'
MIN_PX = 10      # minimum feature width = 10 pixels = 100 m, same as in the paper

# %% Cell 2 - Imports
import os
import numpy as np
import pandas as pd
import rasterio
from crosssection_measure import measure_sections

# %% Cell 3 - Check that all maps share the same grid
# If the rules map was exported with a slightly different extent or pixel
# alignment, its cross-section readings would not be comparable.
# Every map should print the same width, height, pixel size and origin.
for name, path in MAPS.items():
    with rasterio.open(path) as r:
        print(f'{name:26s} {r.width} x {r.height}  pixel {r.res[0]:.0f} m  '
              f'origin ({r.transform.c:.1f}, {r.transform.f:.1f})  {r.crs}')
# Paste this printout back if any line differs from the others.

# %% Cell 4 - Manual measurements, 2019 (CS_01 to CS_08, in that order)
# These are the values used in the paper's validation figure.
# Check them against your own manual measurement file before trusting the result.
manual = pd.DataFrame({
    'section': [f'CS_0{i}' for i in range(1, 9)],
    'channel_width_km':  [1.32, 2.05, 2.98, 2.29, 1.89, 3.14, 3.30, 2.18],
    'bare_bar_width_km': [3.06, 6.21, 3.37, 5.76, 4.20, 5.29, 5.74, 2.71],
    'veg_bar_width_km':  [1.65, 1.47, 2.97, 2.09, 4.60, 5.66, 1.99, 4.52],
    'n_threads':         [3, 6, 8, 7, 4, 8, 5, 3],
    'n_bar_units':       [3, 7, 6, 8, 5, 8, 6, 4],
}).set_index('section')

# %% Cell 5 - Measure every map along the 8 cross-sections
# measure_sections() reads the class under each line and returns widths
# (km) and counts per section, exactly as for the models in the paper.
auto = {}
for name, path in MAPS.items():
    df = measure_sections(SECTIONS, path, id_field='CS_id', min_px=MIN_PX)
    # The script returns sections indexed by their CS_id. If the ids are plain
    # numbers (1, 2, ...), turn them into 'CS_01', 'CS_02', ... to match the manual table.
    df.index = [i if str(i).startswith('CS_') else f'CS_{int(float(i)):02d}' for i in df.index]
    auto[name] = df
    print(f'\n{name}\n', auto[name][list(manual.columns)].round(2).to_string())

# %% Cell 6 - Agreement with the manual measurements
# R2   = how well the method follows the section-to-section pattern (1 = perfect)
# bias = average difference, method minus manual (0 = no systematic error)
# Sections are matched by their CS_id, not by row order.
rows = []
for name, df in auto.items():
    for col in manual.columns:
        m = manual[col]
        a = df[col].reindex(m.index)
        ok = a.notna() & m.notna()
        r = np.corrcoef(m[ok], a[ok])[0, 1] if ok.sum() > 2 else np.nan
        rows.append({'method': name, 'measure': col,
                     'R2': round(r ** 2, 3),
                     'bias': round((a[ok] - m[ok]).mean(), 2),
                     'n_sections': int(ok.sum())})
result = pd.DataFrame(rows)

# %% Cell 7 - Show and save the comparison
# One row per measure, one column per method, for R2 and for bias.
print('\nR2 against manual (higher is better)')
print(result.pivot(index='measure', columns='method', values='R2').to_string())
print('\nBias against manual (closer to 0 is better)')
print(result.pivot(index='measure', columns='method', values='bias').to_string())

os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
result.to_csv(OUT_CSV, index=False)
print(f'\nSaved {OUT_CSV}. Paste the two tables back here.')
