# Independent re-analysis of Brahmaputra flood–morphology dataset

Analyst: Claude (session of 15 Aug 2026). All numbers below recomputed from the
uploaded raw files (`annual_morphometrics.csv`, `flood_metrics_enhanced.csv`,
`spatiotemporal_morphometrics.csv`, `MIM.xlsx`, `Discharge_2001_2025.xlsx`).
This is a working document, not manuscript text. The author must verify every
item independently before use.

## 1. What reproduces

- CMI 2021 = 1.276, CMI 2026 = 0.971. MBVI 2021 = 0.620, MBVI 2026 = 0.989. Match.
- IRTC trend: slope −0.0765/yr, r = −0.768, p = 0.026. Matches report.
- MBVI trend: r² = 0.584, p = 0.027. Matches.
- Cross-section validation: Attention U-Net mean R² = 0.953 (report says 0.958;
  small rounding/aggregation difference, same conclusion). SegFormer mean
  R² = 0.712 (report: 0.710). SegFormer's failure is concentrated in thread and
  bar-unit counts (R² 0.36, 0.34); width variables are close between models.
- Vegetated bar area gain 2021→2026 = 103.65 km². Matches.
- S06 attenuation(2018–23) → veg_of_bar(2021–26): Spearman ρ = 1.000 confirmed
  as computed (identical rank orders). See §3 for why this is not evidence.

## 2. Flood metrics — RESOLVED, fully reproduced

An earlier version of this document reported a failure to reproduce the flood
metrics. That was an analyst error: the bankfull thresholds were taken from the
report text rather than from the notebook. Corrected below.

**The flood metric pipeline reproduces exactly.** Recomputing from the raw
discharge workbook using the thresholds actually used in SCRIPT4
(Q_bkf/Q̄ = 1.475 Bhomoraguri, 1.621 Pandu; Q̄ = 2001–2025 daily mean;
May–October season; QC bounds 100–55,000 Bhomo / 100–72,000 Pandu; linear
interpolation) gives:

- dur_bhomo, dur_pandu: exact match, all 8 years.
- excess_bhomo, excess_pandu: mean absolute difference 0.04 and 0.02
  (Q/Q̄-days), r = 1.0000. Residual is the 1.3% Q̄ difference from minor QC
  handling.
- RIFW, IRTC, EHE_bhomo: match to printed precision, all 8 years.

**However, the Methods text in three drafts states the thresholds incorrectly.**
Both the multi-scale report and Brahmaputra_Flood_Morphology_Report_2025 print
"Q_bkf/Q̄ = 1.65 at Bhomoraguri and Q_bkf/Q̄ = 1.40 at Pandu". The values
actually used were 1.475 and 1.621. The two numbers are wrong and the
station assignment is inverted.

Consequence: the 2025 report justifies the printed ordering physically — "The
lower threshold at Pandu reflects the wider, lower-gradient channel at Guwahati
where overbank flow initiates at a smaller multiple of the mean." Pandu's
threshold is in fact the *higher* of the two. This paragraph argues for an
ordering that the analysis did not use and must be rewritten, not just
renumbered.

Correct Methods values, from SCRIPT4 outputs:

| Station | Segmented rating | Wolman–Miller | Adopted |
|---|---|---|---|
| Bhomoraguri | 1.475 | 1.452 | **1.475** |
| Pandu | 1.621 | 1.671 | **1.621** |

The drafts' claim that the two methods converge is correct and well supported
(agreement within 0.023 and 0.050 respectively). Only the numbers are wrong.

- **S10 "38% of vegetated bar gain".** Recomputed share = 27.0%
  (27.9 of 103.3 km²). The 38% figure in report §5.1.2 and Discussion §5.4.2
  is wrong.

## 3. Statistical verdict on the correlation analysis

Full grid recomputed: 17 flood vars × 10 morph vars × 3 lags = 510 reach-level
tests (n = 6–8 each).

- Raw p < 0.05 (Pearson): 50 of 510. Expected under global null ≈ 26.
  Tests are strongly inter-correlated, so this ~2× enrichment suggests some
  real signal exists but is weak evidence for any specific pair.
- **Benjamini–Hochberg FDR 5% across the full grid: ZERO tests survive**
  (Pearson and Spearman alike).
- A small pre-specified confirmatory family of 4 lag-1 hypotheses
  (excess_pandu→bare_bar, EHE_pandu→bare_bar, excess_pandu→veg_bar_area,
  IRTC→veg_of_bar) survives BH-FDR within-family, 4 of 4.

Robustness of headline claims (drop-2020 leverage test; exclusion of
QC-flagged flood years 2018 & 2025; first differences):

