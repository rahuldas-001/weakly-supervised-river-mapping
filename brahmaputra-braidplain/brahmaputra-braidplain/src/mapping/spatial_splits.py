"""
Spatial block splitting for braided river tiles.

REPLACES the random `create_splits()` in Dataset_Preparation.ipynb.

WHY
---
The original split assigned tiles to train/val/test by random shuffle. Tiles were
generated with OVERLAP_M = 256 on a TILE_SIZE_M = 2560 grid, so adjacent tiles
share 10% of their footprint. Random assignment therefore places the same ground
in both training and test, and reported metrics are optimistic by an unknown
margin.

Even without overlap, adjacent tiles in a braided river share the same bar
complex, the same channel, the same water level and the same illumination.
A random split measures interpolation within a scene, not generalisation.

WHAT THIS DOES
--------------
Groups tiles into contiguous blocks along the reach, then assigns whole blocks.
Optionally inserts a buffer of discarded tiles between splits so that even
overlapping tiles cannot straddle a boundary.

Drop-in usage in the notebook:

    from spatial_splits import create_spatial_splits, report_split

    splits = create_spatial_splits(
        tiles,                      # your list of tile dicts
        block_size=8,               # tiles per block along the reach
        buffer_tiles=1,             # discard this many at each block edge
        train_frac=0.80, val_frac=0.10,
        seed=42,
    )
    report_split(splits, tiles)

Each tile dict must have at least: 'tile_id', 'x', 'y' (projected coordinates
of the tile origin, in metres).
"""

from __future__ import annotations

import random
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────────────────
def _reach_axis(tiles: list[dict]) -> str:
    """Return 'x' or 'y', whichever the reach extends along.

    Braided reaches are long and thin. Blocking along the long axis gives
    contiguous chunks of river rather than arbitrary rectangles.
    """
    xs = [t["x"] for t in tiles]
    ys = [t["y"] for t in tiles]
    return "x" if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else "y"


