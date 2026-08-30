# -*- coding: utf-8 -*-
"""BA KHOI DU LIEU CHO TRANG KHACH HANG XEM.

1. monthly()  — luoi loi suat theo thang (bieu do nhiet). Kem ty le ngay CO CAM HANG
                trong thang, de trang ve "cham mo = dung ngoai thi truong".
2. top6m()    — cac deal 6 thang gan nhat, sap theo loi suat giam dan.
3. candles()  — nen OHLC ~260 phien gan nhat cho cac ma dang quan tam, kem diem mua/ban.
"""
from collections import defaultdict
import numpy as np


def monthly(curve, trades):
    """curve: [[date, nav, light, ...], ...]  -> luoi thang."""
    by = defaultdict(list)
    for row in curve:
        by[row[0][:7]].append(row)
    # ngay nao dang cam hang?
    held = set()
    for t in trades:
        held.add((t['sym'], t['entry'], t['exit']))
    span = defaultdict(int)
    for _, a, z in held:
        pass  # dem theo ngay o duoi cho chinh xac

    dates = [r[0] for r in curve]
    inmkt = {d: 0 for d in dates}
    for _, a, z in held:
        for d in dates:
            if a <= d <= z:
                inmkt[d] += 1

    out = []
    prev = None
    for ym in sorted(by):
        rows = by[ym]
        first = rows[0][1] if prev is None else prev
        last = rows[-1][1]
        ret = last / first - 1 if first else 0.0
        days = [r[0] for r in rows]
        frac = sum(1 for d in days if inmkt[d] > 0) / len(days)
        lights = defaultdict(int)
        for r in rows:
            if len(r) > 2:
                lights[r[2]] += 1
        out.append(dict(ym=ym, ret=round(float(ret), 4), inmkt=round(frac, 3),
                        n=len(rows), light=(max(lights, key=lights.get) if lights else None)))
        prev = last
    return out


def top6m(deals, asof, months=6):
    """Cac deal ket thuc trong N thang gan nhat, sap theo loi suat giam dan."""
    y, m, _ = map(int, asof.split('-'))
    m -= months
    while m <= 0:
        m += 12; y -= 1
    frm = f'{y:04d}-{m:02d}-01'
    sel = [d for d in deals if d.get('entry', '') >= frm]
    sel.sort(key=lambda x: -x['pnl_pct'])
    return dict(frm=frm, to=asof, deals=sel)


def candles(d, I, syms, nbar=260, trades=None):
    """Nen OHLC cho tung ma + danh dau diem mua/ban cua bot."""
    S = [str(x) for x in d['sym']]
    cal = [str(x) for x in d['cal']]
    idx = {s: k for k, s in enumerate(S)}
    lo = max(0, len(cal) - nbar)
    marks = defaultdict(list)
    for t in (trades or []):
        marks[t['sym']].append(('B', t['entry'], t.get('entry_px')))
        marks[t['sym']].append(('S', t['exit'], t.get('exit_px')))

    out = {}
    for s in syms:
        j = idx.get(s)
        if j is None:
            continue
        bars = []
        for i in range(lo, len(cal)):
            o, h, l, c = (d['PriceOpen'][i, j], d['PriceHigh'][i, j],
                          d['PriceLow'][i, j], d['PriceClose'][i, j])
            if not (c == c) or c <= 0:
                continue
            v = float(d['Volume'][i, j]) if d['Volume'][i, j] == d['Volume'][i, j] else 0.0
            bars.append([cal[i], round(float(o) / 1000, 2), round(float(h) / 1000, 2),
                         round(float(l) / 1000, 2), round(float(c) / 1000, 2), round(v / 1000)])
        if len(bars) < 30:
            continue
        ma = {}
        cl = np.array([b[4] for b in bars], dtype=float)
        for n in (20, 50):
            if len(cl) >= n:
                k = np.convolve(cl, np.ones(n) / n, mode='valid')
                ma[f'ma{n}'] = [None] * (n - 1) + [round(float(x), 2) for x in k]
        seen = {b[0] for b in bars}
        mk = [dict(t=k, d=dt, px=(round(float(px) / 1000, 2) if px else None))
              for k, dt, px in marks.get(s, []) if dt in seen]
        out[s] = dict(bars=bars, **ma, marks=mk)
    return out
