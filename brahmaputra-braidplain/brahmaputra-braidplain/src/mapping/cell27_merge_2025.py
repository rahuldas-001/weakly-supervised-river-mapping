# ═══════════════════════════════════════════════════════════════════════════
# MERGE 2025 TILES  — replaces merge_2025_into_training()
#
# WHY THIS CHANGED
# The previous merge appended all 2025 tiles to the training set. Because the
# 2025 grid covers the same ground as 2024 (train_tile_N and train2025_tile_N
# are the same location), a location could sit in training for 2025 and in test
# for 2024. Adjacent lean seasons on a braided river are highly correlated, so
# the model would effectively have seen the test ground.
#
# This version assigns each 2025 tile to the split its 2024 counterpart received,
# so a location belongs to exactly one split regardless of year.
#
# Run AFTER create_spatial_splits().
# ═══════════════════════════════════════════════════════════════════════════

import re

TILES_2025 = os.path.join(TILES, 'training_2025')


def tile_index(tile_id):
    """Extract the numeric grid index shared between years.

    train_tile_2286      -> 2286
    train2025_tile_2286  -> 2286
    """
    m = re.search(r'tile_(\d+)$', tile_id)
    return int(m.group(1)) if m else None


def merge_2025_by_block(splits_dir=None, include_in_eval=True, write=True):
    """Assign 2025 tiles to the same split as their 2024 counterparts.

    include_in_eval
        True  — 2025 tiles join train, val and test alike. More evaluation data,
                and no leakage because location determines the split.
        False — 2025 tiles go only into training. Val and test stay 2024-only,
                matching the original behaviour. Choose this if you want the
                evaluation set to be a single season.
    """
    splits_dir = splits_dir or SPLITS_V2

    # ── Load the 2024 split assignment ───────────────────────────────────
    splits_2024 = {}
    for name in ('train', 'val', 'test'):
        with open(os.path.join(splits_dir, f'{name}_tiles.json')) as f:
            splits_2024[name] = json.load(f)

    # index -> split name
    index_to_split = {}
    for name, ids in splits_2024.items():
        for tid in ids:
            idx = tile_index(tid)
            if idx is not None:
                index_to_split[idx] = name

    print(f'  2024 tiles assigned to a split : {len(index_to_split)}')

    # ── Walk the 2025 tiles ──────────────────────────────────────────────
    available_2025 = [
        t for t in sorted(os.listdir(TILES_2025))
        if os.path.exists(os.path.join(TILES_2025, t, 'mask.npy'))
    ]
    print(f'  2025 tiles on disk             : {len(available_2025)}')

    assigned = {'train': [], 'val': [], 'test': []}
    dropped_buffer = 0
    dropped_unmatched = 0

    for tid in available_2025:
        idx = tile_index(tid)
        if idx is None:
            dropped_unmatched += 1
            continue
        target = index_to_split.get(idx)
        if target is None:
            # counterpart was a buffer tile at a block seam, or was not selected
            # by background subsampling. Drop it: same reasoning applies.
            dropped_buffer += 1
            continue
        if target != 'train' and not include_in_eval:
            continue
        assigned[target].append(tid)

    print(f'  2025 dropped (seam / not selected) : {dropped_buffer}')
    if dropped_unmatched:
        print(f'  2025 dropped (unparseable id)      : {dropped_unmatched}')

    # ── Build merged splits ──────────────────────────────────────────────
    merged = {name: sorted(splits_2024[name] + assigned[name])
              for name in ('train', 'val', 'test')}

    print()
    print(f'  {"split":6s} {"2024":>6s} {"2025":>6s} {"total":>7s}')
    for name in ('train', 'val', 'test'):
        print(f'  {name:6s} {len(splits_2024[name]):6d} '
              f'{len(assigned[name]):6d} {len(merged[name]):7d}')

    # ── Verify no location appears in two splits ─────────────────────────
    location_split = {}
    conflicts = 0
    for name, ids in merged.items():
        for tid in ids:
            idx = tile_index(tid)
            if idx in location_split and location_split[idx] != name:
                conflicts += 1
            location_split[idx] = name
    print(f'\n  LOCATION CHECK: {conflicts} locations appear in more than one '
          f'split {"— PASS" if conflicts == 0 else "— FAIL"}')

    if write:
        for name, ids in merged.items():
            with open(os.path.join(splits_dir, f'{name}_tiles_merged.json'), 'w') as f:
                json.dump(ids, f, indent=2)

        manifest_path = os.path.join(splits_dir, 'split_manifest.json')
        manifest = {}
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                manifest = json.load(f)
        manifest['merge_2025'] = {
            'method': 'block_respecting',
            'include_in_eval': include_in_eval,
            'n_2025_added': {k: len(v) for k, v in assigned.items()},
            'n_2025_dropped_seam': dropped_buffer,
            'n_merged': {k: len(v) for k, v in merged.items()},
            'location_conflicts': conflicts,
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        print(f'  Written *_tiles_merged.json to {splits_dir}')

    return merged


# ── Run ──────────────────────────────────────────────────────────────────
merged = merge_2025_by_block(include_in_eval=True)
