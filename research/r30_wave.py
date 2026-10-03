# -*- coding: utf-8 -*-
"""R30 — dung mang nghien cuu cho engine2.EXTRA: song nganh (theme) va dong tien lon thi truong.
Chi dung du lieu toi phien T-1 cho song; R dung TB20 toi phien T-1. Mac dinh engine KHONG doc gi."""
import numpy as np
OIL = {'GAS','PVT','PET','PGD','CNG','PGS','PVP','PGC'}

def theme_of(sym, sect):
    s = sect.get(sym, 'Khác')
    if s == 'Dầu khí' or sym in OIL: return 'OIL_GAS_CHAIN'
    return s

def _roll_mean(a, n):
    c = np.nancumsum(np.nan_to_num(a), axis=0); out = np.full(a.shape, np.nan)
    out[n-1:] = (c[n-1:] - np.vstack([np.zeros((1,)+a.shape[1:]), c[:-n]])) / n
    return out

def build(d, I, sect, br=0.6, rs=0.03, to=1.2, pops=2, top=200, min_tv=5e9):
    AC = d['AdjClose']; TV = np.nan_to_num(d['TotalValue']); N, S = AC.shape
    tv20 = I['tvma20']
    rk = np.argsort(np.argsort(-np.nan_to_num(tv20), axis=1), axis=1) + 1
    mem = (rk <= top) & (np.nan_to_num(tv20) >= min_tv)
    above = AC > I['ma20']
    r25 = np.full(AC.shape, np.nan); r25[25:] = AC[25:] / AC[:-25] - 1
    tv10 = _roll_mean(TV, 10); tv40 = _roll_mean(TV, 40)
    pop = ((I['pct'] >= 0.04) & (I['volr'] >= 1.5)).astype(float)
    mkt = np.nanmean(np.where(mem, r25, np.nan), axis=1)
    themes = np.array([theme_of(str(x), sect) for x in d['sym']])
    on = np.zeros((N, S), dtype=bool); states = {}
    for t in np.unique(themes):
        cols = np.where(themes == t)[0]
        m = mem[:, cols]; n = m.sum(1)
        with np.errstate(invalid='ignore', divide='ignore'):
            b = (above[:, cols] & m).sum(1) / n
            rsv = np.nanmean(np.where(m, r25[:, cols], np.nan), axis=1) - mkt
            tr = np.nansum(np.where(m, tv10[:, cols], 0), 1) / np.nansum(np.where(m, tv40[:, cols], 0), 1)
        p10 = _roll_mean((pop[:, cols] * m).sum(1)[:, None], 10)[:, 0] * 10
        w = (n >= 3) & (b >= br) & (rsv >= rs) & (tr >= to) & (p10 >= pops)
        w = np.nan_to_num(w).astype(bool)
        wl = np.zeros(N, dtype=bool); wl[1:] = w[:-1]          # lui 1 phien: chi biet toi T-1
        on[:, cols] = wl[:, None]; states[t] = wl
    return on, states

def build_liq(d, I, top=150):
    tv20 = np.nan_to_num(I['tvma20'])
    srt = -np.sort(-tv20, axis=1)[:, :top].sum(1)
    N = len(srt); norm = np.full(N, np.nan)
    for i in range(200, N): norm[i] = np.median(srt[max(0, i-249):i+1])
    R = srt / norm
    Rl = np.full(N, np.nan); Rl[1:] = R[:-1]                    # T-1
    return np.nan_to_num(Rl, nan=1.0)

def install(**kw):
    import engine2 as E
    d, I, tls, sect = E.load()
    on, st = build(d, I, sect, **kw)
    E.EXTRA['wave_on'] = on; E.EXTRA['liq'] = build_liq(d, I)
    return on, st
