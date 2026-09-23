# -*- coding: utf-8 -*-
"""Export the per-symbol history the live scanner needs to reproduce
engine2.screen() for the NEXT session (see signal_spec.py).

export(d, I, tls, sect, C, i, next_day) -> (syms, U)
  i        : index of the last CLOSED session (the spec is for session i+1)
  next_day : datetime.date of session i+1 (fundamentals as_of that day,
             exactly like the engine does on the signal day)
"""
import datetime as dt
import numpy as np
from engine import risk_gate, canslim_score, as_of
from fa_ind import rmax, rmin

STATIC = ('C1', 'C2', 'C3', 'A1', 'A2')


def _s19(a, i):
    w = a[max(0, i - 18):i + 1]
    m = ~np.isnan(w)
    return (float(np.nansum(w)) if m.any() else None), int(m.sum())


def _f(x, nd=None):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if x != x:
        return None
    return round(x, nd) if nd is not None else x


def next_weekday(d0):
    d = d0 + dt.timedelta(days=1)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


def export(d, I, tls, sect, C, i, next_day=None, scan_n=None, syms_extra=()):
    S = [str(x) for x in d['sym']]
    cal = [str(x) for x in d['cal']]
    next_day = next_day or next_weekday(dt.date.fromisoformat(cal[i]))
    AC, AH, AL = d['AdjClose'], d['AdjHigh'], d['AdjLow']
    V, TV, MC, PC = d['Volume'], d['TotalValue'], d['MarketCap'], d['PriceClose']
    rng = (AH - AL) / np.where(AC > 0, AC, np.nan)
    blen = int(C.get('base_len', 30))
    # base for session i+1 = window of `base_len` sessions ENDING at i (engine: shift(rmax,1))
    lo_ = max(0, i - blen + 1)
    top_n = int(C.get('top_n', 120))
    tvma = I['tvma20'][i]
    x = np.where(np.isnan(tvma), -1.0, tvma)
    live = x > 0
    m = min(top_n, int(live.sum()))
    cut = float(np.partition(x, -m)[-m]) if m else float('inf')
    # scan set: TOP-N by yesterday's 20d GTGD plus a margin (entrants from below)
    scan_n = scan_n or int(top_n * 1.5)
    mm = min(scan_n, int(live.sum()))
    cut_scan = float(np.partition(x, -mm)[-mm]) if mm else float('inf')
    r12 = AC[i] / AC[i - 250] - 1 if i >= 250 else np.full(len(S), np.nan)
    r3 = AC[i] / AC[i - 60] - 1 if i >= 60 else np.full(len(S), np.nan)
    U = dict(topn_cut=cut, top_n=top_n,
             r12=sorted(float(v) for v in r12 if v == v),
             r3=sorted(float(v) for v in r3 if v == v))
    out = {}
    for j, s in enumerate(S):
        if not (live[j] and (x[j] >= cut_scan or s in syms_extra)):
            continue
        if not (PC[i, j] == PC[i, j]) or PC[i, j] <= 0:
            continue
        hi30 = np.nanmax(AC[lo_:i + 1, j]); lo30 = np.nanmin(AC[lo_:i + 1, j])
        base = float((hi30 - lo30) / lo30) if (lo30 == lo30 and lo30 > 0 and (i - lo_ + 1) >= blen) else None
        tl = tls.get(s)
        f = as_of(tl, next_day) if tl else None
        if f is None:
            blocked, why, rmul, npg, pts = True, 'Chưa có BCTC', 0.0, None, {}
        else:
            blocked, why, rmul = risk_gate(s, f)
            npg = f.get('npat_yoy')
            _, p = canslim_score(f, None, 0.0, None, None, None)
            pts = {k: p.get(k, 0) for k in STATIC}
        vs, vc = _s19(V[:, j], i)
        ts, tc = _s19(TV[:, j], i)
        rs_, rc = _s19(rng[:, j], i)
        out[s] = dict(
            thr=float(I['thr'][j]), ref=_f(PC[i, j]),
            vol_s19=vs, vol_c19=vc, tv_s19=ts, tv_c19=tc, rng_s19=rs_, rng_c19=rc,
            hi52_249=_f(np.nanmax(AH[max(0, i - 248):i + 1, j])),
            c250=_f(AC[i - 249, j]) if i >= 249 else None,
            c60=_f(AC[i - 59, j]) if i >= 59 else None,
            shares=_f(MC[i, j] / PC[i, j]) if (MC[i, j] == MC[i, j] and PC[i, j] > 0) else None,
            nbars=int(I['nbars'][i, j]) + 1,
            base=base, blocked=bool(blocked), block_why=(why or None) if blocked else None,
            rmul=float(rmul), npat_yoy=_f(npg), pts_static=pts,
            sector=sect.get(s, 'Khác'), in_topn_prev=bool(x[j] >= cut),
        )
    # vol_s19 above is the 19 sessions ENDING at i: with today appended that is
    # the engine's 20-session window ending at i+1.
    return out, U
