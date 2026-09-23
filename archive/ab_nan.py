# -*- coding: utf-8 -*-
"""A/B loi `tot = NaN` — chay MOT LAN de do gia phai tra cua ban sua.

Cach chay (tren may chay bot, sau khi da co data/fa.npz):
    python3 ab_nan.py

In ra hai cot: ban CU (loi con nguyen) va ban SUA. Con so dang nhin la
total_return, maxdd va so deal — neu chenh duoi 3 diem % thi theo quyet dinh
cua anh Son la SUA.
"""
import copy, json
from engine2 import CFG, run

def do(fix):
    c = copy.deepcopy(CFG); c['nan_tot_fix'] = fix
    return run(c, log=False)

cu  = do(False)
moi = do(True)

def lay(r):
    m = r['metrics']; d = r.get('deal_metrics') or {}
    return dict(total_return=m['total_return'], cagr=m['cagr'], maxdd=m['maxdd'],
                pf=m['pf'], sharpe=m['sharpe'], trades=m['trades'], deals=d.get('deals'))

a, b = lay(cu), lay(moi)
print(f"{'chi so':<16}{'CU (con loi)':>16}{'SUA':>16}{'chenh':>14}")
for k in a:
    va, vb = a[k], b[k]
    if va is None or vb is None: continue
    ch = vb - va
    if k in ('total_return', 'cagr', 'maxdd'):
        print(f"{k:<16}{va*100:>15.2f}%{vb*100:>15.2f}%{ch*100:>13.2f}d%")
    else:
        print(f"{k:<16}{va:>16}{vb:>16}{ch:>14}")

# hai lenh da biet la dinh loi
for r, ten in ((cu, 'CU'), (moi, 'SUA')):
    co = [t for t in r['trades']
          if (t['sym'] == 'LCG' and t['entry'].startswith('2024-03'))
          or (t['sym'] == 'VIX' and t['entry'].startswith('2024-03'))]
    print(f"\n{ten}: {len(co)} lenh LCG/VIX thang 3-2024 ->",
          [(t['sym'], t['entry'], round(t['pnl_pct'], 2)) for t in co])

json.dump({'cu': a, 'sua': b}, open('data/ab_nan.json', 'w'), indent=1)
print("\nda ghi data/ab_nan.json")
