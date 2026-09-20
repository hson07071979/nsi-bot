# -*- coding: utf-8 -*-
"""Kiem lai hai ban chinh trong dieu kien CO TRUOT GIA 0,2% — margin lam tang
   vong quay nen phai xem truot gia co an mat phan hon khong."""
import numpy as np, engine_margin as E
from produce2 import PROD
CHUNG = dict(PROD, base_size=0.25, max_pos=0.25,
             size_map={'XANH':1.0,'VANG':1.0,'CAM':1.0,'DO':1.0})
B = {'XANH': (8, 2.00), 'VANG': (4, 1.00), 'CAM': (2, 0.50), 'DO': (1, 0.25)}
C = {'XANH': (4, 1.00), 'VANG': (4, 1.00), 'CAM': (2, 0.50), 'DO': (1, 0.25)}
for ten, cfg, mm, rate in [
    ('0. PROD  + truot 0,2%',            dict(PROD, slip=0.002), None, 0.0),
    ('1. 25%x4 khong vay + truot 0,2%',  dict(CHUNG, slip=0.002), C,   0.0),
    ('3B. Xanh 8 ma, lai 13% + truot',   dict(CHUNG, slip=0.002), B,   0.13)]:
    c = dict(cfg)
    if mm: c.update(margin_map=mm, margin_rate=rate)
    r = E.run(c, log=False); m = E.metrics(r); g = r.get('margin', {})
    print(f"{ten:36s} loi {m['total_return']*100:7.1f}%  DD {m['maxdd']*100:5.2f}%  "
          f"PF {m['pf']:5.2f}  Sharpe {m['sharpe']:4.2f}  lenh {m['trades']:3d}  "
          f"deal {len({(t['sym'],t['entry']) for t in r['trades']}):3d}  "
          f"lai {g.get('phi_lai',0)/1e6:6.1f} tr", flush=True)
