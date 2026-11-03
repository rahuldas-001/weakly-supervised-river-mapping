# Why splits are spatial, not random

## The problem

The prototype pipeline generated tiles with `OVERLAP_M = 256` on a
`TILE_SIZE_M = 2560` grid, so the step was 2304 m and adjacent tiles shared 10%
of their footprint. `create_splits()` then assigned tiles to train, validation
and test by random shuffle.

Random assignment plus overlapping tiles means two tiles containing the same
ground can land on opposite sides of the split. Reported test metrics are
therefore optimistic by an unknown margin.

Even without overlap, adjacent tiles in a braided river are strongly correlated:
the same bar complex, the same channel, the same illumination and water level.
Random splitting measures interpolation within a scene, not generalisation.

## The fix

Assign contiguous blocks of tiles, not individual tiles. Block size is set by
`splits.block_size_tiles`. Blocks are assigned to train, validation or test as
units, so no test ground is adjacent to training ground.

## Cross-basin holdout

Set `splits.holdout_river` to reserve one entire river for testing. This is the
only split that measures whether the model generalises across braiding style,
sediment calibre and hydrological regime. It is worth more than any amount of
additional within-basin data.

## Reporting

Report all three: block-split within basin, cross-basin holdout, and if desired
the random split for comparison with prior work that used one. Stating the
difference between them is itself a useful result.
