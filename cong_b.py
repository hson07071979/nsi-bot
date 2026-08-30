# -*- coding: utf-8 -*-
"""CONG B — "Backtest co trade duoc ngoai doi khong?"

   Ba cau hoi ma bo kiem dinh cu KHONG tra loi, va la ba cau nang nhat:

   B1. THIEN LECH KHOP GIA DONG CUA.
       Tin hieu dung gia dong cua, gia cao nhat, gia thap nhat va khoi luong CA
       PHIEN — roi mua o CHINH gia dong cua do. Nhung bon so ay chi biet duoc SAU
       khi phien dong. Ngoai doi, luc 14h25 anh Son chua biet khoi luong cuoi phien
       la bao nhieu. Day khong phai truot gia; day la BIET TRUOC.

   B2. KHONG KHOP DUOC LENH.
       He nay mua co phieu cham tran. Tran trang ben ban thi khong co ai ban cho
       ma mua. Truot gia 2,5% khong mo phong duoc chuyen "khong mua duoc dong nao".

   B3. SUC CHUA VON.
       GTGD >= 15 ty la nguong cho MOT ma. Voi NAV 1 ty thi 42% = 420 trieu, chiem
       2,8% GTGD — khop duoc. Voi NAV 50 ty thi 21 ty tren mot ma co GTGD 15 ty:
       khong the.

   Chay: python3 cong_b.py   ->  data/cong_b.json
"""
import json, time
import numpy as np
import engine2 as E
from produce2 import PROD

RNG = np.random.default_rng(20260830)
OUT = {}


def gon(x):
    return {k: x.get(k) for k in ('trades', 'total_return', 'cagr', 'maxdd', 'pf', 'sharpe', 'winrate')}


def chay(**ov):
    c = dict(PROD); c.update(ov)
    r = E.run(c, log=False)
    return E.metrics(r), r


def dong(t, x, extra=''):
    print(f"  {t:44s} {x['total_return']:+8.1%}  DD {x['maxdd']:6.2%}  PF {str(x['pf']):>5s}  "
          f"{x['trades']:3d} lenh {extra}", flush=True)


# ══════════════════════════════════════════ B1. KHOP GIA DONG CUA
print('=' * 74)
print('B1 — THIEN LECH KHOP GIA DONG CUA (chay lai duoi CAU HINH DANG CHAY)')
print('=' * 74)
print('  Ban cu chay thi nghiem nay duoi cau hinh KHAC (215 lenh) nen khong so duoc.')
print('  Day la ban chay lai dung PROD hom nay.\n')
b1 = []
for ten, ov in [
    ('Dong cua phien tin hieu (dang gia dinh)', dict(entry_mode='close')),
    ('Mo cua phien sau',                        dict(entry_mode='next_open')),
    ('Binh quan gia quyen phien sau (VWAP)',    dict(entry_mode='next_vwap')),
]:
    x, _ = chay(**ov)
    b1.append(dict(ten=ten, **gon(x)))
    dong(ten, x)
# them: co truot gia 0,2% de sat thuc te hon
b1b = []
for ten, ov in [
    ('Dong cua + truot 0,2%',  dict(entry_mode='close', slip=0.002)),
    ('Mo cua phien sau + truot 0,2%', dict(entry_mode='next_open', slip=0.002)),
    ('VWAP phien sau + truot 0,2%',   dict(entry_mode='next_vwap', slip=0.002)),
]:
    x, _ = chay(**ov)
    b1b.append(dict(ten=ten, **gon(x)))
    dong(ten, x)
OUT['b1_khop_lenh'] = dict(khong_truot=b1, co_truot=b1b)

# ══════════════════════════════════════════ B2. KHONG KHOP DUOC
print()
print('=' * 74)
print('B2 — KHONG KHOP DUOC LENH (tran trang ben ban)')
print('=' * 74)
m0, r0 = chay()
d, I = r0['d'], r0['I']
cal = list(map(str, d['cal']))
idx_ngay = {t: i for i, t in enumerate(cal)}
idx_ma = {str(s): j for j, s in enumerate(d['sym'])}
PX, PB = d['PriceClose'], d['PriceBasic']
V, TV = d['Volume'], d['TotalValue']

# Voi tung deal, kiem PHIEN VAO LENH: gia dong cua co bang gia tran khong,
# va khoi luong phien do co be bat thuong khong (dau hieu trang ben ban).
tran_cung = 0
mong = 0
chi_tiet = []
for t in r0['trades']:
    i = idx_ngay.get(t['entry']); j = idx_ma.get(t['sym'])
    if i is None or j is None: continue
    px, pb = PX[i, j], PB[i, j]
    if not (px and pb) or np.isnan(px) or np.isnan(pb): continue
    pct = px / pb - 1
    tran = pct >= 0.067                       # cham tran HOSE (7%) hoac gan
    vr = float(I['volr'][i, j]) if not np.isnan(I['volr'][i, j]) else 0
    if tran:
        tran_cung += 1
        # tran ma khoi luong chi ~2x TB20 -> ben ban rut, kha nang khong khop het
        if vr < 3.0:
            mong += 1
            chi_tiet.append(dict(sym=t['sym'], ngay=t['entry'], pct=round(pct * 100, 2),
                                 volr=round(vr, 2), pnl=t['pnl_pct']))
