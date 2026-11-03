# Stage 1 Roadmap — Indian Braided River Benchmark Dataset

Working document. Target venue: Earth System Science Data (ESSD), fallback Scientific Data.
Prepared 19 Aug 2026. All tile arithmetic computed, not estimated from memory.
Annotation rate assumptions are estimates and must be recalibrated after Phase 3.

---

## The one-line pitch

A manually annotated, multi-class, multi-epoch benchmark for braided river geomorphic
units across Indian rivers, with published weak-label-versus-manual agreement statistics
and a temporal consistency evaluation protocol.

Three things make it defensible. No existing dataset separates bare bar from vegetated
bar. No existing dataset is multi-epoch with consistent annotation. No existing dataset
quantifies how much error automated spectral labelling introduces.

---

## Phase 0 — Class definition (do this first, alone, before anything else)

This is the contribution. Everything downstream inherits it. Budget two weeks and expect
to revise it after the pilot.

Deliverable: a class definition document with worked visual examples for every ambiguous
case. It goes in the paper as an appendix and in the repository as a PDF.

### The four base classes

| Class | Definition | Notes |
|---|---|---|
| 0 Background | Outside the braidplain envelope | Floodplain, terraces, built-up, tributaries beyond confluence |
| 1 Water | Surface water at the acquisition date | Lean-season extent, a low-flow minimum |
| 2 Bare bar | Subaerial sediment within the braidplain, unvegetated | Includes wet and dry sand |
| 3 Vegetated bar | Subaerial sediment within the braidplain, vegetated | Includes cultivated char surfaces |

### Ambiguous cases that must be resolved in writing

Each needs a rule and at least one annotated example image.

1. **Braidplain boundary.** The single hardest decision. Options: geomorphic (outer edge
   of demonstrably reworked surface), historical envelope (union of active area over a
   defined period), or embankment-bounded. Recommendation: historical envelope over a
   stated period, because it is reproducible and it fixes the denominator so that class
   areas across epochs are comparable. State the period explicitly.

2. **Vegetated bar versus island versus floodplain.** An island is a vegetated surface
   surrounded by channel; a vegetated bar is attached. Both are class 3 here, but record
   the distinction in a separate attribute if you can, because it matters geomorphically
   and someone will want it.

3. **Char lands.** Brahmaputra-specific and unavoidable. Inhabited and cultivated bars
   are common. Cultivated vegetation is spectrally similar to natural pioneer vegetation
   but geomorphically different — it implies stability and it is actively maintained.
   Recommendation: class 3, with a boolean `cultivated` attribute at the tile level.
   Do not create a fifth class; it will not be separable reliably and it will hurt
   inter-annotator agreement.

4. **Wet sand.** Saturated sediment near the waterline. Spectrally between water and bare
   bar. Rule must be explicit: recommend class 2 if subaerial, with the waterline drawn at
   the visible edge of standing water.

5. **Sparse vegetation.** Where does bare become vegetated? Recommend a stated cover
   threshold judged visually, with example tiles at, above and below it. Any threshold
   works; an undocumented threshold does not.

6. **Sand mining, embankments, spurs, bridge piers.** Anthropogenic features within the
   braidplain. Recommend a separate `anthropogenic` mask layer rather than a class, so
   users can include or exclude them.

7. **Shadow, thin cloud, haze.** Recommend a `no-data` mask layer, not a class.

### Decision gate 0

Do not proceed until a second person can annotate a tile from your document alone and
reach agreement with you. If they cannot, the document is not finished.

---

## Phase 1 — Reach and epoch selection

### Rivers

Four rivers, chosen to span braiding style and sediment calibre, not to maximise count.

| River | Reach | Rationale |
|---|---|---|
| Brahmaputra | Bhomoraguri–Pandu (131 km) + Rupai–Majuli | Anchor. Already mapped. Large sand-bed. |
| Kosi | Barahkshetra to confluence zone | Megafan, avulsive, distinct style |
| Teesta | Foothill reach | Gravel-to-sand transition |
| Gandak or Ghaghara | Foreland reach | Ganga-plain sand-bed, moderate braiding |

Avoid the Sutlej and Chenab for version one. Heavy regulation confounds the natural
braiding signal and invites a reviewer objection you cannot answer.

### Epochs

Five lean seasons, spaced to capture both the Landsat and Sentinel eras. The exact years
depend on cloud-free availability, which must be checked per reach before committing.

