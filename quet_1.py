# -*- coding: utf-8 -*-
"""GIAI DOAN 1 — quet TUNG can gat mot, doi voi ban dang chay.
   Muc tieu: xem can gat nao thuc su tao them tin hieu, va gia phai tra la gi.
   KHONG dung de chot — chot phai qua giai doan 3 (ngoai mau)."""
import json, numpy as np, engine2 as E
from produce2 import PROD

def chay(ten, ghi_de):
    c = dict(PROD); c.update(ghi_de)
    r = E.run(c, log=False); m = E.metrics(r)
    deal = len({(t['sym'], t['entry']) for t in r['trades']})
    d = dict(ten=ten, **{k: (float(v) if isinstance(v, (np.floating, np.integer)) else v)
                         for k, v in m.items()}, deal=deal)
    print(f"{ten:44s} {m['total_return']*100:8.1f}%  DD {m['maxdd']*100:5.2f}%  PF {m['pf']:5.2f}  "
          f"Sharpe {m['sharpe']:4.2f}  lenh {m['trades']:3d}  deal {deal:3d}  "
          f"thang {m['winrate']*100:4.1f}%", flush=True)
    return d

KQ = [chay('0. DANG CHAY (nen)', {})]

print('\n--- A. NOI VU TRU: TOP thanh khoan ---', flush=True)
for n in (120, 140, 160, 180, 200, 250, 300):
    KQ.append(chay(f'A. top_n = {n}', dict(top_n=n)))
KQ.append(chay('A. bo han TOP (ca thi truong)', dict(use_top_liquid=False)))

print('\n--- B. NOI NEN GIA ---', flush=True)
for b in (0.20, 0.22, 0.25, 0.30):
    KQ.append(chay(f'B. base_range = {int(b*100)}%', dict(base_range=b)))

print('\n--- C. HA SAN DIEM ---', flush=True)
for s in (40, 42, 35):
    KQ.append(chay(f'C. score_floor = {s}', dict(score_floor=s)))

print('\n--- D. NOI NGUONG DONG TIEN ---', flush=True)
for o in (1.10, 1.00):
    KQ.append(chay(f'D. ordimb_min = {o:.2f}', dict(ordimb_min=o)))
KQ.append(chay('D. tat han cong dong tien', dict(use_ordimb=False)))

print('\n--- E. HA SAN VON HOA / THANH KHOAN ---', flush=True)
KQ.append(chay('E. min_mktcap 1000 -> 500 ty', dict(min_mktcap=500e9)))
KQ.append(chay('E. gtgd_min 15 -> 8 ty', dict(gtgd_min=8e9)))
KQ.append(chay('E. vol_floor 2,0 -> 1,8', dict(vol_floor=1.8)))
KQ.append(chay('E. volat_min 1,5% -> 1,2%', dict(volat_min=0.012)))

print('\n--- F. CO VI THE / SO MA ---', flush=True)
for bs in (0.50, 0.60):
    KQ.append(chay(f'F. base_size = {int(bs*100)}%', dict(base_size=bs, max_pos=max(0.5, bs))))
KQ.append(chay('F. max_pos_n 12 -> 16', dict(max_pos_n=16)))

print('\n--- G. VAN THOI GIAN / LAI LON ---', flush=True)
for t in (5, 6):
    KQ.append(chay(f'G. t_valve = T+{t}', dict(t_valve=t)))
for bw in (0.17, 0.22):
    KQ.append(chay(f'G. big_win = {int(bw*100)}%', dict(big_win=bw)))

json.dump(KQ, open('/tmp/quet1.json', 'w'), ensure_ascii=False)
print('\nxong', len(KQ), 'ban')
