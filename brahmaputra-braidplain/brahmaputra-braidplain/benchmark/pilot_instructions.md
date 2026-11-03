# Pilot annotation — what to do

Ten tiles. Aim to finish in one or two sittings so your judgement stays consistent.

---

## 1. Generate the tiles

Open a new Colab notebook. Paste in `make_pilot_tiles.py`. Check the settings at
the top, especially `EE_PROJECT` and `BRAIDPLAIN_ASSET`.

Run it. It profiles every tile in the reach, picks ten spanning the hard cases,
and submits export tasks. Watch the GEE Tasks tab; exports take a while.

The script has not been tested against Earth Engine from my side. Expect to fix
one or two things on the first run, most likely band names on the braidplain
asset.

### Why these ten and not ten random ones

Random tiles would mostly be moderate cases and would teach you little. The
script picks two tiles from each of five strata:

| Stratum | What it tests |
|---|---|
| high vegetation | the bare/vegetated boundary, your hardest rule |
| low vegetation | wet sand, sparse cover |
| high channel density | waterline placement, thread topology |
| braidplain edge | the envelope boundary |
| mixed | all three classes present together |

---

## 2. Set up QGIS

Load per tile:

1. `_rgb.tif` — true colour, digitise against this
2. `_falsecolour.tif` — NIR false colour, vegetation is obvious here
3. `_braidplain.tif` — the envelope, set to outline only
4. `_weaklabel.tif` — **switch this OFF and leave it off**

Load `braidbench_classes.qml` onto any label layer for consistent colours.

### The rule about the weak label

Do not look at it while annotating. If you can see what the rules decided, you
will unconsciously agree with them, and the comparison afterwards becomes
meaningless.

Annotate blind. Then turn it on and compare. The disagreements are the whole
point of the pilot.

---

## 3. Annotate

Create a polygon layer with an integer `class` field. Values 0, 1, 2, 3, and
255 for uncertain.

Suggested order per tile:

1. Water first — clearest boundaries, sets your reference
2. Vegetated bar — use the false colour layer
3. Bare bar — by elimination within the braidplain
4. Anything you cannot decide — 255, and move on

Do not agonise. If a call takes more than about thirty seconds, mark it 255,
screenshot it, and continue. Those are your hard cases and they are more useful
as flagged examples than as forced guesses.

---

## 4. Record as you go

Keep a document open. Every time you hesitate:

- Screenshot the area
- One line: what you were deciding, what you chose, why

Expect five to fifteen of these across ten tiles. **These become the figures and
the difficult-cases log in your class definition document.** You are writing the
hard part of that document by doing the work rather than imagining it.

---

## 5. Time yourself

Note the start and end time for each tile. Ten numbers.

This replaces my guess of 20 to 35 minutes with a measurement, and everything in
the project plan gets recalculated from it.

---

## 6. Afterwards

Three things to look at:

**Your rate.** Median minutes per tile. Multiply by the full tile count.

**Weak label agreement.** Now turn on `_weaklabel.tif`. Per class, where do you
and the rules disagree? Expect boundary pixels, wet sand, sparse vegetation. Is
the disagreement random, or systematically in one direction?

**Your uncertain flags.** How many, and are they clustered on one rule? If most
255s are the bare/vegetated boundary, that rule needs a tighter definition
before full annotation starts.

---

## 7. Then the second annotator

Same ten tiles, same instructions, no discussion beforehand. Compare.

If you and they agree well, the class document works and full annotation can
start. If you do not, the document needs revising — and that is a cheap thing to
discover at ten tiles rather than at five hundred.