Recommended structure: two epochs in the Landsat-only era, one in the overlap, two in the
Sentinel era. This is what makes the cross-sensor consistency work possible later.

### Decision gate 1

Confirm cloud-free lean-season imagery exists for every river-epoch combination before
annotating anything. A missing epoch on one river breaks the temporal analysis.

---

## Phase 2 — Tiling and sampling

Tile size 512 × 512 pixels. At 10 m this is 5.12 × 5.12 km, 26.2 km² per tile.

Computed tile budget:

| River | Braidplain (km², est.) | Tiles per epoch |
|---|---|---|
| Brahmaputra | 1,123 (measured) | 51 |
| Kosi | ~700 | 32 |
| Ganga-plain | ~450 | 21 |
| Teesta | ~250 | 11 |
| **Total** | | **115 per epoch** |

Five epochs gives 577 tiles. Includes a 20% allowance for partial braidplain-edge tiles.

Splits must be **spatial, not random**. Assign whole sub-reaches to train, validation and
test, so that adjacent overlapping tiles cannot leak across the split. Random tile splits
in a braided river are a leakage failure and a reviewer will catch it.

Recommend also holding out **one entire river** as a cross-basin generalisation test. That
single design decision is worth more than a hundred extra tiles.

---

## Phase 3 — Pilot annotation

Annotate 20 tiles yourself. Then have a second annotator do the same 20 independently.

Measure Cohen's kappa per class and overall. Identify which classes disagree and why.
Revise the class document. Repeat until agreement is acceptable.

Recalibrate the time estimate here. Everything in Phase 4 depends on the real rate, not
the assumed one.

### Decision gate 2

If per-class kappa for the bare/vegetated distinction cannot be brought to an acceptable
level, the four-class scheme is not viable at 10 m and the project needs rethinking.
Better to find this out at 20 tiles than at 500.

---

## Phase 4 — Full annotation, tiered

A fully manual pass over 577 tiles is roughly 1.5 to 2.6 person-months at 20 to 35 minutes
per tile. Tractable but slow. A tiered scheme is standard practice and is faster without
sacrificing defensibility, provided it is documented.

**Gold tier — 15% of tiles, roughly 87.** Fully manual, no model assistance, annotated
independently by two people. This is the evaluation set and the basis for all reported
agreement statistics. Roughly 0.8 person-months including the duplicate pass.

**Silver tier — the remaining 490.** Model prediction as a starting point, manually
corrected. Roughly 0.5 person-months at 8 minutes per tile.

Total annotation effort: approximately 1.3 person-months. This is achievable alone; with
one assistant it is a term's work.

Critical rules for the tiered approach:

- Gold tiles are never seen by the model that assists silver annotation.
- Report gold and silver separately in the paper. Never pool them in evaluation.
- Annotate each site's full time series in one sitting, not epoch by epoch. Annotating by
  year risks your interpretation drifting across epochs, which would encode a false trend
  into the ground truth of a dataset whose purpose is measuring trends. This is the most
  dangerous failure mode in the whole project.

---

## Phase 5 — The weak-label audit

This is your differentiator and it costs almost nothing once the gold tier exists.

Run your existing spectral-index pipeline (MNDWI with Otsu, BSI 60th percentile, NDVI and
MSAVI2 thresholds) over the gold tiles. Compare against manual annotation.

Report, per class:

- Agreement, confusion matrix, per-class IoU
- Where weak labels systematically fail — expect boundary pixels, wet sand, sparse
  vegetation
- Whether the error is a constant offset or varies with planform complexity
- Whether the error varies across epochs, which would matter for time series work

Nobody has published this for fluvial mapping. It tells the field how much to trust the
large body of weakly supervised river work, including your own. It is a genuine service
contribution and it is the section reviewers will remember.

---

## Phase 6 — Scale sensitivity

Degrade the gold annotations from 10 m to 30 m by majority vote. Recompute class areas
and any derived metrics.

Report how much class information survives, per class, and specifically whether the bias
in channel area is constant or scales with planform complexity. This directly determines
whether Landsat-era work in Stage 3 is viable, and it answers a question the field
currently hand-waves.

Release both resolutions in the dataset.

---

## Phase 7 — Baselines

Provide at least two, ideally three:

- Your Attention U-Net
- SegFormer-B2, including the count-metric failure you already documented
- Optionally a temporally-aware model or an Earth observation foundation model

