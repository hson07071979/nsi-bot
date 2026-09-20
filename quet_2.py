# -*- coding: utf-8 -*-
"""GIAI DOAN 2 — luoi HAI CHIEU: noi vu tru (top_n) x noi nen gia (base_range).
   Voi MOI o, do them ba thu de biet con so co that hay do may:
     - nua dau 2019-2022 va nua sau 2023-2026 rieng ra (co on dinh khong)
     - phan tram loi nhuan den tu 3 lenh lon nhat (co phu thuoc duoi phai khong)
     - co truot gia 0,2% (co song sot khong)"""
import json, numpy as np, engine2 as E
from produce2 import PROD

def nua(r, dau, cuoi):
    """Chi so tinh RIENG cho mot lat cat thoi gian."""
    eq = [(d, v) for d, v, *_ in r['eq'] if dau <= d[:4] <= cuoi]
    if len(eq) < 30: return None
    a = np.array([v for _, v in eq])
    dd = float((1 - a / np.maximum.accumulate(a)).max())
    tr = [t for t in r['trades'] if dau <= t['exit'][:4] <= cuoi]
    gp = sum(t['pnl_vnd'] for t in tr if t['pnl_vnd'] > 0)
    gl = abs(sum(t['pnl_vnd'] for t in tr if t['pnl_vnd'] < 0))
    return dict(loi=round(float(a[-1] / a[0] - 1), 4), dd=round(dd, 4),
                pf=round(gp / gl, 2) if gl else None, lenh=len(tr))

def dinh(r):
    """Ba lenh lai nhieu nhat chiem bao nhieu % tong lai gop."""
    v = sorted((t['pnl_vnd'] for t in r['trades']), reverse=True)
    gp = sum(x for x in v if x > 0)
    return round(sum(v[:3]) / gp * 100, 1) if gp else None

def chay(ten, ghi_de, truot=False):
    c = dict(PROD); c.update(ghi_de)
    if truot: c['slip'] = 0.002
    r = E.run(c, log=False); m = E.metrics(r)
    return dict(ten=ten, **{k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                            for k, v in m.items()},
                deal=len({(t['sym'], t['entry']) for t in r['trades']}),
                dau=nua(r, '2019', '2022'), cuoi=nua(r, '2023', '2026'), top3=dinh(r))

KQ = []
print(f"{'top_n':>6} {'nen':>5} | {'tong lai':>9} {'DD':>6} {'PF':>5} {'Sharpe':>6} {'deal':>4} | "
      f"{'19-22':>8} {'23-26':>8} | {'top3':>5}", flush=True)
for tn in (110, 120, 140, 160, 180, 200, 250, 300):
    for br in (0.18, 0.20, 0.22, 0.25):
        d = chay(f'top{tn}_nen{int(br*100)}', dict(top_n=tn, base_range=br))
        KQ.append(d)
        print(f"{tn:>6} {int(br*100):>4}% | {d['total_return']*100:8.1f}% {d['maxdd']*100:5.2f}% "
              f"{d['pf']:5.2f} {d['sharpe']:6.2f} {d['deal']:4d} | "
              f"{d['dau']['loi']*100:7.1f}% {d['cuoi']['loi']*100:7.1f}% | {d['top3']:4.1f}%", flush=True)
json.dump(KQ, open('/tmp/quet2.json', 'w'), ensure_ascii=False)
print('\nxong', len(KQ), 'o luoi')
