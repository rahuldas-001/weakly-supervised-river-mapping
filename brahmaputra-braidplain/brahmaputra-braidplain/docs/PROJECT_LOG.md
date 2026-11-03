# Project log

A record of what was done and what was found. Numbers are as reported at the time.

## 1. Four-class mapping with weak labels

- Weak labels from spectral rules (MNDWI/VV Otsu for water; BSI percentile with NDVI and
  MSAVI2 for bare and vegetated bar) inside the braidplain envelope.
- Spatial block split. A random split had 79 % (103/130) of held-out tiles overlapping
  training tiles.
- Test tiles (weak labels), mean Dice / IoU / Boundary IoU:
  - Attention U-Net, 9 bands: 0.878 / 0.788 / 0.355 (vegetated bar Dice 0.775)
  - SegFormer-B2, 9 bands: 0.832 / 0.725 / 0.366 (vegetated bar Dice 0.654)
  - Attention U-Net, 6 bands: 0.846 / 0.744 / 0.383 (vegetated bar Dice 0.679)

## 2. Validation against 8 manual cross-sections (2019, Bhomoraguri - Pandu)

R2 against manual measurement (min feature width 100 m):

| Measure | Rules only | Att. U-Net 9 | SegFormer 9 | Att. U-Net 6 |
|---|---|---|---|---|
| Channel width | 0.900 | 0.993 | 0.905 | 0.967 |
| Bare bar width | 0.668 | 0.590 | 0.715 | 0.689 |
| Vegetated bar width | 0.894 | 0.777 | 0.631 | 0.920 |
| Thread count | 0.351 | 0.344 | 0.517 | 0.268 |
| Bar unit count | 0.523 | 0.469 | 0.612 | 0.696 |

Mean bias (method minus manual):

| Measure | Rules only | Att. U-Net 9 | SegFormer 9 | Att. U-Net 6 |
|---|---|---|---|---|
| Channel width (km) | -0.00 | +0.23 | +0.33 | +0.06 |
| Bare bar width (km) | -0.74 | +0.53 | +0.88 | -0.67 |
| Vegetated bar width (km) | +0.80 | -0.70 | -1.14 | +0.67 |
| Thread count | -1.25 | -0.62 | 0.00 | -1.00 |
| Bar unit count | +0.75 | +2.75 | +1.88 | +2.25 |

**Conclusion.** The deep learning models do not clearly outperform the spectral rules that
produced their training labels. The only clear gain is channel width R2 for the 9-band
Attention U-Net. The 6-band model and the rules make very similar errors. Eight sections
from one year is a small reference.

Weak-label scores and manual measurement ranked the models differently for vegetated bar.

## 3. Planform change, 2019-2026 (9-band Attention U-Net maps)

- Vegetated bar area fell from 227.7 km2 (2019) to 172.9 km2 (2021), then rose every year
  to 294.3 km2 (2026). Envelope 1,123.2 km2.
- 29-35 % of the envelope changes class each year; 33-39 % of that change reverses the
  next year.
- 77 % of reversals are water <-> bare bar, consistent with river stage at image time.
  21 % bare <-> vegetated, 3 % water <-> vegetated.
- Gross exchange between bar classes is several times the net change.
- Persistence (7 of 8 years): stable unvegetated 68.7 %, stable vegetated 9.7 %
  (108.4 km2), vegetation gained 9.8 %, lost 5.2 %, fluctuating 6.7 %.

Tables: `docs/results/`.

## 4. Mapping paper

- Submitted to Remote Sensing Applications: Society and Environment (RSASE-D-26-03699);
  desk-rejected on 3 November 2026 for lack of sufficient novelty.
- After the rules-vs-models check, the work was set aside.

## 5. Gauge analysis, Pandu and Bhomoraguri

- Daily discharge does not behave as a fixed function of stage: at the same stage
  (+-0.5 cm) within 15 days, discharge differs by a median 1.4 % (Pandu) and 2.2 %
  (Bhomoraguri), including in the steady dry season and when the rate of stage change is
  matched. Consistent with routine (near-daily) measurement; possibly mixed with computed
  days at Pandu. Not confirmed by CWC.
- **Pandu step around 2011-2012.** For the same high flow, stage rose by about 0.7-1.1 m
  (about 1 m at 20,000-30,000 m3/s; 0.2-0.35 m at low flow). The step is unchanged when
  possibly computed days are removed, and appears when Pandu stage is compared with the
  upstream Bhomoraguri discharge (1-day lag). Pandu/Bhomoraguri discharge ratio did not
  fall after 2012.
- Most likely cause: the New Saraighat Bridge (built beside the old bridge; piers visible
  in imagery by November 2013, absent October 2010; opened January 2017). Not confirmed.
- A datum change is unlikely to explain the main pattern (the step is flow-dependent and
  fades at low flow), but CWC's gauge-zero history would settle it.
- Bhomoraguri 2011 shows a one-year drop of 1.2-1.6 m at all flows: probably a data issue.

Figures: `figures/4_*`, `5_*`, `6_*`. Tables: `docs/results/`.

## 6. Earlier flood-morphology analysis

`docs/reanalysis_summary.md` and `figures/lag1_correlations.png` were computed on maps from
the superseded random-split model. They must be recomputed on the final maps before use.

## Lessons

- Compare against the simplest alternative (here, the labelling rules themselves) before
  writing a paper.
- Weak-label test scores alone are not enough to choose or justify a model.
- Year-to-year water area from optical composites is dominated by river stage.
