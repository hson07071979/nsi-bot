# -*- coding: utf-8 -*-
"""Export the per-symbol history the live scanner needs to reproduce
engine2.screen() for the NEXT session (see signal_spec.py, SPEC v3).

export(d, I, tls, sect, C, i, next_day) -> (syms, U)
  i        : index of the last CLOSED session (the spec is for session i+1)
  next_day : datetime.date of session i+1 (fundamentals as_of that day,
             exactly like the engine does on the signal day)

U['xs'] is the session cross-section the engine ranks on at i+1 (RS / Momentum
percentiles, TOP-N by 20-day GTGD): EVERY symbol of the engine universe that can
have a valid r12, r3 or tvma20 at i+1, with the history those need. The live
layer adds each symbol's session row and recomputes the cross-section exactly
(signal_spec.cross_section) instead of ranking against yesterday's lists.
"""
import datetime as dt
import numpy as np
from engine import risk_gate, canslim_score, as_of
import signal_spec as SP

STATIC = ('C1', 'C2', 'C3', 'A1', 'A2')


def _s19(a, i):
    """(running sum, count) of the n-1 sessions ENDING at i, accumulated exactly like
    fa_ind.sma_seq (float64, oldest -> newest, NaN skipped): with the session value
    added it is the engine's 20-session window ending at i+1."""
    w = a[max(0, i - (SP.MEAN_N - 2)):i + 1]
    return SP.window_sum([float(x) for x in w])


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
    rng = (AH - AL) / np.where(AC > 0, AC, np.nan)          # == fa_ind.indicators
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
    # ---- session cross-section of i+1 (signal_spec.cross_section) ----
    xs = {}
    for j, s in enumerate(S):
        c250 = _f(AC[i - 249, j]) if i >= 249 else None      # r12[i+1] = AC[i+1] / AC[i-249] - 1
        c60 = _f(AC[i - 59, j]) if i >= 59 else None          # r3[i+1]  = AC[i+1] / AC[i-59]  - 1
        ts, tc = _s19(TV[:, j], i)
        # tvma20[i+1] needs >= 16 of 20 values -> >= 15 of the previous 19
        if c250 is None and c60 is None and tc < SP.MEAN_NEED - 1:
            continue
        xs[s] = [c250, c60, ts, tc]
    U = dict(topn_cut=cut, top_n=top_n, spec_version=SP.SPEC_VERSION, xs=xs)
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
            # engine2.screen: khong co BCTC -> `continue` truoc canslim_score: KHONG co diem
            blocked, why, rmul, npg, pts = True, 'Chưa có BCTC', 0.0, None, None
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
            nbars_prev=int(I['nbars'][i, j]), nbars=int(I['nbars'][i, j]) + 1,
            base=base, blocked=bool(blocked), block_why=(why or None) if blocked else None,
            rmul=float(rmul), npat_yoy=_f(npg), pts_static=pts or {}, funda=pts is not None,
            sector=sect.get(s, 'Khác'), in_topn_prev=bool(x[j] >= cut),
        )
    return out, U