def assign_blocks(tiles: list[dict], block_size: int = 8) -> dict[int, list[dict]]:
    """Group tiles into contiguous blocks of `block_size` along the reach axis."""
    axis = _reach_axis(tiles)
    ordered = sorted(tiles, key=lambda t: (t[axis], t["y" if axis == "x" else "x"]))

    # unique positions along the reach, so a block is a slice of the reach
    positions = sorted({t[axis] for t in ordered})
    pos_to_block = {p: i // block_size for i, p in enumerate(positions)}

    blocks: dict[int, list[dict]] = defaultdict(list)
    for t in ordered:
        blocks[pos_to_block[t[axis]]].append(t)
    return dict(blocks)


def _buffer_out(block: list[dict], axis: str, n: int) -> list[dict]:
    """Drop `n` tile-columns from each end of a block.

    These discarded tiles sit on the seam between two splits. Removing them
    guarantees that no test tile overlaps a training tile even when tiles were
    generated with overlap.
    """
    if n <= 0:
        return block
    positions = sorted({t[axis] for t in block})
    if len(positions) <= 2 * n:
        return []                      # block too small to buffer; drop it
    keep = set(positions[n:-n])
    return [t for t in block if t[axis] in keep]


# ─────────────────────────────────────────────────────────────────────────────
def create_spatial_splits(
    tiles: list[dict],
    block_size: int = 8,
    buffer_tiles: int = 1,
    train_frac: float = 0.80,
    val_frac: float = 0.10,
    seed: int = 42,
) -> dict[str, list[dict]]:
    """Assign whole spatial blocks to train / val / test.

    Blocks are shuffled before assignment so the splits are not simply the
    upstream, middle and downstream thirds, which would confound the split with
    a genuine downstream gradient in braiding style.
    """
    axis = _reach_axis(tiles)
    blocks = assign_blocks(tiles, block_size)
    ids = sorted(blocks)

    rng = random.Random(seed)
    rng.shuffle(ids)

    n = len(ids)
    n_train = max(1, int(round(n * train_frac)))
    n_val = max(1, int(round(n * val_frac)))
    if n_train + n_val >= n:                    # guarantee a non-empty test set
        n_val = max(1, n - n_train - 1)

    groups = {
        "train": ids[:n_train],
        "val": ids[n_train:n_train + n_val],
        "test": ids[n_train + n_val:],
    }

    out: dict[str, list[dict]] = {}
    for name, block_ids in groups.items():
        collected = []
        for b in block_ids:
            # buffer val and test only; training may keep its seams
            nb = buffer_tiles if name in ("val", "test") else 0
            collected += _buffer_out(blocks[b], axis, nb)
        out[name] = collected

    out["_blocks"] = groups          # kept for reporting and reproducibility
    return out


# ─────────────────────────────────────────────────────────────────────────────
def verify_no_leakage(
    splits: dict[str, list[dict]],
    tile_size_m: float,
    min_separation_m: float = 0.0,
) -> dict:
    """Confirm no test tile overlaps (or sits too close to) any training tile.

    Run this and put the result in the paper. A stated leakage check is the
    difference between a metric a reviewer trusts and one they do not.
    """
    def overlaps(a, b, size, sep):
        return (abs(a["x"] - b["x"]) < size + sep and
                abs(a["y"] - b["y"]) < size + sep)

    problems = []
    for held in ("val", "test"):
        for t in splits[held]:
            for tr in splits["train"]:
                if overlaps(t, tr, tile_size_m, min_separation_m):
                    problems.append((held, t["tile_id"], tr["tile_id"]))
                    break
    return {
        "n_problems": len(problems),
        "examples": problems[:10],
        "pass": len(problems) == 0,
    }


def report_split(splits: dict[str, list[dict]], tiles: list[dict]) -> None:
    total = len(tiles)
    kept = sum(len(splits[k]) for k in ("train", "val", "test"))
    print("Spatial block split")
    print("-" * 46)
    for k in ("train", "val", "test"):
        n = len(splits[k])
        print(f"  {k:6s} {n:5d} tiles  ({n / total:5.1%})  "
              f"blocks: {sorted(splits['_blocks'][k])}")
    print(f"  {'buffer':6s} {total - kept:5d} tiles discarded at split seams")
    print(f"  {'total':6s} {total:5d}")


# ─────────────────────────────────────────────────────────────────────────────
def compare_with_random(
    tiles: list[dict],
    tile_size_m: float,
    seed: int = 42,
) -> None:
    """Quantify how much ground the old random split shared between splits.

    Worth running once so the paper can state the size of the problem that was
    fixed, rather than just asserting that a spatial split was used.
    """
    rng = random.Random(seed)
    shuffled = tiles[:]
    rng.shuffle(shuffled)
    n = len(shuffled)
    rand = {
        "train": shuffled[:int(n * 0.8)],
        "val": shuffled[int(n * 0.8):int(n * 0.9)],
        "test": shuffled[int(n * 0.9):],
    }
    rand_leak = verify_no_leakage(rand, tile_size_m)

    spatial = create_spatial_splits(tiles, seed=seed)
    spat_leak = verify_no_leakage(spatial, tile_size_m)

    print("\nLeakage comparison")
    print("-" * 46)
    print(f"  random split : {rand_leak['n_problems']:4d} held-out tiles "
          f"adjacent to or overlapping training tiles")
    print(f"  spatial split: {spat_leak['n_problems']:4d}")
    if rand_leak["n_problems"]:
        frac = rand_leak["n_problems"] / (len(rand["val"]) + len(rand["test"]))
        print(f"  -> {frac:.0%} of held-out tiles were contaminated under the "
              f"random split")


if __name__ == "__main__":
    # synthetic reach: 60 tiles long, 6 wide, 10% overlap as in the notebook
    TILE_M, STEP_M = 2560, 2304
    demo = [
        {"tile_id": f"t_{i:03d}_{j}", "x": i * STEP_M, "y": j * STEP_M}
        for i in range(60) for j in range(6)
    ]
    s = create_spatial_splits(demo, block_size=8, buffer_tiles=1)
    report_split(s, demo)
    print("\nLeakage check:", verify_no_leakage(s, TILE_M))
    compare_with_random(demo, TILE_M)
