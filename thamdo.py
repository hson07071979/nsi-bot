# -*- coding: utf-8 -*-
"""THAM DO HAI THAM SO ANH SON DE NGHI: nen 14% va van T+4.

   Cau hoi KHONG PHAI "cai nao cho backtest dep hon" — bang tren trang da tra loi
   roi. Cau hoi la: "con so dep do co song sot khong khi bi thu that".

   Bon phep thu, theo dung thu tu quan trong:
     1. NOI RONG LUOI QUET  — 18% dang o mep vung phang hay o suon doc? Va 14% co
        that su la dinh, hay chi la diem cuoi cung minh chiu quet toi?
     2. THU KET HOP         — 14% va T+4 chua bao gio duoc chay CUNG NHAU.
     3. WALK-FORWARD        — nam chua dung de thiet ke co con lai khong.
     4. CHIU SOC            — truot gia, bo deal lai nhat, Monte Carlo.
"""
import json, time, sys
import numpy as np
import engine2 as E
from produce2 import PROD

RNG = np.random.default_rng(20260830)


def m(cfg, **ov):
    c = dict(PROD); c.update(cfg or {}); c.update(ov)
    r = E.run(c, log=False)
    return E.metrics(r), r


def gon(x):
    return {k: x.get(k) for k in ('trades', 'total_return', 'cagr', 'maxdd', 'pf', 'sharpe', 'winrate')}


def dong(ten, x, extra=''):
    print(f"  {ten:34s} {x['total_return']:+8.1%}  DD {x['maxdd']:6.2%}  PF {str(x['pf']):>5s}  "
          f"Sharpe {str(x['sharpe']):>4s}  {x['trades']:3d} lenh {extra}", flush=True)


OUT = {}

# ============================================================ 1. NOI RONG LUOI
# Bang tren trang quet 14% -> 20%. Vay 14% la DINH, hay chi la o cuoi cung cua
# bang? Neu quet tiep xuong 10-13% ma van tot len thi day khong phai vung phang —
# day la mot suon doc, va di theo suon doc chi don gian la "it lenh hon thi it
# lenh xau hon", roi ket thuc o mau qua nho de tin.
print('=== 1. NOI RONG LUOI QUET DO RONG NEN (10% -> 24%) ===', flush=True)
nen = []
for b in (0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.20, 0.22, 0.24):
    x, _ = m({}, base_range=b)
    nen.append(dict(v=b, **gon(x)))
    dong(f'nen {b*100:.0f}%', x, '<-- dang chay' if abs(b - 0.18) < 1e-9 else '')
OUT['nen'] = nen

print('\n=== 1b. NOI RONG LUOI QUET VAN THOI GIAN (T+3 -> T+10) ===', flush=True)
van = []
for t in (3, 4, 5, 6, 7, 8, 10):
    x, _ = m({}, t_valve=t)
    van.append(dict(v=t, **gon(x)))
    dong(f'van T+{t}', x, '<-- dang chay' if t == 6 else '')
OUT['van'] = van

# ============================================================ 2. KET HOP
# Hai tham so nay chua bao gio duoc chay CUNG NHAU. Doi rieng tung cai deu tot
# len khong co nghia doi ca hai cung tot len — chung deu tac dong len cung mot
# thu: so lenh duoc phep mo va thoi gian giu lenh xau.
print('\n=== 2. THU KET HOP nen x van (chua tung chay cung nhau) ===', flush=True)
ket = []
for b in (0.14, 0.16, 0.18):
    for t in (4, 5, 6):
        x, _ = m({}, base_range=b, t_valve=t)
        ket.append(dict(nen=b, van=t, **gon(x)))
        dong(f'nen {b*100:.0f}% + T+{t}', x, '<-- dang chay' if (abs(b-0.18) < 1e-9 and t == 6) else '')
OUT['ket_hop'] = ket

