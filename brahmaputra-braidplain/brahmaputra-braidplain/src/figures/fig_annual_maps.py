"""
Annual classification maps, 2019-2026, as one multi-panel figure.

Makes two figures from the same GeoTIFFs:
  fig_annual_maps_full.*  whole reach, 8 panels (for the supplement)
  fig_annual_maps_zoom.*  one sub-reach, 8 panels (for the main text)

Pick the zoom window in ArcMap: read the corner coordinates (UTM 46N, metres)
of a 15-20 km stretch where bars and channels are clearly visible, and enter
them in ZOOM_BOUNDS.

Class colours match the line graphs (fig_planform_change).
"""

import os
import numpy as np
import rasterio
from rasterio.windows import from_bounds
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

PRED_DIR = '/content/drive/MyDrive/BRAHMA_MORPHO/inference'          # edit
PATTERN  = 'attention_unet_pred_{year}_braidplain_spatial.tif'
YEARS    = list(range(2019, 2027))
OUT_DIR  = os.path.join(PRED_DIR, 'figures')

# (left, bottom, right, top) in EPSG:32646 metres. Edit after choosing in ArcMap.
ZOOM_BOUNDS = None          # e.g. (760000, 2900000, 778000, 2912000)

COLOURS = ['#ffffff',       # 0 background / outside envelope
           '#2a78d6',       # 1 water
           '#eb6834',       # 2 bare bar
           '#1baf7a']       # 3 vegetated bar
NAMES = ['Water', 'Bare bar', 'Vegetated bar']
cmap = ListedColormap(COLOURS)
norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], cmap.N)

INK, MUTED = '#222222', '#666666'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9})
os.makedirs(OUT_DIR, exist_ok=True)


def read(year, bounds=None):
    with rasterio.open(os.path.join(PRED_DIR, PATTERN.format(year=year))) as src:
        if bounds is None:
            a = src.read(1)
            b = src.bounds
            ext = (b.left, b.right, b.bottom, b.top)
        else:
            w = from_bounds(*bounds, transform=src.transform)
            a = src.read(1, window=w, boundless=True, fill_value=0)
            ext = (bounds[0], bounds[2], bounds[1], bounds[3])
    return a, ext


def crop_to_data(arrs, ext, pad=20):
    """Trim empty margins shared by all years."""
    occ = np.any([a > 0 for a in arrs], axis=0)
    r = np.where(occ.any(1))[0]; c = np.where(occ.any(0))[0]
    r0, r1 = max(r[0] - pad, 0), min(r[-1] + pad, occ.shape[0] - 1)
    c0, c1 = max(c[0] - pad, 0), min(c[-1] + pad, occ.shape[1] - 1)
    px = (ext[1] - ext[0]) / occ.shape[1]
    new_ext = (ext[0] + c0 * px, ext[0] + (c1 + 1) * px,
               ext[3] - (r1 + 1) * px, ext[3] - r0 * px)
    return [a[r0:r1 + 1, c0:c1 + 1] for a in arrs], new_ext


def scalebar(ax, ext, km):
    width_km = (ext[1] - ext[0]) / 1000
    while km > 0.4 * width_km and km > 1:      # keep the bar inside the panel
        km = km // 2 or 1
    x0 = ext[0] + 0.05 * (ext[1] - ext[0])
    y0 = ext[2] + 0.07 * (ext[3] - ext[2])
    ax.plot([x0, x0 + km * 1000], [y0, y0], color=INK, lw=2.5, solid_capstyle='butt')
    ax.text(x0 + km * 500, y0 + 0.03 * (ext[3] - ext[2]), f'{km} km',
            ha='center', va='bottom', fontsize=8, color=INK)
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])   # keep the bar from rescaling the panel


def make(bounds, name, ncols, width_in, bar_km):
    arrs, ext = [], None
    for y in YEARS:
        a, ext = read(y, bounds)
        arrs.append(a)
    if bounds is None:
        arrs, ext = crop_to_data(arrs, ext)

    nrows = int(np.ceil(len(YEARS) / ncols))
    aspect = (ext[3] - ext[2]) / (ext[1] - ext[0])
    panel_w = width_in / ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(width_in, panel_w * aspect * nrows + 0.6),
                             layout='constrained')
    for ax, y, a in zip(axes.flat, YEARS, arrs):
        ax.imshow(a, cmap=cmap, norm=norm, extent=ext, interpolation='nearest')
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color('#cccccc'); s.set_linewidth(0.6)
        ax.text(0.02, 0.96, str(y), transform=ax.transAxes, va='top', ha='left',
                fontsize=10, color=INK, fontweight='bold')
    for ax in list(axes.flat)[len(YEARS):]:
        ax.axis('off')
    scalebar(axes.flat[0], ext, bar_km)

    handles = [Patch(facecolor=c, label=n) for c, n in zip(COLOURS[1:], NAMES)]
    fig.legend(handles=handles, loc='outside lower center', ncol=3, frameon=False, fontsize=9)

    out = os.path.join(OUT_DIR, name)
    fig.savefig(out + '.png', dpi=300, bbox_inches='tight')
    fig.savefig(out + '.pdf', bbox_inches='tight')
    fig.savefig(out + '.jpg', dpi=300, bbox_inches='tight', pil_kwargs={'quality': 95})
    plt.close(fig)
    print('saved', out)


make(None, 'fig_annual_maps_full', ncols=2, width_in=7.5, bar_km=20)
if ZOOM_BOUNDS is not None:
    make(ZOOM_BOUNDS, 'fig_annual_maps_zoom', ncols=4, width_in=7.5, bar_km=5)
else:
    print('Set ZOOM_BOUNDS to make the zoomed figure.')
