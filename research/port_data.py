# -*- coding: utf-8 -*-
"""Dữ liệu cho nghiên cứu Lọc port (R38 giải ngân, R39 định giá) — không nhìn trước.

Giá: data/fa.npz (FireAnt, giá điều chỉnh 2017→nay, HOSE + HNX).
BCTC: data/funda_raw2.json qua prep.parse_funda (mỗi quý có ngày `avail` = phiên được phép dùng).
Mỗi chỉ tiêu cơ bản ở phiên i chỉ dùng các quý có avail <= ngày i.

Trả về dict:
  cal, sym, C (AdjClose), O (AdjOpen), H, L, TV (GTGD), MC (vốn hóa),
  vni (VN-Index khớp lịch), np_ttm, np_ttm_yoy, rev_ttm_yoy, roe, pe, pb, pe_rel, pb_rel
  (pe_rel = P/E ÷ trung vị P/E 750 phiên trước đó của chính mã, chỉ khi P/E > 0)
"""
from __future__ import annotations

import json
import os
import sys
import datetime as dt

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

_CACHE = {}


def _ffill(a):
    a = a.copy()
    for j in range(a.shape[1]):
        col = a[:, j]
        m = ~np.isnan(col)
        if not m.any():
            continue
        idx = np.where(m, np.arange(len(col)), 0)
        np.maximum.accumulate(idx, out=idx)
        out = col[idx]
        out[: np.argmax(m)] = np.nan
        a[:, j] = out
    return a


def _roll_median_past(x, win=750, step=5, minn=120):
    """Trung vị của `win` phiên TRƯỚC (không gồm phiên hiện tại), tính mỗi `step` phiên rồi giữ."""
    N, M = x.shape
    out = np.full((N, M), np.nan, dtype=np.float32)
    last = None
    for i in range(N):
        if i % step == 0 or last is None:
            a = x[max(0, i - win):i]
            with np.errstate(all='ignore'):
                cnt = np.sum(~np.isnan(a), axis=0)
                med = np.nanmedian(a, axis=0) if len(a) else np.full(M, np.nan)
            med = np.where(cnt >= minn, med, np.nan)
            last = med
        out[i] = last
    return out


