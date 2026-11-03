# Class definitions

Status: DRAFT. Every ambiguous case below needs a worked visual example before
annotation begins. This document is released with the dataset and is the primary
intellectual contribution of the benchmark.

## Classes

| ID | Name | Definition |
|----|------|-----------|
| 0 | background | Outside the braidplain envelope |
| 1 | water | Surface water at acquisition date (lean-season minimum) |
| 2 | bare_bar | Subaerial sediment within braidplain, unvegetated |
| 3 | vegetated_bar | Subaerial sediment within braidplain, vegetated |

## Resolved decisions

1. **Braidplain boundary** — historical envelope from 28 years of Landsat MNDWI
   (1988-2025), manually corrected. Asset: `braidplain_mask_v1`. Fixing the
   envelope makes class areas comparable across epochs.

2. **Island vs attached bar** — both class 3. Distinction recorded as a separate
   attribute. An island is surrounded by channel; a bar is attached.

3. **Char lands** — class 3, with a tile-level `cultivated` boolean. Not a fifth
   class: cultivated and natural vegetation are not reliably separable at 10 m
   and a fifth class would degrade inter-annotator agreement.

4. **Wet sand** — class 2 if subaerial. Waterline drawn at the visible edge of
   standing water.

5. **Sparse vegetation** — operational thresholds from the weak-label pipeline:
   bare bar requires NDVI < 0.15; vegetated bar requires MSAVI2 > 0.05.
   Manual annotation follows the same boundary, judged visually.
   TODO: example tiles at, above and below the boundary.

6. **Anthropogenic features** — separate mask layer, not a class. Covers
   embankments, spurs, bridge piers, sand mining.

7. **Shadow, thin cloud, haze** — separate `no_data` mask layer, not a class.

## Fallback rule

Braidplain pixels not resolved by the above are assigned by nearest index
neighbour in the weak-label pipeline. Manual annotators resolve them by
judgement and flag the tile for review.

## Outstanding

- Worked visual examples for cases 2, 4, 5
- Inter-annotator agreement target and measurement protocol