# ============================================================ 3. WALK-FORWARD
# Phep thu nghiem khac nhat. Backtest toan ky luon uu ai tham so chat hon, vi no
# duoc nhin thay ca ky. Walk-forward khong cho phep dieu do.
print('\n=== 3. WALK-FORWARD — cham diem tren nam CHUA DUNG de thiet ke ===', flush=True)
UNG_VIEN = [
    ('Dang chay      nen 18% T+6', dict(base_range=0.18, t_valve=6)),
    ('De xuat        nen 14% T+6', dict(base_range=0.14, t_valve=6)),
    ('De xuat        nen 18% T+4', dict(base_range=0.18, t_valve=4)),
    ('De xuat        nen 14% T+4', dict(base_range=0.14, t_valve=4)),
    ('Walk-forward   nen 16% T+6', dict(base_range=0.16, t_valve=6)),
]
NAM = ['2023', '2024', '2025', '2026']
wf = []
for ten, cfg in UNG_VIEN:
    hang = {'ten': ten, 'cfg': cfg, 'nam': []}
    for y in NAM:
        x, _ = m(cfg, start=y + '-01-01', end=y + '-12-31')
        hang['nam'].append(dict(nam=y, **gon(x)))
    duong = sum(1 for z in hang['nam'] if z['total_return'] > 0)
    tong = float(np.prod([1 + z['total_return'] for z in hang['nam']]) - 1)
    nlenh = sum(z['trades'] for z in hang['nam'])
    hang['duong'] = duong; hang['tong_4nam'] = round(tong, 4); hang['n_lenh'] = nlenh
    wf.append(hang)
    print(f"  {ten:30s} {duong}/4 nam lai · gop 4 nam {tong:+7.1%} · {nlenh:3d} lenh · "
          + ' '.join(f"{z['nam']}:{z['total_return']:+6.1%}" for z in hang['nam']), flush=True)
OUT['walk_forward'] = wf

# ============================================================ 4. CHIU SOC
print('\n=== 4. CHIU SOC ===', flush=True)
soc = []
for ten, cfg in UNG_VIEN:
    x0, r0 = m(cfg)
    tr = r0['trades']

    # -- truot gia --
    s = {}
    for sl in (0.002, 0.005, 0.015):
        xs, _ = m(cfg, slip=sl)
        s[f'{sl}'] = gon(xs)
    xa, _ = m(cfg, slip_buy=0.005, slip_sell=0.025)     # trang ben mua

    # -- bo deal lai nhat (giu THU TU THOI GIAN, co vi the hieu chuan) --
    p = np.array([t['pnl_pct'] for t in tr]) / 100.0
    lo, hi = 1e-4, 1.0
    for _ in range(90):
        mid = (lo + hi) / 2
        if float(np.prod(1 + p * mid)) - 1 < x0['total_return']: lo = mid
        else: hi = mid
    f = (lo + hi) / 2

    def dung(ds):
        d = sorted(ds, key=lambda t: (t['exit'], t['entry']))
        nav = 1.0; peak = 1.0; mdd = 0.0
        for t in d:
            nav *= (1 + t['pnl_pct'] / 100 * f); peak = max(peak, nav)
            mdd = max(mdd, 1 - nav / peak)
        q = [t['pnl_pct'] for t in d]
        gp = sum(z for z in q if z > 0); gl = abs(sum(z for z in q if z <= 0))
        return dict(ret=round(nav - 1, 4), pf=round(gp / gl, 2) if gl else None, dd=round(mdd, 4))

    xep = sorted(tr, key=lambda t: -t['pnl_pct'])
    k10 = max(1, int(len(xep) * 0.10))
    bo = dict(bo0=dung(tr), bo3=dung(xep[3:]), bo5=dung(xep[5:]), bo10pc=dung(xep[k10:]), n_bo10=k10)

    # -- Monte Carlo: xao thu tu, doc duoi phai cua phan bo drawdown --
    pp = p * f
    dds = np.empty(3000); streaks = np.empty(3000, dtype=int)
    for i in range(3000):
        rr = pp[RNG.permutation(len(pp))]
        nav = np.cumprod(1 + rr); pk = np.maximum.accumulate(nav)
        dds[i] = float((1 - nav / pk).max())
        best = cur = 0
        for z in (rr <= 0).astype(int):
            cur = cur + 1 if z else 0; best = max(best, cur)
        streaks[i] = best

    soc.append(dict(ten=ten, cfg=cfg, goc=gon(x0), truot=s,
                    trang_ben_mua=gon(xa), bo_winner=bo, frac=round(f, 4),
                    mc=dict(dd_p50=round(float(np.percentile(dds, 50)), 4),
                            dd_p95=round(float(np.percentile(dds, 95)), 4),
                            dd_worst=round(float(dds.max()), 4),
                            streak_p99=int(np.percentile(streaks, 99)),
                            streak_worst=int(streaks.max()))))
    print(f"  {ten:30s} truot1,5% PF {s['0.015']['pf']:>5} · trang-ben-mua PF {str(xa['pf']):>5} · "
          f"bo3 PF {str(bo['bo3']['pf']):>5} · bo10% PF {str(bo['bo10pc']['pf']):>5} · "
          f"MC DD p95 {np.percentile(dds,95):.1%} · chuoi thua p99 {int(np.percentile(streaks,99))}", flush=True)
OUT['chiu_soc'] = soc

json.dump(OUT, open('data/thamdo.json', 'w'), ensure_ascii=False)
print('\nGHI data/thamdo.json', flush=True)
