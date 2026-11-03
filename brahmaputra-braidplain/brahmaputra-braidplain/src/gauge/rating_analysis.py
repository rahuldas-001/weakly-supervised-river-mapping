"""
Rating-curve analysis for Pandu and Bhomoraguri (CWC), 2001-2025.

Does four things:
  1. Pairs each discharge value with the water level at the same time and
     plots discharge against stage for every year.
  2. Separates values that sit exactly on a rating curve (computed from stage)
     from values that scatter around it (possibly measured).
  3. Finds when the rating curve was revised.
  4. Specific gauge analysis: the stage at fixed discharges, year by year,
     from the possibly-measured values only.

Run in Colab or locally. Edit the CONFIG block first.
Outputs (CSV and PNG) go to OUT_DIR.

Method notes
- Rating form: Q = a (H - H0)^b, fitted in log space with H0 found by search.
- A value is "on curve" if it lies within ON_CURVE_TOL of the robust annual fit.
  Computed values sit within rounding error; measured values scatter by several %.
- Revisions are found by fitting a rating to the on-curve values of each
  half-year and comparing it with the previous half-year over the stage range
  both cover. An unchanged rating gives ~0 %; a revision gives a step.
- Specific stage uses only off-curve values. With computed values it would
  show the agency's rating revisions, not the river.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ─── CONFIG ────────────────────────────────────────────────────────────────
Q_FILE  = 'Discharge_2001_2025_Pandu_Bhomoraguri.xlsx'   # India-WRIS export
WL_FILE = 'Pandu_and_Bhomoraguri_WL_2001_2025.csv'
OUT_DIR = 'rating_analysis_out'

# Column names in the exports (India-WRIS format). Change if your WL file differs.
COL_STATION, COL_TIME, COL_VALUE = 'stationName', 'dataTime', 'dataValue'

PAIR_TOLERANCE  = pd.Timedelta('3h')     # max gap between a Q value and its stage.
                                         # If stage is read only at 08:00, values at 10-11:00
                                         # need >= 3h; widen if many values stay unpaired.
ON_CURVE_TOL    = 0.01                   # 1 % from the annual fit = "on curve"
MIN_POINTS_FIT  = 20                     # minimum points to fit a rating
JUMP_THRESHOLD  = 0.02                   # 2 % change between periods = possible revision
TARGET_Q        = [5000, 15000, 30000]   # discharges for specific gauge analysis (m3/s)

# Cleaning
# Gauge zero (m above MSL). Pandu: 39.00 m, measured from 35,000 timestamps where the
# file holds both the MSL (HHS) and gauge-zero (HZS) reading. Bhomoraguri is all MSL.
GAUGE_ZERO      = {'Pandu': 39.00}
GAUGE_ZERO_MAX  = 20.0      # a stage below this (m) is a gauge-zero reading, whatever its label
STAGE_RANGE     = {'Pandu': (40.0, 51.0), 'Bhomoraguri': (57.0, 68.5)}   # plausible MSL stage
MAX_STAGE_JUMP  = 1.0       # m per hour; larger jumps are treated as entry errors
Q_RANGE         = (500, 80000)   # plausible discharge, m3/s
LIMB_DAYS       = 3                      # stage change over this many days sets rising/falling
# ───────────────────────────────────────────────────────────────────────────

os.makedirs(OUT_DIR, exist_ok=True)


# ═══ Loading and pairing ═══════════════════════════════════════════════════
def load(path):
    df = pd.read_excel(path) if path.endswith(('.xls', '.xlsx')) else pd.read_csv(path)
    df = df[[COL_STATION, COL_TIME, COL_VALUE]].rename(
        columns={COL_STATION: 'station', COL_TIME: 'time', COL_VALUE: 'value'})
    df['time'] = pd.to_datetime(df['time'])
    df['station'] = df['station'].str.strip()
    return df.dropna().sort_values(['station', 'time'])


def clean_stage(h):
    """Put every stage on one datum (m above MSL) and drop entry errors."""
    h = h.copy()
    n0 = len(h)
    for st, z in GAUGE_ZERO.items():
        m = (h.station == st) & (h.value < GAUGE_ZERO_MAX) & (h.value > 0)
        h.loc[m, 'value'] += z
    h = h.groupby(['station', 'time'], as_index=False)['value'].median()   # drop duplicate HHS/HZS rows
    keep = pd.Series(True, index=h.index)
    for st, (lo, hi) in STAGE_RANGE.items():
        m = h.station == st
        keep &= ~m | h.value.between(lo, hi)
    h = h[keep]
    # spikes: a jump of more than MAX_STAGE_JUMP per hour that reverses
    out = []
    for st, g in h.groupby('station'):
        g = g.sort_values('time')
        dt = g.time.diff().dt.total_seconds().div(3600).clip(lower=1)
        rate = g.value.diff().abs() / dt
        spike = (rate > MAX_STAGE_JUMP) & (rate.shift(-1) > MAX_STAGE_JUMP)
        out.append(g[~spike])
    h = pd.concat(out)
    print(f'Stage: {n0} rows -> {len(h)} after datum correction, de-duplication and range/spike checks')
    return h


def clean_q(q):
    n0 = len(q)
    q = q[q.value.between(*Q_RANGE)]
    q = q.drop_duplicates(['station', 'time'])
    print(f'Discharge: {n0} rows -> {len(q)} after removing values outside {Q_RANGE} m3/s')
    return q


def pair(q, h):
    """Attach to each discharge value the nearest stage reading at the same station."""
    out = []
    for st in sorted(set(q.station) & set(h.station)):
        qs = q[q.station == st].rename(columns={'value': 'Q'})
        hs = h[h.station == st].rename(columns={'value': 'H'})[['time', 'H']]
        m = pd.merge_asof(qs.sort_values('time'), hs.sort_values('time'), on='time',
                          direction='nearest', tolerance=PAIR_TOLERANCE)
        out.append(m)
    p = pd.concat(out).dropna(subset=['Q', 'H'])
    p = p[(p.Q > 0)]
    p['year'] = p.time.dt.year
    p['obs_hour'] = p.time.dt.hour
    p['not_0800'] = p.obs_hour != 8
    return p


def add_limb(p, h):
    """Rising or falling limb from the daily stage change over LIMB_DAYS."""
    res = []
    for st, g in p.groupby('station'):
        daily = h[h.station == st].set_index('time')['value'].resample('D').mean()
        trend = daily.diff(LIMB_DAYS)
        g = g.copy()
        g['dH'] = trend.reindex(g.time.dt.normalize()).values
        g['limb'] = np.where(g.dH > 0.05, 'rising', np.where(g.dH < -0.05, 'falling', 'steady'))
        res.append(g)
    return pd.concat(res)


# ═══ Rating fit ════════════════════════════════════════════════════════════
def fit_rating(H, Q):
    """Fit Q = a (H - H0)^b. Returns (a, b, H0) or None."""
    H, Q = np.asarray(H, float), np.asarray(Q, float)
    if len(H) < MIN_POINTS_FIT or np.ptp(H) < 0.3:
        return None
    best = None
    hmin = H.min()
    for H0 in np.linspace(hmin - 15, hmin - 0.05, 300):
        x = np.log(H - H0)
        b, loga = np.polyfit(x, np.log(Q), 1)
        sse = np.sum((np.log(Q) - (loga + b * x)) ** 2)
        if best is None or sse < best[0]:
            best = (sse, np.exp(loga), b, H0)
    return best[1:]


def rating_q(params, H):
    a, b, H0 = params
    H = np.asarray(H, float)
    return np.where(H > H0, a * np.clip(H - H0, 1e-9, None) ** b, np.nan)


def rating_h(params, Q):
    a, b, H0 = params
    return H0 + (np.asarray(Q, float) / a) ** (1 / b)


def robust_fit(g, n_iter=4):
    """Fit, keep points near the curve, refit. Ends on the dominant (computed) rating."""
    keep = np.ones(len(g), bool)
    params = None
    for _ in range(n_iter):
        params = fit_rating(g.H.values[keep], g.Q.values[keep])
        if params is None:
            return None, None
        resid = g.Q.values / rating_q(params, g.H.values) - 1
        new_keep = np.abs(resid) < max(3 * np.nanmedian(np.abs(resid[keep])), ON_CURVE_TOL)
        if new_keep.sum() < MIN_POINTS_FIT or (new_keep == keep).all():
            break
        keep = new_keep
    return params, g.Q.values / rating_q(params, g.H.values) - 1


# ═══ 1 + 2. Annual fits, on/off-curve classification, Q-H plots ═══════════
def classify(p):
    rows, fits = [], {}
    for (st, yr), g in p.groupby(['station', 'year']):
        params, resid = robust_fit(g)
        g = g.copy()
        if params is None:
            g['resid'] = np.nan
            g['on_curve'] = np.nan
        else:
            g['resid'] = resid
            g['on_curve'] = np.abs(resid) < ON_CURVE_TOL
            fits[(st, yr)] = params
        rows.append(g)
    return pd.concat(rows), fits


def plot_qh(p, fits):
    for st, gs in p.groupby('station'):
        years = sorted(gs.year.unique())
        n = len(years); cols = 5; rows = int(np.ceil(n / cols))
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 2.6), sharex=True, sharey=True)
        for ax, yr in zip(axes.flat, years):
            g = gs[gs.year == yr]
            on = g.on_curve == True
            ax.scatter(g.Q[on] / 1000, g.H[on], s=4, c='#2a78d6', label='on curve')
            ax.scatter(g.Q[~on] / 1000, g.H[~on], s=8, c='#eb6834', label='off curve')
            if (st, yr) in fits:
                hh = np.linspace(g.H.min(), g.H.max(), 100)
                ax.plot(rating_q(fits[(st, yr)], hh) / 1000, hh, c='#222', lw=0.8)
            ax.set_title(str(yr), fontsize=9)
        for ax in list(axes.flat)[n:]:
            ax.axis('off')
        fig.supxlabel('Discharge (1000 m³/s)'); fig.supylabel('Stage (m)')
        axes.flat[0].legend(fontsize=7, frameon=False)
        fig.suptitle(f'{st}: discharge against stage by year')
        fig.tight_layout()
        fig.savefig(f'{OUT_DIR}/1_QH_by_year_{st}.png', dpi=200)
        plt.close(fig)


def plot_residuals(p):
    """Distribution of distance from the annual curve, split by timestamp.
    Computed values pile up near 0; measured values spread out."""
    for st, g in p.groupby('station'):
        fig, ax = plt.subplots(figsize=(6.5, 3.4))
        bins = np.linspace(-15, 15, 121)
        for lab, m, c in [('08:00', ~g.not_0800, '#2a78d6'), ('other times', g.not_0800, '#eb6834')]:
            r = g.resid[m].dropna() * 100
            ax.hist(r.clip(-15, 15), bins=bins, alpha=0.6, color=c,
                    label=f'{lab} (n={len(r)}, median |r|={np.median(np.abs(r)):.2f}%)')
        ax.set_xlabel('Distance from annual rating (%)'); ax.set_ylabel('Count')
        ax.set_title(f'{st}: residuals from the annual rating'); ax.legend(fontsize=8, frameon=False)
        fig.tight_layout(); fig.savefig(f'{OUT_DIR}/2_residuals_{st}.png', dpi=200); plt.close(fig)


# ═══ 3. Rating revisions ═══════════════════════════════════════════════════
def _period(t):
    """Half-year periods: Jan-May (dry) and Jun-Dec (monsoon and after)."""
    return f"{t.year}-{'A' if t.month <= 5 else 'B'}"


def detect_revisions(p):
    """Fit a rating to the on-curve values of each half-year, then compare each
    period's rating with the previous one over the stage range both cover.
    Under one unchanged rating the difference is ~0; a revision shows as a step."""
    events, series = [], []
    for st, g in p[p.on_curve == True].groupby('station'):
        g = g.copy(); g['period'] = g.time.map(_period)
        per = [(k, fit_rating(d.H, d.Q), d.H.min(), d.H.max())
               for k, d in g.groupby('period')]
        per = [x for x in per if x[1] is not None]
        for (k0, f0, lo0, hi0), (k1, f1, lo1, hi1) in zip(per[:-1], per[1:]):
            lo, hi = max(lo0, lo1), min(hi0, hi1)
            if hi - lo < 0.2:                       # too little common stage range
                continue
            hh = np.linspace(lo, hi, 50)
            diff = np.median(rating_q(f1, hh) / rating_q(f0, hh) - 1) * 100
            series.append({'station': st, 'period': k1, 'diff_pct': diff})
            if abs(diff) > JUMP_THRESHOLD * 100:
                events.append({'station': st, 'between': f'{k0} and {k1}',
                               'step_percent': round(diff, 1),
                               'stage_range_compared': f'{lo:.2f}-{hi:.2f} m'})
    ser = pd.DataFrame(series)
    ser.to_csv(f'{OUT_DIR}/3_period_to_period_change.csv', index=False)
    ev = pd.DataFrame(events)
    ev.to_csv(f'{OUT_DIR}/3_possible_revisions.csv', index=False)

    for st, d in ser.groupby('station'):
        fig, ax = plt.subplots(figsize=(10, 3.2))
        x = np.arange(len(d))
        ax.bar(x, d.diff_pct, color=np.where(d.diff_pct.abs() > JUMP_THRESHOLD * 100, '#eb6834', '#9db8d6'))
        ax.axhline(0, c='#888', lw=0.6)
        step = max(1, len(d) // 25)
        ax.set_xticks(x[::step]); ax.set_xticklabels(d.period.values[::step], rotation=90, fontsize=7)
        ax.set_ylabel('Change from previous\nperiod\'s rating (%)')
        ax.set_title(f'{st}: rating change between half-year periods (orange = possible revision)')
        fig.tight_layout(); fig.savefig(f'{OUT_DIR}/3_rating_revisions_{st}.png', dpi=200); plt.close(fig)
    return ev


# ═══ 4. Specific gauge analysis ════════════════════════════════════════════
def specific_gauge(p):
    rows = []
    for (st, yr), g in p.groupby(['station', 'year']):
        sets = {'off-curve, all': g[g.on_curve == False],
                'off-curve, falling limb': g[(g.on_curve == False) & (g.limb == 'falling')],
                'on-curve (rating only)': g[g.on_curve == True]}
        for label, s in sets.items():
            params = fit_rating(s.H, s.Q)
            if params is None:
                continue
            for qt in TARGET_Q:
                if s.Q.min() <= qt <= s.Q.max():      # no extrapolation
                    rows.append({'station': st, 'year': yr, 'set': label, 'Q_target': qt,
                                 'stage': rating_h(params, qt), 'n_points': len(s)})
    sg = pd.DataFrame(rows)
    sg.to_csv(f'{OUT_DIR}/4_specific_gauge.csv', index=False)

    for st, gs in sg.groupby('station'):
        fig, axes = plt.subplots(1, len(TARGET_Q), figsize=(4.2 * len(TARGET_Q), 3.4), sharex=True)
        for ax, qt in zip(np.atleast_1d(axes), TARGET_Q):
            for label, col, ls in [('off-curve, all', '#eb6834', '-'),
                                   ('off-curve, falling limb', '#b0441a', ':'),
                                   ('on-curve (rating only)', '#2a78d6', '--')]:
                d = gs[(gs.Q_target == qt) & (gs.set == label)]
                if len(d):
                    ax.plot(d.year, d.stage, marker='o', ms=3, lw=1.2, c=col, ls=ls, label=label)
            ax.set_title(f'Q = {qt:,} m³/s', fontsize=10); ax.set_xlabel('Year')
        np.atleast_1d(axes)[0].set_ylabel('Stage (m)')
        np.atleast_1d(axes)[0].legend(fontsize=7, frameon=False)
        fig.suptitle(f'{st}: specific gauge analysis')
        fig.tight_layout(); fig.savefig(f'{OUT_DIR}/4_specific_gauge_{st}.png', dpi=200); plt.close(fig)
    return sg


# ═══ Run ═══════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    q = clean_q(load(Q_FILE)); h = clean_stage(load(WL_FILE))
    print('Discharge:', q.groupby('station').size().to_dict())
    print('Stage:    ', h.groupby('station').size().to_dict())

    p = pair(q, h)
    p = add_limb(p, h)
    print(f'\nPaired values: {len(p)} of {len(q)} discharge values (tolerance {PAIR_TOLERANCE})')
    if len(p) < 0.9 * len(q):
        print('  WARNING: many discharge values have no stage reading nearby. '
              'Check the WL timestamps and widen PAIR_TOLERANCE.')

    p, fits = classify(p)
    plot_qh(p, fits)
    plot_residuals(p)

    p = p.reset_index(drop=True)
    p['off_curve'] = p.on_curve == False
    p['off_and_not_0800'] = p.off_curve & p.not_0800
    summary = (p.groupby(['station', 'year'])
                 .agg(n=('Q', 'size'),
                      on_curve=('on_curve', lambda s: int((s == True).sum())),
                      off_curve=('off_curve', 'sum'),
                      off_curve_not_0800=('off_and_not_0800', 'sum'),
                      median_abs_resid_pct=('resid', lambda r: round(np.nanmedian(np.abs(r)) * 100, 2)))
                 .reset_index())
    summary.to_csv(f'{OUT_DIR}/2_on_off_curve_by_year.csv', index=False)
    print('\n2. On/off curve by year\n', summary.to_string(index=False))

    # Does being off-curve go with a non-08:00 timestamp?
    print('\nOff-curve share by timestamp:')
    print(p.groupby(['station', 'not_0800'])['on_curve']
            .apply(lambda s: round((s == False).mean() * 100, 1)).rename('% off curve').to_string())

    rev = detect_revisions(p)
    print('\n3. Possible rating revisions\n', rev.to_string(index=False) if len(rev) else 'none found')

    sg = specific_gauge(p)
    print('\n4. Specific gauge (first rows)\n', sg.head(20).to_string(index=False))

    p.to_csv(f'{OUT_DIR}/paired_classified.csv', index=False)
    print(f'\nAll outputs in {OUT_DIR}/')
