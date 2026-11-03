# ═══════════════════════════════════════════════════════════════════════════
# SPATIAL BLOCK SPLITS  — replaces create_splits()
#
# WHY: the previous split shuffled tile_ids randomly. Tiles are generated with
# OVERLAP_M = 256 on a 2560 m grid, so adjacent tiles share 10% of their ground.
# Random assignment therefore puts the same ground in train and test, and the
# reported metrics measure interpolation within a scene rather than
# generalisation. This version assigns contiguous blocks along the reach.
#
# Reads x_min/y_min from the metadata already written by extract_tile().
# No re-extraction needed.
# ═══════════════════════════════════════════════════════════════════════════

SPLITS_V2 = f'{ROOT}/training/splits_spatial'
for d in [SPLITS_V2, f'{SPLITS_V2}/train', f'{SPLITS_V2}/val', f'{SPLITS_V2}/test']:
    os.makedirs(d, exist_ok=True)
print(f'Spatial split output: {SPLITS_V2}')


def load_tile_records(site_name='training'):
    """Collect tile_id, coordinates and type from the existing metadata."""
    tile_root = os.path.join(TILES, site_name)
    records = []
    missing_meta = 0

    for tile_id in sorted(os.listdir(tile_root)):
        mask_path = os.path.join(tile_root, tile_id, 'mask.npy')
        meta_path = os.path.join(META, f'{tile_id}.json')
        if not os.path.exists(mask_path):
            continue
        if not os.path.exists(meta_path):
            missing_meta += 1
            continue

        with open(meta_path) as f:
            meta = json.load(f)

        records.append({
            'tile_id':   tile_id,
            'x':         meta['x_min'],
            'y':         meta['y_min'],
            'tile_type': meta.get('tile_type', 'braidplain'),
        })

    if missing_meta:
        print(f'  WARNING: {missing_meta} tiles have no metadata and were skipped')
    return records


