# Brahmaputra braidplain: mapping, planform change and gauge analysis

Research code and records for satellite-based mapping of the Brahmaputra braidplain
(Assam, India) and related analyses of planform change and gauge behaviour.
Author: Rahul Das, Hydro-Informatics Unit, Water Resources Department, Guwahati.

**Status (November 2026).** The mapping paper was desk-rejected for lack of novelty and
has been set aside. A later check showed that the deep learning models do not clearly
outperform the spectral rules used to train them (see `docs/PROJECT_LOG.md`). The code,
maps and findings are kept here for future work.

## What is in this repository

| Folder | Contents |
|---|---|
| `notebooks/` | Colab notebooks, in workflow order (outputs stripped) |
| `src/mapping/` | Spatial splitting, cross-section measurement, QC, rules-vs-models check |
| `src/planform/` | Year-to-year change, reversal (flicker) and persistence analysis |
| `src/gauge/` | Stage-discharge (rating) analysis for Pandu and Bhomoraguri |
| `src/figures/` | Figure scripts |
| `src/utils/` | Drive inventory and data-packaging helpers |
| `benchmark/` | Plans and skeleton code for a manually annotated benchmark (not started) |
| `docs/` | Project log, data notes, earlier re-analysis summary, result tables |
| `figures/` | Key figures |

## Workflow

1. `notebooks/01_dataset_preparation.ipynb` - Sentinel-1/2 lean-season composites in
   Google Earth Engine, weak labels from spectral rules, tiling, inference scenes.
2. `src/mapping/spatial_splits.py`, `cell25_spatial_splits.py`, `cell27_merge_2025.py` -
   spatial block train/validation/test split, 2025 tiles assigned by location.
3. `notebooks/02a_attention_unet.ipynb`, `02b_segformer.ipynb`,
   `02c_ablation_6band_attention_unet.ipynb` - model training, test metrics, inference.
4. `src/mapping/crosssection_measure.py` - widths and counts along manual cross-sections.
5. `src/planform/planform_analysis.py` - transitions, reversals, persistence (2019-2026).
6. `src/mapping/07a_*.py`, `07b_*.py` - rules-only map and comparison with the models.
7. `src/gauge/rating_analysis.py` - stage-discharge analysis at the CWC gauges.
8. `notebooks/03_*`, `04_*`, `05_*` - flood metrics and morphometrics (earlier work,
   computed on maps from the superseded random-split model).

## Data

No data are included. See `docs/DATA.md` for sources, the Google Drive layout used by
the notebooks, and restrictions on the CWC gauge data.

## Environment

Python 3.10 or newer. See `requirements.txt`. The notebooks were run in Google Colab with
Earth Engine access (`earthengine-api`, `geemap`).