n = len(r0['trades'])
print(f"  {n} lenh · {tran_cung} lenh vao dung phien CHAM TRAN ({tran_cung/n:.0%})")
print(f"  trong do {mong} lenh co khoi luong < 3x TB20 — kha nang khong khop du ({mong/n:.0%})")

# Mo phong: mot ty le X% so lenh cham tran KHONG khop duoc -> bo han lenh do.
# Khong phai truot gia, ma la MAT LUON co hoi.
print('\n  Mo phong bo lenh khong khop duoc (2.000 lan moi muc):')
b2 = []
p = np.array([t['pnl_pct'] for t in r0['trades']]) / 100.0
la_tran = np.zeros(n, dtype=bool)
for k, t in enumerate(r0['trades']):
    i = idx_ngay.get(t['entry']); j = idx_ma.get(t['sym'])
    if i is None or j is None: continue
    px, pb = PX[i, j], PB[i, j]
    if px and pb and not np.isnan(px) and not np.isnan(pb) and px / pb - 1 >= 0.067:
        la_tran[k] = True
# hieu chuan co vi the de duong von dung lai khop backtest that
lo, hi = 1e-4, 1.0
for _ in range(90):
    mid = (lo + hi) / 2
    if float(np.prod(1 + p * mid)) - 1 < m0['total_return']: lo = mid
    else: hi = mid
f = (lo + hi) / 2
for ty in (0.10, 0.25, 0.50, 1.00):
    ends = np.empty(2000)
    for s in range(2000):
        giu = np.ones(n, dtype=bool)
        ct = np.where(la_tran)[0]
        if len(ct):
            bo = RNG.choice(ct, size=int(len(ct) * ty), replace=False)
            giu[bo] = False
        ends[s] = float(np.prod(1 + p[giu] * f)) - 1
    b2.append(dict(ty_le=ty, n_bo=int(la_tran.sum() * ty),
                   p50=round(float(np.percentile(ends, 50)), 4),
                   p5=round(float(np.percentile(ends, 5)), 4)))
    print(f"    bo {ty:4.0%} so lenh cham tran ({int(la_tran.sum()*ty):3d} lenh) -> "
          f"loi nhuan trung vi {np.percentile(ends,50):+7.1%}  (p5 {np.percentile(ends,5):+7.1%})")
OUT['b2_khong_khop'] = dict(n_lenh=n, n_cham_tran=int(tran_cung), n_mong=int(mong),
                            goc=round(m0['total_return'], 4), kich_ban=b2,
                            vi_du=chi_tiet[:15])

# ══════════════════════════════════════════ B3. SUC CHUA VON
print()
print('=' * 74)
print('B3 — SUC CHUA VON (mot lenh chiem bao nhieu % GTGD phien do)')
print('=' * 74)
gtgd = []
for t in r0['trades']:
    i = idx_ngay.get(t['entry']); j = idx_ma.get(t['sym'])
    if i is None or j is None: continue
    tv = TV[i, j]
    if tv and not np.isnan(tv) and tv > 0: gtgd.append(float(tv))
gtgd = np.array(gtgd)
print(f"  GTGD phien vao lenh: trung vi {np.median(gtgd)/1e9:.0f} ty · "
      f"p25 {np.percentile(gtgd,25)/1e9:.0f} ty · p10 {np.percentile(gtgd,10)/1e9:.0f} ty")
b3 = []
for nav in (1e9, 5e9, 10e9, 50e9, 100e9, 500e9):
    lenh = nav * PROD['base_size']                 # 42% NAV moi lenh
    ty = lenh / gtgd
    # nguyen tac thi truong: mot lenh vuot 10% GTGD phien la bat dau day gia
    qua = float((ty > 0.10).mean())
    b3.append(dict(nav=nav, lenh=lenh, ty_tb=round(float(np.median(ty)), 4),
                   pct_qua_10=round(qua, 4)))
    print(f"  NAV {nav/1e9:6.0f} ty -> moi lenh {lenh/1e9:6.1f} ty = {np.median(ty):6.1%} GTGD (trung vi) · "
          f"{qua:5.1%} so lenh vuot 10% GTGD")
OUT['b3_suc_chua'] = dict(gtgd_trungvi=float(np.median(gtgd)), bang=b3)

def _sach(o):
    """numpy float32/int64 khong ghi thang ra JSON duoc — doi het ve kieu Python."""
    if isinstance(o, dict):  return {k: _sach(v) for k, v in o.items()}
    if isinstance(o, list):  return [_sach(v) for v in o]
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (np.integer,)):  return int(o)
    if isinstance(o, (np.bool_,)):    return bool(o)
    return o

json.dump(_sach(OUT), open('data/cong_b.json', 'w'), ensure_ascii=False)
print('\nGHI data/cong_b.json')
