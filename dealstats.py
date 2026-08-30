# -*- coding: utf-8 -*-
"""Gom cac lan thoat tung phan thanh MOT DEAL (giong cach dem 'deal' cua Khoa Nguyen)."""
import numpy as np
from collections import defaultdict


def deals(trades):
    g = defaultdict(list)
    for t in trades:
        g[(t['sym'], t['entry'])].append(t)
    out = []
    for k, ts in g.items():
        pnl_vnd = sum(t['pnl_vnd'] for t in ts)
        w = []
        for t in ts:
            cost = abs(t['pnl_vnd'] / (t['pnl_pct'] / 100)) if t['pnl_pct'] else 0.0
            w.append(cost)
        tot = sum(w) or 1.0
        pct = sum(t['pnl_pct'] * ww for t, ww in zip(ts, w)) / tot
        out.append(dict(sym=k[0], entry=k[1],
                        exit=max(t['exit'] for t in ts),
                        pnl_pct=round(pct, 2), pnl_vnd=pnl_vnd,
                        held=max(t['held'] for t in ts),
                        reason=ts[-1]['reason'], n_exit=len(ts)))
    out.sort(key=lambda x: x['entry'])
    return out


def stats(trades):
    D = deals(trades)
    p = [d['pnl_pct'] for d in D]
    w = [x for x in p if x > 0]
    l = [x for x in p if x <= 0]
    gp = sum(d['pnl_vnd'] for d in D if d['pnl_vnd'] > 0)
    gl = abs(sum(d['pnl_vnd'] for d in D if d['pnl_vnd'] < 0))
    return dict(deals=len(D),
                winrate=round(len(w) / len(p), 4) if p else 0,
                avg_win=round(float(np.mean(w)), 2) if w else 0,
                avg_loss=round(float(np.mean(l)), 2) if l else 0,
                rr=round(abs(np.mean(w) / np.mean(l)), 2) if (w and l) else None,
                pf=round(gp / gl, 2) if gl > 0 else None,
                expectancy=round(float(np.mean(p)), 2) if p else 0)
