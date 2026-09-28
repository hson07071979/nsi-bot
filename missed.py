# -*- coding: utf-8 -*-
"""R29 — MISSED-WINNER AUDIT (28/09/2026). CHI DO VA HIEN THI, KHONG PHAI LUAT.

Cau hoi: he dang bo lo winner vi CONG NAO, va cach nguong bao xa?
Voi moi phien tu 2019, lay cac ma "gan no" — moi cong bat buoc (TOP thanh khoan, von hoa,
lich su, GTGD, bien dong) deu dat — roi xep vao nhom:
  SIGNAL      : dat du 8 cong + Cond9 = tin hieu PROD (moc so sanh)
  truot DUNG 1 cong, chia theo cong va khoang cach toi nguong:
    vol   : khoi luong 1,2–2,0x TB20 (4 nac 0,2x)          pct  : bien do thieu 0–1 / 1–2 diem %
    base  : nen 24–28% / 28–32%                           cfo  : CFO 4 quy am (chi CFO chan)
    risk  : cong rui ro khac (ICR, D/E, NPL, CAR)         score: CANSLIM 35–45
    cond9 : du 8 cong, OrdImb 1,2–1,4 / < 1,2 (PROD mua do roi ban T+3)
Loi nhuan phia truoc tinh tu gia dong cua phien tin hieu (khop ATC, da gom phi mua 0,15% va
phi ban 0,25%) toi dong cua T+3 / T+5 / T+10; "chay" = dong cua cao nhat trong 10 phien
>= +10%. Mot ma chi tinh mot lan trong 10 phien cho moi cong (khong dem lap mot dot song).

Khong doc gi cua so ghi tien / von / thu tu uu tien: day la muc TIN HIEU, khong phai deal.
Moc OOS: moi phien tu OOS_FROM tro di la NGOAI MAU (sau khi cac nguong da chot).
"""
import datetime as dt
import numpy as np

OOS_FROM = '2026-09-29'
START = '2019-01-01'
HOR = (3, 5, 10)
COOLDOWN = 10
NEAR = dict(vol_lo=1.2, pct_gap=0.02, base_hi=0.32, score_lo=35.0, oi_lo=1.2)

GROUP_VI = {
    'SIGNAL': 'Tín hiệu PROD (đủ 8 cổng + Cond9)',
    'vol_1.8-2.0': 'Khối lượng 1,8–2,0×', 'vol_1.6-1.8': 'Khối lượng 1,6–1,8×',
    'vol_1.4-1.6': 'Khối lượng 1,4–1,6×', 'vol_1.2-1.4': 'Khối lượng 1,2–1,4×',
    'pct_0-1': 'Biên độ thiếu 0–1 điểm %', 'pct_1-2': 'Biên độ thiếu 1–2 điểm %',
    'base_24-28': 'Nền 24–28%', 'base_28-32': 'Nền 28–32%',
    'cfo': 'CFO 4 quý âm', 'risk': 'Rủi ro khác (ICR, D/E, NPL, CAR)', 'score_35-45': 'CANSLIM 35–45',
    'cond9_1.2-1.4': 'Cond9 1,2–1,4 (lệnh dò bị bán)', 'cond9_<1.2': 'Cond9 < 1,2 (lệnh dò bị bán)',
}
ORDER = list(GROUP_VI)


def _grp(gate, v):
    if gate == 'vol':
        lo = min(1.8, max(1.2, np.floor((v + 1e-9) * 5) / 5))
        return f'vol_{lo:.1f}-{lo + 0.2:.1f}'
    if gate == 'pct': return 'pct_0-1' if v < 0.01 else 'pct_1-2'           # v = so diem thieu
    if gate == 'base': return 'base_24-28' if v <= 0.28 else 'base_28-32'
    if gate == 'score': return 'score_35-45'
    if gate == 'cond9': return 'cond9_1.2-1.4' if v >= 1.2 else 'cond9_<1.2'
    return gate


