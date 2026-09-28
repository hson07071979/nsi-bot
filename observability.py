# -*- coding: utf-8 -*-
"""LOP QUAN SAT (R27A, 27/09/2026) — CHI DOC VA HIEN THI. KHONG phai luat giao dich.

Hai thu:
  1. path_block(): "duong di sau breakout" cua mot vi the dang mo (T+1/T+2/T+3/T+5,
     lai hien tai, dinh lai, MFE/MAE, giu tren gia breakout, dinh moi, Cond9) + mot nhan
     MO TA (RUN_FAST / HEALTHY_TREND / STALL / WEAK_BREAKOUT). Nhan chi de doc — engine,
     exit_rules, portfolio.py va chuong Telegram KHONG doc no.
  2. watch78(): danh sach "GAN DAT — thieu dung 1 cong" tai phien cuoi, dung DUNG cac cong
     va nguong PROD (cung cong thuc voi engine2.screen). Khong bao gio la MUA: khong vao
     signals, khong vao so ghi tien, khong vao chuong.

R25 (27/09/2026) da do: Behavior Score / 7-8 + behavior KHONG co edge ngoai mau ben ->
khong dung lam luat. OBS nam NGOAI produce2.PROD nen khong doi prod_config_hash.
"""
import datetime as dt
import numpy as np

OBS = dict(
    show_path=True, show_7of8=True,
    # R29 (28/09/2026): nhan them ma thieu 2 cong mem (6/8) — VD PET 22/09 thieu khoi luong + CFO.
    # 6/8 BAT BUOC gia da no (cong bien do dat), khong thi ma nao nam im cung thanh 6/8.
    max_missing=2, six_needs_pct=True,
    path=dict(run_fast_t3=0.05,        # T+3 dong cua >= +5% so voi gia breakout -> RUN_FAST (R25 dinh nghia run-fast A)
              stall_band=0.02,          # |lai| < 2% sau >= 3 phien ma chua mat breakout -> STALL
              min_days_stall=3),
    note='DIAGNOSTIC ONLY — không dùng trong tín hiệu, cỡ lệnh hay luật thoát',
)

LABEL_VI = {'RUN_FAST': 'CHẠY NHANH', 'HEALTHY_TREND': 'XU HƯỚNG TỐT', 'STALL': 'ĐI NGANG',
            'WEAK_BREAKOUT': 'BREAKOUT YẾU', 'NEW': 'VỪA BREAKOUT'}