| Claim | Full data | Drop 2020 | Drop QC-flagged | First diff | Verdict |
|---|---|---|---|---|---|
| L1 excess_pandu→bare_bar | r+0.93 p.001 | r+0.67 p.10 | r+0.91 p.011 | r+0.90 p.006 | SURVIVES (diff-robust; 2020-leveraged in raw) |
| L1 EHE_pandu→bare_bar | r+0.91 p.002 | r+0.56 p.19 | r+0.89 p.016 | r+0.89 p.006, ρ+0.86 | SURVIVES (same caveat) |
| L1 excess_pandu→veg_bar_area | r−0.78 p.023 | r−0.80 p.030 | r−0.77 p.071 | r−0.79 p.034, ρ−0.89 | SURVIVES — most robust result in dataset |
| L1 IRTC→veg_of_bar | r−0.88 p.004 | r−0.76 p.047 | r−0.88 p.021 | r−0.83 p.020 | SURVIVES |
| L2 IRTC→veg_of_bar | r−0.77 p.042 | r−0.85 p.030 | r−0.77 p.072 | r−0.19 p.72 (sign flips in ρ) | FAILS — trend artefact |
| L3 atten→veg_of_bar | r+0.94 p.005 | r+0.97 p.007 | r+0.87 p.056 | r+0.63 p.26; detrended r+0.51 p.30 | FAILS — trend-on-trend |
| L3 atten→MBVI | r+0.90 p.015 | r+0.89 p.045 | r+0.88 p.047 | r+0.55 p.33; detrended r+0.43 p.39 | FAILS — trend-on-trend |
| L3 RIFW→channel_area | r−0.85 p.031 | r−0.72 p.17 | r−0.87 p.053 | r−0.75 p.15 | FAILS robustness |

Trend diagnosis (why lag-2/3 collapse): attenuation_ratio has a near-perfect
secular trend (r = 0.927, p = 0.0009/yr) and veg_of_bar/MBVI trend upward;
any lag pairing of two trending series yields r ≈ 0.9 regardless of mechanism.

S06 ρ = 1.000: arithmetic verified, but (a) detrended r = 0.75, p = 0.085;
(b) exact permutation p for ρ = 1 at n = 6 is 0.0028, and across the ~2,500
segment-level test family ~7 such "perfect" results are expected by chance.
Do not present as a finding.

Implication for the lag-1 survivors: the honest claim is a ONE-tier lag
relationship (monsoon flood energy at the integrated downstream gauge →
next-lean-season bare-bar expansion and vegetated-bar loss), stated as
exploratory (n = 8, 2 flood years QC-flagged) and robust to first differencing.
The "three-tier lag structure" is not supported by this record.

## 4. Untouched by all of the above

The 2021 tri-index sign reversal is now **independently verified from the raw
discharge record**: RIFW −21.17→+5.33, IRTC +0.051→−0.291, attenuation ratio
−0.052→+0.140, with all three indices holding the post-shift sign for every
year 2021–2025 (confirmed programmatically). This is a descriptive observation
requiring no inferential statistics and it is the strongest result in the
study. Note the drafts write RIFW 2021 as +5.34; the CSV and recomputation
both give +5.33.

## 5. Validation scope (for Methods/Limitations)

- Cross-section validation uses the 2025 prediction only (per SCRIPT3 paths),
  n = 7 sections, one year, adjacent to the 2024/2025 training years.
  Temporal transferability to 2019–2023 is untested. State as limitation.
- Dice/mIoU are agreement with spectral-index weak labels, not ground truth.
- 2018 flood metrics: PANDU_DATA_UNCERTAIN flag. 2025: PANDU_OCT_GAP,
  Bhomo/Pandu peaks from different events, 82.6% coverage. Sensitivity
  analysis excluding these years belongs in the paper (done above; lag-1
  survivors hold at n = 6 except veg_bar_area at p = 0.071).

## 6. Open items for the author (do not skip)

1. ~~Reconcile flood-metric generation~~ — DONE, see §2. Pipeline verified.
   Remaining action: correct the bankfull thresholds in Methods (1.475 / 1.621,
   not 1.65 / 1.40) and rewrite the physical justification paragraph, which
   currently argues for the inverted ordering.
2. Correct 38% → 27% (S10), RIFW 2021 +5.34 → +5.33, and the items from the
   earlier inconsistency list:
   reach length 175 vs 131 km; three vs four classes; S14 r −0.867 vs −0.781;
   S06 p = 0.003 vs p < 0.001; "0.37 units" vs 0.424; IRTC 2018 "−0.12" vs
   −0.280; unlabelled Pearson/Spearman p-values; missing attenuation rows in
   Table 4; missing EHE_pandu column in Table 3.
3. Every reference verified against Crossref/publisher records before
   submission. Bibliography in APGARS_Paper.docx has extraction damage
   (refs 1, 3, 10). UNVERIFIED as of this session: Bertoldi 2010 & 2011,
   Gurnell 2014, Gurnell et al. 2001, Liébault & Piégay 2002, Tal & Paola 2007,
   Egozi & Ashmore 2008, and all ten APGARSS refs.
4. Decide: report lag analysis as pre-specified 4-hypothesis confirmatory set
   (survives FDR) + full grid in supplement with FDR disclosure — or drop to
   exploratory framing entirely.