def load(force=False):
    if 'd' in _CACHE and not force:
        return _CACHE['d']
    cache = os.path.join(ROOT, 'data', 'port_research.npz')
    if os.path.exists(cache) and not force:
        z = np.load(cache, allow_pickle=True)
        d = {k: z[k] for k in z.files}
        _CACHE['d'] = d
        return d
    import fa_prep
    from prep import parse_funda
    fa = fa_prep.build()
    cal = [str(x) for x in fa['cal']]
    sym = [str(x) for x in fa['sym']]
    N, M = len(cal), len(sym)
    C = fa['AdjClose'].astype(np.float32)
    MC = _ffill(fa['MarketCap'].astype(np.float32))
    # VN-Index khớp lịch
    v = json.load(open('data/VNINDEX.json'))
    vd = {dt.datetime.utcfromtimestamp(t).date().isoformat(): c for t, c in zip(v['t'], v['c'])}
    vni = np.array([vd.get(d, np.nan) for d in cal], dtype=np.float64)
    vni = _ffill(vni[:, None])[:, 0]
    # BCTC theo ngày avail
    fu = parse_funda('data/funda_raw2.json')
    np_ttm = np.full((N, M), np.nan, dtype=np.float32)
    np_yoy = np.full((N, M), np.nan, dtype=np.float32)
    rv_yoy = np.full((N, M), np.nan, dtype=np.float32)
    roe = np.full((N, M), np.nan, dtype=np.float32)
    pbq = np.full((N, M), np.nan, dtype=np.float32)      # P/B tại quý (giá cuối quý) + vốn hóa cuối quý
    mcq = np.full((N, M), np.nan, dtype=np.float32)
    cal_d = np.array([dt.date.fromisoformat(x) for x in cal])
    for j, s in enumerate(sym):
        rows = fu.get(s) or []
        if len(rows) < 4:
            continue
        for k, r in enumerate(rows):
            w = rows[max(0, k - 3):k + 1]
            npw = [x.get('npat') for x in w]
            if len(w) == 4 and all(isinstance(x, (int, float)) for x in npw):
                ttm = float(sum(npw))
            else:
                ttm = np.nan
            w0 = rows[max(0, k - 7):max(0, k - 3)]
            np0 = [x.get('npat') for x in w0]
            ttm0 = float(sum(np0)) if len(w0) == 4 and all(isinstance(x, (int, float)) for x in np0) else np.nan
            rvw = [x.get('rev') for x in w]
            rv0 = [x.get('rev') for x in w0]
            rttm = float(sum(rvw)) if len(w) == 4 and all(isinstance(x, (int, float)) for x in rvw) else np.nan
            rttm0 = float(sum(rv0)) if len(w0) == 4 and all(isinstance(x, (int, float)) for x in rv0) else np.nan
            a = r['avail'] if isinstance(r['avail'], dt.date) else dt.date.fromisoformat(str(r['avail'])[:10])
            i0 = int(np.searchsorted(cal_d, a))
            if i0 >= N:
                continue
            np_ttm[i0, j] = ttm
            np_yoy[i0, j] = (ttm / ttm0 - 1) if (ttm0 and ttm0 > 0 and not np.isnan(ttm)) else np.nan
            rv_yoy[i0, j] = (rttm / rttm0 - 1) if (rttm0 and rttm0 > 0 and not np.isnan(rttm)) else np.nan
            if isinstance(r.get('roe'), (int, float)):
                roe[i0, j] = r['roe'] * (100 if abs(r['roe']) < 2 else 1)
            if isinstance(r.get('pb'), (int, float)) and r['pb'] > 0:
                pbq[i0, j] = r['pb']
                mcq[i0, j] = r['marketCap'] if isinstance(r.get('marketCap'), (int, float)) else np.nan
    np_ttm, np_yoy, rv_yoy, roe = (_ffill(x) for x in (np_ttm, np_yoy, rv_yoy, roe))
    pbq, mcq = _ffill(pbq), _ffill(mcq)
    with np.errstate(all='ignore'):
        pe = np.where(np_ttm > 0, MC / np_ttm, np.nan).astype(np.float32)
        pb = np.where((pbq > 0) & (mcq > 0), pbq * MC / mcq, np.nan).astype(np.float32)
    pe = np.where((pe > 0) & (pe < 300), pe, np.nan).astype(np.float32)
    pb = np.where((pb > 0) & (pb < 60), pb, np.nan).astype(np.float32)
    pe_med = _roll_median_past(pe)
    pb_med = _roll_median_past(pb)
    with np.errstate(all='ignore'):
        pe_rel = (pe / pe_med).astype(np.float32)
        pb_rel = (pb / pb_med).astype(np.float32)
    d = dict(cal=np.array(cal), sym=np.array(sym), exch=fa['exch'],
             C=C, O=fa['AdjOpen'].astype(np.float32), H=fa['AdjHigh'].astype(np.float32),
             L=fa['AdjLow'].astype(np.float32), TV=fa['TotalValue'].astype(np.float32), MC=MC,
             vni=vni, np_ttm=np_ttm, np_ttm_yoy=np_yoy, rev_ttm_yoy=rv_yoy, roe=roe,
             pe=pe, pb=pb, pe_rel=pe_rel, pb_rel=pb_rel)
    np.savez_compressed(cache, **d)
    _CACHE['d'] = d
    return d


def roll_max(x, n):
    """Cực đại n phiên gần nhất (gồm phiên hiện tại), theo cột; NaN bỏ qua."""
    N = x.shape[0]
    out = np.full_like(x, np.nan)
    for i in range(N):
        with np.errstate(all='ignore'):
            out[i] = np.nanmax(x[max(0, i - n + 1):i + 1], axis=0)
    return out


def roll_min(x, n):
    N = x.shape[0]
    out = np.full_like(x, np.nan)
    for i in range(N):
        with np.errstate(all='ignore'):
            out[i] = np.nanmin(x[max(0, i - n + 1):i + 1], axis=0)
    return out


def roll_mean(x, n):
    c = np.nancumsum(np.nan_to_num(x), axis=0)
    k = np.cumsum(~np.isnan(x), axis=0)
    out = np.full_like(x, np.nan, dtype=np.float64)
    out[n:] = (c[n:] - c[:-n]) / np.maximum(k[n:] - k[:-n], 1)
    out[:n] = np.nan
    return out


if __name__ == '__main__':
    d = load(force=True)
    s = list(d['sym'])
    for t in ('FPT', 'HPG', 'MWG', 'VCB'):
        j = s.index(t)
        print(t, d['cal'][-1], 'giá', d['C'][-1, j], 'P/E', d['pe'][-1, j], 'P/E rel', d['pe_rel'][-1, j],
              'P/B', d['pb'][-1, j], 'ROE', d['roe'][-1, j], 'LN TTM yoy', d['np_ttm_yoy'][-1, j])
