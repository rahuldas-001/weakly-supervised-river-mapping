# Data

None of the data below are in this repository.

## Satellite data (public)

- Sentinel-2 L2A surface reflectance (`COPERNICUS/S2_SR_HARMONIZED`), bands B2, B3, B4,
  B8, B8A, B11, B12.
- Sentinel-1 GRD (`COPERNICUS/S1_GRD`), VV and VH, in dB.
- Lean-season composites, 1 February to 31 March, 10 m, EPSG:32646.
- Braidplain envelope: Earth Engine asset `projects/rahulds001/assets/braidplain_mask_v1`
  (28-year Landsat MNDWI union, manually corrected).

## Reaches

- Training: Rupai - Majuli (2024 and 2025 tiles).
- Inference and manual validation: Bhomoraguri - Pandu (2019-2026).

## Google Drive layout used by the notebooks (`MyDrive/BRAHMA_MORPHO/`)

| Path | Contents |
|---|---|
| `training/tiles/training/`, `training_2025/` | 3,286 tiles per year; `image.npy` (256, 256, 9) float32, channels last; `mask.npy` (256, 256, 1) uint8, classes 0-3 |
| `training/splits_spatial/` | `*_tiles_merged.json`: 882 / 86 / 126 tiles. Use these. |
| `training/splits/` | Old random split. Do not use. |
| `inference/scenes/` | `inference_YYYY_9band_merged.tif`, 11,574 x 7,163 px |
| `models/` | Checkpoints. `*_best_spatial*.pth` are the final models. |
| `predictions/` | `attention_unet_pred_YYYY_braidplain_spatial.tif` (final annual maps) |
| `CS/CS_seven.shp` | The 8 manual cross-sections (field `CS_id`) |

Channel order in tiles and scenes: B2, B3, B4, B8, B8A, B11, B12, VV, VH. Optical bands are
reflectance x 10,000; radar bands are dB.

Classes: 0 background, 1 water, 2 bare bar, 3 vegetated bar.

Known issue: `models/attention_unet/attention_unet_test_metrics.json` was overwritten by
the 6-band ablation run. The 9-band test metrics must be recomputed from
`attention_unet_best_spatial.pth` if needed.

## CWC gauge data (restricted)

Daily discharge and hourly water level at Pandu and Bhomoraguri, 2001-2025, India-WRIS
export format. Brahmaputra basin data are classified under the hydro-meteorological data
policy. Raw values must not be published or committed; only analysis results may be
shared, with CWC credited.

- Water level codes: `HHS` = metres above MSL, `HZS` = metres above gauge zero.
- Pandu gauge zero = 39.00 m above MSL (from about 35,000 timestamps with both codes).
- Some values carry the wrong code; values below 20 m at Pandu are gauge-zero readings.
- Bhomoraguri stage and discharge in 2010-2011 look unreliable.