def _f(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if x != x else x


def path_block(AC, AH, AL, PX, ei, j, last, fee_buy, cond9=None, obs=OBS):
    """Duong di tu phien breakout ei (= phien mua, khop gia dong cua) toi phien `last`.
    Moi % tinh tren gia DIEU CHINH (AC/AH/AL) nen co tuc/chia tach khong lam sai.
    Thieu du lieu -> None, khong doan."""
    b = _f(AC[ei, j])
    if b is None or b <= 0 or last < ei:
        return None
    cost = b * (1 + fee_buy)
    closes = [(_f(AC[k, j])) for k in range(ei, last + 1)]
    def ret(h):
        k = ei + h
        if k > last: return None
        c = _f(AC[k, j]); return None if c is None else round(c / b - 1, 4)
    now = closes[-1]
    after = [c for c in closes[1:] if c is not None]
    hi = [_f(AH[k, j]) for k in range(ei + 1, last + 1)]; lo = [_f(AL[k, j]) for k in range(ei + 1, last + 1)]
    hi = [x for x in hi if x is not None]; lo = [x for x in lo if x is not None]
    valid = [(k, c) for k, c in enumerate(closes) if c is not None]
    kmax = max(valid, key=lambda t: (t[1], t[0]))[0] if valid else None
    o = dict(breakout_date=None, breakout_price=round(float(PX[ei, j]), 2) if _f(PX[ei, j]) else None,
             breakout_adj=round(b, 4), entry_price=round(float(PX[ei, j]) * (1 + fee_buy), 2) if _f(PX[ei, j]) else None,
             days_since_breakout=int(last - ei),
             ret_t1=ret(1), ret_t2=ret(2), ret_t3=ret(3), ret_t5=ret(5),
             gain_now=(round(now / cost - 1, 4) if now is not None else None),
             peak_gain=(round(max(c for _, c in valid) / cost - 1, 4) if valid else None),
             mfe_since_entry=(round(max(hi) / cost - 1, 4) if hi else None),
             mae_since_entry=(round(min(lo) / cost - 1, 4) if lo else None),
             above_breakout_close=(bool(now >= b) if now is not None else None),
             new_high_since_breakout=(bool(max(after) > b) if after else None),
             days_since_last_high=(int(len(closes) - 1 - kmax) if kmax is not None else None),
             cond9_confirmed=cond9)
    o['diagnostic_label'] = label(o, obs)
    o['diagnostic_label_vi'] = LABEL_VI.get(o['diagnostic_label'])
    o['diagnostic_only'] = True
    return o


def label(o, obs=OBS):
    """Nhan MO TA don gian (nguong o OBS['path']). KHONG phai luat."""
    P = obs['path']
    if o['days_since_breakout'] == 0: return 'NEW'
    if o['above_breakout_close'] is False: return 'WEAK_BREAKOUT'
    t3 = o['ret_t3']
    if (t3 is not None and t3 >= P['run_fast_t3']) or (t3 is None and (o['gain_now'] or 0) >= P['run_fast_t3']):
        return 'RUN_FAST'
    if o['days_since_breakout'] >= P['min_days_stall'] and o['gain_now'] is not None and abs(o['gain_now']) < P['stall_band']:
        return 'STALL'
    return 'HEALTHY_TREND'


# ------------------------------------------------------------------------- 7/8
GATE_VI = {'uni': 'Trong TOP {top_n} thanh khoản', 'pct': 'Biên độ tăng giá', 'vol': 'Khối lượng ≥ {vol_floor}× TB20',
           'gtgd': 'GTGD phiên ≥ {gtgd_bn} tỷ', 'volat': 'Biến động TB20 ≥ {volat_pct}%', 'base': 'Nền giá ≤ {base_pct}%',
           'risk': 'Cổng rủi ro (CFO, ICR, NPL, CAR)', 'score': 'Điểm CANSLIM ≥ {score_floor}'}
GATES = ('uni', 'pct', 'vol', 'gtgd', 'volat', 'base', 'risk', 'score')
SOFT = ('pct', 'vol', 'volat', 'base', 'risk')     # cong duoc phep la cong DUY NHAT con thieu
# uni/gtgd (thanh khoan), score (CANSLIM phai dat san), von hoa / lich su / du lieu -> bat buoc


def _thr(d, I, C):
    import engine2 as E
    t = (I['thr_hard'] if C['hard_ceiling'] else I['thr'])
    if C.get('trig_pct') is not None: t = np.full_like(t, float(C['trig_pct']))
    return E._trig_thr(d, t, C)


def watch78(d, I, tls, sect, C, i, held=(), today_signals=()):
    """Danh sach GAN DAT tai phien i. Tra ve (near, stats). Moi phan tu co du 8 cong
    (pass, actual, threshold, gap) + Cond9 rieng. Khong co ma nao da la tin hieu / dang cam."""
    import engine2 as E
    from engine import as_of, risk_gate, canslim_score
    from vn300 import build_topn
    assert not C.get('use_cond8') and not (C.get('dk5_hi', 0) > C.get('dk5_lo', 0)), 'cond8/DK5 bat: cap nhat GATES'
    S = d['sym']; AC = d['AdjClose']; TV = d['TotalValue']; MC = d['MarketCap']
    day = dt.date.fromisoformat(str(d['cal'][i]))
    base_rng = E.prep_masks(d, I, C)[0]
    thr = _thr(d, I, C)
    TOP = build_topn(I, int(C['top_n']))
    x = np.where(np.isnan(I['tvma20'][i]), -1.0, I['tvma20'][i]); order = np.argsort(-x)
    rank = np.empty(len(x), dtype=int); rank[order] = np.arange(1, len(x) + 1)
    OI = E._oi_arr(d, I, C)
    out = []; stats = dict(invalid=0, full=0, near=0, near7=0, near6=0)
    for j in range(len(S)):
        sym = str(S[j])
        if sym in held or sym in today_signals: continue
        # dieu kien tien quyet: du lieu phien i, von hoa, lich su — thieu -> DATA INVALID, khong xet
        if not (AC[i, j] == AC[i, j]) or not (MC[i, j] > C['min_mktcap']) or not (I['nbars'][i, j] >= C['min_history']):
            continue
        g = {}
        g['uni'] = (bool(TOP[i, j]), int(rank[j]), int(C['top_n']))
        th_ = thr[i, j] if thr.ndim == 2 else thr[j]
        g['pct'] = (bool(I['pct'][i, j] >= th_), _f(I['pct'][i, j]), _f(th_))
        g['vol'] = (bool(I['volr'][i, j] >= C['vol_floor']), _f(I['volr'][i, j]), float(C['vol_floor']))
        g['gtgd'] = (bool(TV[i, j] >= C['gtgd_min']), _f(TV[i, j]), float(C['gtgd_min']))
        g['volat'] = (bool(I['volat20'][i, j] >= C['volat_min']), _f(I['volat20'][i, j]), float(C['volat_min']))
        g['base'] = (bool(base_rng[i, j] <= C['base_range']), _f(base_rng[i, j]), float(C['base_range']))
        if any(v[1] is None for k, v in g.items() if k != 'uni'):
            continue                                                   # thieu so -> DATA INVALID
        fails = [k for k, v in g.items() if not v[0]]
        if len(fails) > OBS['max_missing']: continue                   # qua nhieu cong ky thuat truot -> khong gan dat
        tl = tls.get(sym); f = as_of(tl, day) if tl else None
        if f is None: stats['invalid'] += 1; continue                  # khong co BCTC
        blk, why, rmul = risk_gate(sym, f)
        cfo_only = bool(blk and str(why).startswith('CFO'))
        if blk and not cfo_only: stats['invalid'] += 1; continue       # rui ro cung -> RISK INVALID
        g['risk'] = (not blk, _f(f.get('cfo_ttm')), 0.0 if cfo_only else None)   # CFO luon hien (ke ca khi qua)
        sc, pts = canslim_score(f, I['rs'][i, j], I['mom3'][i, j],
                                float(AC[i, j] / I['hi52'][i, j] - 1) if I['hi52'][i, j] > 0 else None,
                                float(I['volr'][i, j]), float(I['tvma20'][i, j]))
        g['score'] = (bool(sc >= C['score_floor']), round(float(sc), 1), float(C['score_floor']))
        fails = [k for k in GATES if not g[k][0]]
        oi = _f(OI[i, j]); c9 = (None if oi is None else bool(oi >= C['ordimb_min']))
        if not g['score'][0]: continue                                 # CANSLIM phai dat san
        if len(fails) == 0:
            if c9 is False:     # du 8 cong nhung truot Cond9: hien rieng, canh bao
                stats['full'] += 1
                out.append(_rec(sym, sect, g, [], c9, oi, C, rank[j], f, kind='COND9_FAIL'))
            continue
        if not (1 <= len(fails) <= OBS['max_missing']) or any(k not in SOFT for k in fails): continue
        if len(fails) == 2 and OBS['six_needs_pct'] and 'pct' in fails: continue   # 6/8 phai la ma DA NO gia
        stats['near'] += 1; stats['near%d' % (8 - len(fails))] = stats.get('near%d' % (8 - len(fails)), 0) + 1
        out.append(_rec(sym, sect, g, fails, c9, oi, C, rank[j], f, kind='NEAR'))
    out.sort(key=lambda r: (r['kind'] != 'NEAR', -r['passed'], -r['score']))
    return out, stats


def _rec(sym, sect, g, fails, c9, oi, C, rk, f, kind):
    gates = []
    for k in GATES:
        ok, act, th = g[k]
        if k == 'uni': gap = (th - act) if act is not None else None                       # hang: con cach bao nhieu bac
        elif k == 'base': gap = (th - act) if act is not None else None                    # <= nguong
        elif k == 'risk': gap = act if (not ok and act is not None) else None              # CFO am bao nhieu
        if k == 'risk' and ok: th = None                                                   # qua cong: khong co nguong de so
        else: gap = (act - th) if (act is not None and th is not None) else None           # >= nguong
        gates.append(dict(gate=k, ok=bool(ok), actual=act, threshold=th, gap=gap))
    m = fails[0] if fails else None
    return dict(symbol=sym, sector=sect.get(sym, 'Khác'), kind=kind, score=g['score'][1], passed=8 - len(fails), total=8,
                missing_gate=m, missing_gates=list(fails), gates=gates, cond9=c9, ordimb=(round(oi, 3) if oi is not None else None),
                ordimb_min=float(C['ordimb_min']), liquidity_rank=int(rk), period=f.get('label'),
                status='WATCH_ONLY', status_vi='GẦN ĐẠT — KHÔNG PHẢI MUA')