def events(d, I, tls, C, start=START):
    """Tat ca su kien (SIGNAL + truot dung 1 cong) kem loi nhuan phia truoc."""
    import engine2 as E
    from engine import as_of, risk_gate, canslim_score
    from vn300 import build_topn
    assert not C.get('use_cond8') and not (C.get('dk5_hi', 0) > C.get('dk5_lo', 0)), 'cond8/DK5 bat: cap nhat R29'
    assert C.get('cfo_mode', 'hard') == 'hard'
    E.reset_research_state()
    cal = [str(x) for x in d['cal']]; S = d['sym']
    AC = d['AdjClose']; TV = d['TotalValue']; MC = d['MarketCap']
    base_rng = E.prep_masks(d, I, C)[0]
    from observability import _thr
    thr = _thr(d, I, C)
    TOP = build_topn(I, int(C['top_n']))
    OI = E._oi_arr(d, I, C)
    fb, fs = float(C['fee_buy']), float(C['fee_sell'])
    i0 = next(k for k, c in enumerate(cal) if c >= start)
    N = len(cal); out = []; last = {}
    with np.errstate(invalid='ignore'):
        hard = (TOP & (MC > C['min_mktcap']) & (I['nbars'] >= C['min_history']) & (TV >= C['gtgd_min'])
                & (I['volat20'] >= C['volat_min']) & ~np.isnan(AC))
        TH = thr if thr.ndim == 2 else np.broadcast_to(thr, AC.shape)
        p_ok = I['pct'] >= TH; p_nr = (I['pct'] >= TH - NEAR['pct_gap']) & ~p_ok
        v_ok = I['volr'] >= C['vol_floor']; v_nr = (I['volr'] >= NEAR['vol_lo']) & ~v_ok
        b_ok = base_rng <= C['base_range']; b_nr = (base_rng <= NEAR['base_hi']) & ~b_ok
        pre = hard & (p_ok | p_nr) & (v_ok | v_nr) & (b_ok | b_nr)
        nnear = p_nr.astype(np.int8) + v_nr + b_nr
        pre &= nnear <= 1
    for i in range(i0, N):
        js = np.where(pre[i])[0]
        if not len(js): continue
        day = dt.date.fromisoformat(cal[i])
        for j in js:
            j = int(j); sym = str(S[j])
            tl = tls.get(sym); f = as_of(tl, day) if tl else None
            if f is None: continue
            oi = float(OI[i, j])
            if oi != oi: continue                                         # khong co Cond9 -> khong xep duoc
            fails = []
            if p_nr[i, j]: fails.append(('pct', float(TH[i, j] - I['pct'][i, j])))
            if v_nr[i, j]: fails.append(('vol', float(I['volr'][i, j])))
            if b_nr[i, j]: fails.append(('base', float(base_rng[i, j])))
            blk, why, _ = risk_gate(sym, f)
            if blk: fails.append(('cfo' if str(why).startswith('CFO') else 'risk', None))
            sc, _p = canslim_score(f, I['rs'][i, j], I['mom3'][i, j],
                                   float(AC[i, j] / I['hi52'][i, j] - 1) if I['hi52'][i, j] > 0 else None,
                                   float(I['volr'][i, j]), float(I['tvma20'][i, j]))
            if sc < NEAR['score_lo']: continue
            if sc < C['score_floor']: fails.append(('score', float(sc)))
            if oi < C['ordimb_min']: fails.append(('cond9', oi))
            if len(fails) > 1: continue
            g = 'SIGNAL' if not fails else _grp(*fails[0])
            fam = g.split('_')[0]
            if i - last.get((fam, j), -99) < COOLDOWN: continue
            last[(fam, j)] = i
            e = AC[i, j] * (1 + fb); r = {}
            for h in HOR:
                c = AC[i + h, j] if i + h < N else np.nan
                r[h] = None if c != c else round(float(c * (1 - fs) / e - 1), 4)
            w = AC[i + 1:min(N, i + 11), j]; w = w[~np.isnan(w)]
            pk = round(float(w.max() / e - 1), 4) if len(w) == 10 else None
            out.append(dict(date=cal[i], sym=sym, group=g, t3=r[3], t5=r[5], t10=r[10], peak10=pk,
                            score=round(float(sc), 1), volr=round(float(I['volr'][i, j]), 2), ordimb=round(oi, 2)))
    return out


