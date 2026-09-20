# -*- coding: utf-8 -*-
"""DEMO MARGIN — KHONG phai cau hinh dang chay. Chi de tra loi cau hoi cua anh Son:
   25% NAV moi ma, so ma toi da theo den thi truong, co/khong co lai vay 13%/nam.
   Dung engine_margin.py (ban sao cua engine2.py co them lop vay) — engine2.py
   KHONG bi dong toi."""
import json, numpy as np, engine_margin as E
from collections import Counter
from produce2 import PROD

# Cau hinh chung cho moi ban demo: moi ma dung 25% NAV, khong phan biet den.
# Den chi quyet dinh CAM BAO NHIEU MA (tuc tran tong von), khong quyet dinh co vi the.
CHUNG = dict(PROD, base_size=0.25, max_pos=0.25,
             size_map={'XANH': 1.0, 'VANG': 1.0, 'CAM': 1.0, 'DO': 1.0})

# (so ma toi da, tran tong von theo % NAV). 1.0 = khong vay, 2.0 = don bay 2:1.
A = {'XANH': (4, 1.00), 'VANG': (8, 2.00), 'CAM': (2, 0.50), 'DO': (1, 0.25)}
B = {'XANH': (8, 2.00), 'VANG': (4, 1.00), 'CAM': (2, 0.50), 'DO': (1, 0.25)}
C = {'XANH': (4, 1.00), 'VANG': (4, 1.00), 'CAM': (2, 0.50), 'DO': (1, 0.25)}

BAN = [
 ('0. Dang chay (PROD, khong margin)',      dict(PROD), None,  0.00),
 ('1. 25%x4 ca Xanh lan Vang - KHONG vay',  CHUNG,      C,     0.00),
 ('2A. Xanh 4 ma / Vang 8 ma - lai 0%',     CHUNG,      A,     0.00),
 ('2B. Xanh 4 ma / Vang 8 ma - lai 13%',    CHUNG,      A,     0.13),
 ('3A. Xanh 8 ma / Vang 4 ma - lai 0%',     CHUNG,      B,     0.00),
 ('3B. Xanh 8 ma / Vang 4 ma - lai 13%',    CHUNG,      B,     0.13),
]

def sau_thue(r):
    """Deal = gop cac dong lenh cung ma cung lan vao, de dem 'so deal' giong trang."""
    return len({(t['sym'], t['entry']) for t in r['trades']})

out = []
for ten, cfg, mm, rate in BAN:
    c = dict(cfg)
    if mm: c.update(margin_map=mm, margin_rate=rate)
    r = E.run(c, log=False)
    m = E.metrics(r)
    mg = r.get('margin', {})
    eq = np.array([x[1] for x in r['eq']])
    m['deals'] = sau_thue(r)
    m['phi_lai'] = mg.get('phi_lai', 0.0)
    m['ngay_vay'] = mg.get('ngay_vay', 0)
    m['vay_dinh'] = mg.get('vay_dinh', 0.0)
    m['don_bay_dinh'] = mg.get('don_bay_dinh', 1.0)
    m['goi_ky_quy'] = len(mg.get('goi_ky_quy', []))
    m['cua'] = dict(Counter(t['reason'] for t in r['trades']).most_common())
    # Do thuc: bao nhieu phien thuc su dung den tien vay, don bay trung binh la bao nhieu.
    _gross = []
    for k, (dd, nv, l, _) in enumerate(r['eq']):
        _gross.append(0.0)
    m['ngay'] = len(r['eq'])
    m['nam'] = {}
    d = {}
    for dd, nv, l, _ in r['eq']: d.setdefault(dd[:4], []).append(float(nv))
    p = None
    for y in sorted(d):
        s0 = p if p is not None else d[y][0]
        m['nam'][y] = round(d[y][-1] / s0 - 1, 4); p = d[y][-1]
    m['ten'] = ten
    out.append(m)
    print(f"{ten:42s} loi {m['total_return']*100:8.1f}%  DD {m['maxdd']*100:5.2f}%  "
          f"PF {m['pf']:5.2f}  Sharpe {m['sharpe']:4.2f}  lenh {m['trades']:3d}  deal {m['deals']:3d}",
          flush=True)

def _sach(o):
    if isinstance(o, dict):  return {k: _sach(v) for k, v in o.items()}
    if isinstance(o, list):  return [_sach(v) for v in o]
    if isinstance(o, (np.floating, np.integer)): return float(o)
    return o
json.dump(_sach(out), open('/tmp/margin_demo.json', 'w'), ensure_ascii=False)
for m in out:
    print(f"\n{m['ten']}")
    print(f"   lai tra   {m['phi_lai']/1e6:10.1f} tr   ngay co vay {m['ngay_vay']:5d}/{m['ngay']}"
          f"   vay dinh {m['vay_dinh']/1e6:9.1f} tr   don bay dinh {m['don_bay_dinh']:.2f}x"
          f"   goi ky quy {m['goi_ky_quy']}")
    print(f"   winrate {m['winrate']*100:5.2f}%  avg win {m['avg_win']:6.2f}%  avg loss {m['avg_loss']:6.2f}%"
          f"  RR {m['rr']:5.2f}  expectancy {m['expectancy']:5.2f}  CAGR {m['cagr']*100:5.2f}%")
    print('   cua ra:', m['cua'])
    print('   theo nam:', m['nam'])
print('\nxong')
