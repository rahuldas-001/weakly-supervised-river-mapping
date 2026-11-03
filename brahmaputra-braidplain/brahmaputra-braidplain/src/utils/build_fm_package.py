"""
Build FM_comparison_package in your Drive by COPYING files from BRAHMA_MORPHO.
Nothing in BRAHMA_MORPHO is moved, changed or deleted.

Only the 1,094 tiles used in the spatial split are copied, not all 6,572.
Run in Colab after mounting Drive. Copying to Drive is slow; expect 20-40 minutes.
Safe to re-run: files already copied are skipped.
"""

import os, json, glob, shutil

SRC = '/content/drive/MyDrive/BRAHMA_MORPHO'
DST = '/content/drive/MyDrive/FM_comparison_package'

def copy(src, dst_dir, name=None):
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, name or os.path.basename(src))
    if not os.path.exists(src):
        print(f'  MISSING: {src}')
        return
    if not os.path.exists(dst):
        shutil.copy2(src, dst)

# 1. Splits
print('Splits')
split_dir = f'{SRC}/training/splits_spatial'
for f in ['train_tiles_merged.json', 'val_tiles_merged.json',
          'test_tiles_merged.json', 'split_manifest.json']:
    copy(f'{split_dir}/{f}', f'{DST}/splits')

# 2. Tiles and metadata (only tiles listed in the merged splits)
ids = []
for s in ['train', 'val', 'test']:
    ids += json.load(open(f'{split_dir}/{s}_tiles_merged.json'))
print(f'Tiles to copy: {len(ids)}')

meta_src = f'{SRC}/training/metadata'
for i, tid in enumerate(ids, 1):
    folder = 'training_2025' if tid.startswith('train2025_') else 'training'
    src_t = f'{SRC}/training/tiles/{folder}/{tid}'
    dst_t = f'{DST}/tiles/{folder}/{tid}'
    if not os.path.isdir(src_t):
        print(f'  MISSING tile: {tid}')
        continue
    for f in os.listdir(src_t):
        copy(f'{src_t}/{f}', dst_t)
    for m in glob.glob(f'{meta_src}/{tid}*.json'):
        copy(m, f'{DST}/tile_metadata')
    if i % 100 == 0:
        print(f'  {i}/{len(ids)}')

# 3. Normalisation: training mean and std (.npy in models/attention_unet)
print('Normalisation')
for f in glob.glob(f'{SRC}/models/attention_unet/*.npy'):
    copy(f, f'{DST}/normalisation')

# 4. Code
print('Code')
for f in ['SCRIPT2A_ATTENTION_UNET.ipynb', 'SCRIPT2B_SEGFORMER.ipynb', 'Dataset_Preparation.ipynb']:
    copy(f'{SRC}/{f}', f'{DST}/code')

# 5. Baseline results
print('Baseline results')
ref = f'{DST}/baseline_results'
copy(f'{SRC}/models/segformer/segformer_test_metrics.json', ref)
# This file currently holds the 6-band (ablation) results, so it is renamed on copy.
copy(f'{SRC}/models/attention_unet/attention_unet_test_metrics.json', ref,
     'attention_unet_6band_test_metrics.json')
# 9-band baseline weights (377 MB). Set to False to leave them out.
INCLUDE_BASELINE_WEIGHTS = True
if INCLUDE_BASELINE_WEIGHTS:
    copy(f'{SRC}/models/attention_unet/attention_unet_best_spatial.pth', ref)

# 8. Check
print('\nCheck')
for folder in ['training', 'training_2025']:
    p = f'{DST}/tiles/{folder}'
    n = len(os.listdir(p)) if os.path.isdir(p) else 0
    print(f'  tiles/{folder}: {n} tiles (expected 547)')
print(f'  tile_metadata: {len(os.listdir(f"{DST}/tile_metadata"))} files')
for d in ['splits', 'normalisation', 'code', 'baseline_results']:
    print(f'  {d}: {sorted(os.listdir(f"{DST}/{d}"))}')

print('\nStill to add by hand:')
print('  baseline_results/attention_unet_9band_test_metrics.json   (re-run test evaluation with attention_unet_best_spatial.pth)')
