# =============================================================================
# 07a_export_rules_map_2019.py
# Purpose : Make a "rules-only" map of the inference reach for 2019.
#           It applies the SAME spectral rules that made the training labels
#           (build_label in Dataset_Preparation.ipynb) directly to the 2019 image,
#           with no deep learning involved.
# Where   : Run in Colab, at the END of Dataset_Preparation.ipynb, after all its
#           earlier cells have run (they define build_label, INFERENCE_AOI,
#           RESOLUTION and CRS, and initialise Earth Engine).
# Output  : rules_2019_mask.tif in Drive folder BRAHMA_MORPHO/inference/scenes
#           Values: 0 background, 1 water, 2 bare bar, 3 vegetated bar
# =============================================================================

# %% Cell 1 - Build the rules-only map for the 2019 lean season
# build_label() is the function that made the training labels.
# Here it runs on the inference reach (Bhomoraguri-Pandu) for Feb-Mar 2019,
# the same window and year as the manual cross-section measurements.
rules_layers = build_label(INFERENCE_AOI, '2019-02-01', '2019-03-31')
rules_mask = rules_layers['mask']          # the 4-class map (0-3)

# %% Cell 2 - Quick check: are all four classes present, and in sensible amounts?
# Counts pixels per class at 30 m (coarser than 10 m, only to make it fast).
hist = rules_mask.reduceRegion(
    reducer=ee.Reducer.frequencyHistogram(),
    geometry=INFERENCE_AOI,
    scale=30,
    bestEffort=True,
    maxPixels=1e10,
).getInfo().get('mask', {})

names = {'0': 'Background', '1': 'Water', '2': 'Bare bar', '3': 'Vegetated bar'}
total = sum(hist.values())
for k, name in names.items():
    n = hist.get(k, 0)
    print(f'{name:14s}: {100 * n / total:5.1f} %')
# Paste this printout back so we can check it before measuring.

# %% Cell 3 - Export the map to Google Drive
# Same region, resolution and projection as the model predictions,
# so the rules map lines up pixel for pixel with them.
task = ee.batch.Export.image.toDrive(
    image=rules_mask.toByte(),
    description='rules_2019_mask',
    folder='BRAHMA_MORPHO/inference/scenes',
    fileNamePrefix='rules_2019_mask',
    region=INFERENCE_AOI,
    scale=RESOLUTION,          # 10 m
    crs=CRS,                   # EPSG:32646
    maxPixels=1e13,
    fileFormat='GeoTIFF',
)
task.start()
print('Export started. Watch the Tasks tab in the Earth Engine Code Editor,')
print('or run task.status() in a new cell. It may take 15-45 minutes.')