def _stats(ev):
    o = dict(n=len(ev))
    for h in HOR:
        x = np.array([e[f't{h}'] for e in ev if e[f't{h}'] is not None])
        o[f'n{h}'] = int(len(x))
        o[f'avg{h}'] = round(float(x.mean()), 4) if len(x) else None
    x = np.array([e['t10'] for e in ev if e['t10'] is not None])
    if len(x):
        gp = x[x > 0].sum(); gl = -x[x < 0].sum()
        o.update(med10=round(float(np.median(x)), 4), win10=round(float((x > 0).mean()), 3),
                 pf10=(round(float(gp / gl), 2) if gl > 0 else None))
    pk = np.array([e['peak10'] for e in ev if e['peak10'] is not None])
    o['run10'] = round(float((pk >= 0.10).mean()), 3) if len(pk) else None       # ty le "chay" >= +10% trong 10 phien
    return o


def audit(d, I, tls, C, start=START):
    ev = events(d, I, tls, C, start)
    P = {'all': lambda e: e['date'] < OOS_FROM, '2019-2022': lambda e: e['date'] < '2023-01-01',
         '2023-now': lambda e: '2023-01-01' <= e['date'] < OOS_FROM, 'oos': lambda e: e['date'] >= OOS_FROM}
    tab = {}
    for g in ORDER:
        E_ = [e for e in ev if e['group'] == g]
        tab[g] = {k: _stats([e for e in E_ if f(e)]) for k, f in P.items()}
    recent = sorted([e for e in ev if e['group'] != 'SIGNAL'], key=lambda e: e['date'])[-40:]
    return dict(asof=str(d['cal'][-1]), start=start, oos_from=OOS_FROM, near=NEAR, cooldown=COOLDOWN,
                horizons=list(HOR), groups=ORDER, group_vi=GROUP_VI, table=tab, recent=recent,
                n_events=len(ev), note='CHỈ ĐO — không đổi luật. Mức tín hiệu, không phải deal (bỏ qua vốn, thứ tự ưu tiên).')


if __name__ == '__main__':
    import json, time, engine2 as E
    from produce2 import PROD
    t = time.time(); C = dict(E.CFG); C.update(PROD)
    d, I, tls, sect = E.load()
    A = audit(d, I, tls, C)
    print(f'{A["n_events"]} su kien, {time.time() - t:.0f}s')
    pc = lambda x: '   —  ' if x is None else f'{x * 100:+6.2f}%'
    for per in ('all', '2019-2022', '2023-now'):
        print(f'\n== {per}')
        print(f'{"nhom":34s} {"n":>5s} {"T+3":>8s} {"T+5":>8s} {"T+10":>8s} {"med10":>8s} {"win10":>6s} {"PF10":>5s} {"chay10":>6s}')
        for g in A['groups']:
            s = A['table'][g][per]
            if not s['n']: continue
            print(f'{GROUP_VI[g]:34s} {s["n"]:5d} {pc(s["avg3"]):>8s} {pc(s["avg5"]):>8s} {pc(s["avg10"]):>8s} '
                  f'{pc(s.get("med10")):>8s} {s.get("win10", 0) * 100:5.1f}% {s.get("pf10")!s:>5s} {(s["run10"] or 0) * 100:5.1f}%')
    json.dump(A, open('evidence/r29_missed.json', 'w'), ensure_ascii=False, indent=1)