Report standard segmentation metrics, but also the two that make this benchmark different:

**Geometric metrics.** Channel width, bar width, thread count, bar unit count against
manually digitised cross-sections. Width metrics can look fine while the topology is
destroyed, which is exactly what your SegFormer comparison showed.

**Temporal consistency.** Score year-to-year class transitions for physical plausibility.
Water to vegetated bar in a single step, skipping bare bar, is implausible. Vegetated bar
to bare bar is plausible after a large flood. Define a transition matrix of allowed,
unlikely and implausible changes, and report the fraction of implausible transitions per
model. No published fluvial work reports this.

---

## Phase 8 — Packaging

ESSD requirements are strict and non-negotiable. Meet them exactly.

- Deposit on Zenodo with a functional DOI **before submission**
- Licence **CC BY 4.0**. Not NC, not SA, not ND. ESSD rejects restrictive licences.
- Community formats: Cloud-Optimised GeoTIFF for imagery and masks, with full CRS and
  geotransform. No proprietary formats.
- Croissant metadata file, which also makes it NeurIPS-ready later
- Per-tile metadata: river, reach, epoch, sensor, acquisition dates, tier, split
  assignment, cloud fraction, annotator ID
- Class definition document as a PDF
- Annotation protocol and QA log
- Code for tiling, weak-label generation, metrics, and baselines

---

## Phase 9 — Manuscript

ESSD structure is prescribed. Follow it.

1. Introduction — the gap, stated as "to our knowledge" since it is a negative claim
2. Study areas
3. Data sources and preprocessing
4. Class definitions — substantial, with visual examples
5. Annotation methodology — tiers, protocol, inter-annotator agreement
6. **Technical validation** — mandatory. Agreement statistics, weak-label audit, scale
   sensitivity, baseline results
7. Data records — file structure, formats, naming
8. Code availability
9. Usage notes — including honest limitations

ESSD is judged on uniqueness and reusability, not novelty or impact. Write accordingly.
Do not oversell. The dataset either fills a gap or it does not.

---

## Timeline

| Phase | Duration | Depends on |
|---|---|---|
| 0 Class definition | 2–3 weeks | Nothing. Start now. |
| 1 Reach and epoch selection | 2 weeks | Imagery availability check |
| 2 Tiling | 1 week | Phase 1 |
| 3 Pilot | 2 weeks | Phases 0–2, second annotator |
| 4 Full annotation | 2–3 months | Gate 2 passed |
| 5 Weak-label audit | 1 week | Gold tier complete |
| 6 Scale sensitivity | 1 week | Gold tier complete |
| 7 Baselines | 3–4 weeks | Full annotation complete |
| 8 Packaging | 2 weeks | Everything |
| 9 Manuscript | 4–6 weeks | Everything |

Roughly eight to ten months at part-time effort. Phases 5, 6 and 7 can overlap.

---

## Risks

**A competing dataset appears.** Watch Carbonneau's group at Durham and the RiverScope
team. If a multi-class multi-temporal braided benchmark is released, pivot to the Indian
and South Asian focus and the vegetated bar class, both of which remain defensible.

**Inter-annotator agreement fails on bare versus vegetated.** Caught at gate 2. Mitigation
is a stricter cover threshold or, in the worst case, merging to three classes and
reframing around the temporal dimension instead.

**Annotation drift across epochs.** Mitigated by annotating full time series per site in
one sitting. This is the risk most likely to quietly ruin the dataset.

**Effort underestimated.** The rates here are assumptions. Phase 3 exists to replace them
with measurements. Revise the plan at that point rather than pushing through.

---

## What to do this week

1. Start the class definition document. Nothing else can begin without it.
2. Check lean-season imagery availability for Kosi, Teesta and your fourth river.
3. Identify a second annotator. Without one there is no agreement statistic, and without
   that the dataset is not a benchmark.

---

## Open items requiring verification

- All venue requirements above (ESSD licensing, repository, Croissant) come from a
  research summary and are **UNVERIFIED against the current author guidelines**. Check
  the ESSD site directly before building to these specifications.
- Braidplain area estimates for Kosi, Teesta and the Ganga-plain river are placeholders.
  Measure them before finalising the tile budget.
- The claim that no comparable benchmark exists is a negative based on search. State it
  as "to our knowledge" in any publication.