def create_spatial_splits(target_bg_fraction=0.35, block_size=8, buffer_tiles=1,
                          train_frac=0.80, val_frac=0.10, seed=42,
                          site_name='training', write=True):
    """Stratified background sampling, but split by contiguous spatial blocks."""
    import random
    rng = random.Random(seed)

    records = load_tile_records(site_name)
    if not records:
        raise RuntimeError(f'No tiles found under {os.path.join(TILES, site_name)}')

    braidplain = [r for r in records if r['tile_type'] != 'background']
    background = [r for r in records if r['tile_type'] == 'background']
    print(f'  Braidplain tiles available : {len(braidplain)}')
    print(f'  Background tiles available : {len(background)}')

    # ── Background subsampling, unchanged from the original ──────────────
    n_bp = len(braidplain)
    n_bg_target = int(n_bp * target_bg_fraction / (1 - target_bg_fraction))
    n_bg_use = min(n_bg_target, len(background))
    rng.shuffle(background)
    selected = braidplain + background[:n_bg_use]
    print(f'  Background tiles selected  : {n_bg_use} '
          f'({100 * n_bg_use / (n_bp + n_bg_use):.1f}% of dataset)')

    # ── Block along the long axis of the reach ───────────────────────────
    xs = [r['x'] for r in selected]
    ys = [r['y'] for r in selected]
    axis = 'x' if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else 'y'
    print(f'  Reach long axis            : {axis}')

    positions = sorted({r[axis] for r in selected})
    pos_to_block = {p: i // block_size for i, p in enumerate(positions)}
    for r in selected:
        r['block'] = pos_to_block[r[axis]]

    block_ids = sorted({r['block'] for r in selected})
    rng.shuffle(block_ids)          # so splits are not simply up/mid/downstream

    n = len(block_ids)
    n_train = max(1, int(round(n * train_frac)))
    n_val = max(1, int(round(n * val_frac)))
    if n_train + n_val >= n:
        n_val = max(1, n - n_train - 1)

    assign = {
        'train': set(block_ids[:n_train]),
        'val':   set(block_ids[n_train:n_train + n_val]),
        'test':  set(block_ids[n_train + n_val:]),
    }
    print(f'  Blocks                     : {n} '
          f'(train {len(assign["train"])}, val {len(assign["val"])}, '
          f'test {len(assign["test"])})')

    # ── Buffer: drop tile-columns at the edges of held-out blocks ────────
    def buffer_block(tiles_in_block):
        if buffer_tiles <= 0:
            return tiles_in_block
        pos = sorted({t[axis] for t in tiles_in_block})
        if len(pos) <= 2 * buffer_tiles:
            return []
        keep = set(pos[buffer_tiles:-buffer_tiles])
        return [t for t in tiles_in_block if t[axis] in keep]

    splits, n_buffered = {}, 0
    for name, blocks in assign.items():
        collected = []
        for b in sorted(blocks):
            in_block = [r for r in selected if r['block'] == b]
            kept = in_block if name == 'train' else buffer_block(in_block)
            n_buffered += len(in_block) - len(kept)
            collected += kept
        splits[name] = collected

    # ── Leakage check ────────────────────────────────────────────────────
    def overlaps(a, b, size=TILE_SIZE_M):
        return abs(a['x'] - b['x']) < size and abs(a['y'] - b['y']) < size

    leaks = 0
    for held in ('val', 'test'):
        for t in splits[held]:
            if any(overlaps(t, tr) for tr in splits['train']):
                leaks += 1

    # ── Report and write ─────────────────────────────────────────────────
    total = sum(len(v) for v in splits.values())
    print()
    for name in ('train', 'val', 'test'):
        print(f'  {name:5s}: {len(splits[name]):5d} tiles '
              f'({100 * len(splits[name]) / total:.1f}%)')
    print(f'  buffer: {n_buffered:5d} tiles discarded at block seams')
    print(f'  LEAKAGE CHECK: {leaks} held-out tiles overlap a training tile '
          f'{"— PASS" if leaks == 0 else "— FAIL"}')

    if write:
        for name, recs in splits.items():
            ids = sorted(r['tile_id'] for r in recs)
            with open(os.path.join(SPLITS_V2, f'{name}_tiles.json'), 'w') as f:
                json.dump(ids, f, indent=2)
        with open(os.path.join(SPLITS_V2, 'split_manifest.json'), 'w') as f:
            json.dump({
                'method': 'spatial_block',
                'block_size': block_size, 'buffer_tiles': buffer_tiles,
                'axis': axis, 'seed': seed,
                'target_bg_fraction': target_bg_fraction,
                'blocks': {k: sorted(v) for k, v in assign.items()},
                'n_tiles': {k: len(v) for k, v in splits.items()},
                'n_buffered': n_buffered, 'leakage_check': leaks,
            }, f, indent=2)
        print(f'\n  Written to {SPLITS_V2}')

    return {k: [r['tile_id'] for r in v] for k, v in splits.items()}


def compare_with_random(target_bg_fraction=0.35, seed=42, site_name='training'):
    """Quantify how much ground the old random split shared across splits.

    Run once. The number goes in the paper: stating the size of the problem is
    stronger than asserting that a spatial split was used.
    """
    import random
    rng = random.Random(seed)
    records = load_tile_records(site_name)

    bp = [r for r in records if r['tile_type'] != 'background']
    bg = [r for r in records if r['tile_type'] == 'background']
    n_bg = min(int(len(bp) * target_bg_fraction / (1 - target_bg_fraction)), len(bg))
    rng.shuffle(bg)
    sel = bp + bg[:n_bg]
    rng.shuffle(sel)

    n = len(sel)
    rand = {'train': sel[:int(n * .8)],
            'val':   sel[int(n * .8):int(n * .9)],
            'test':  sel[int(n * .9):]}

    def overlaps(a, b, size=TILE_SIZE_M):
        return abs(a['x'] - b['x']) < size and abs(a['y'] - b['y']) < size

    leaks = sum(
        any(overlaps(t, tr) for tr in rand['train'])
        for held in ('val', 'test') for t in rand[held]
    )
    held_n = len(rand['val']) + len(rand['test'])
    print(f'\n  RANDOM SPLIT: {leaks}/{held_n} held-out tiles '
          f'({100 * leaks / held_n:.0f}%) overlap a training tile')
    return leaks, held_n


# ── Run ──────────────────────────────────────────────────────────────────
compare_with_random(target_bg_fraction=0.35)          # note this number
splits = create_spatial_splits(target_bg_fraction=0.35,
                               block_size=8, buffer_tiles=1)
