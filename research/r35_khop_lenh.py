# -*- coding: utf-8 -*-
"""R35 (05/10/2026) — KL/GTGD co nen loai giao dich THOA THUAN khong?
FireAnt 'Volume' = khop lenh + thoa thuan (PutthroughVolume). A = PROD (tong),
B = KL khop lenh cho DK2/TB20/diem S, C = B + GTGD tru gia tri thoa thuan (uoc = KL tt x gia dong cua)
— anh huong ca TOP-N thanh khoan. Monte Carlo lo 10% lenh, 30 seed."""
import os, sys, json, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import engine2 as E
from research import common as C
from fa_ind import indicators

def bien_the(kind):
    E._CACHE.clear(); d, I, tls, sect = E.load()
    if kind == 'A': return
    PT = np.load('/tmp/PT.npy')
    d = dict(d)
    V = d['Volume'].astype(np.float64); PTm = np.where(np.isnan(V), np.nan, PT)
    d['Volume'] = np.maximum(V - PTm, 0).astype(np.float32)
    if kind == 'C':
        TV = d['TotalValue'].astype(np.float64)
        d['TotalValue'] = np.maximum(TV - PTm * d['PriceClose'], 0).astype(np.float32)
    E._CACHE['d'] = d; E._CACHE['I'] = indicators(d)

out = {}
for k in ('A', 'B', 'C'):
    bien_the(k)
    s = C.run({}, name=k)
    mc = [C.run(dict(miss_prob=0.10, miss_seed=sd), name=f'{k}|{sd}')['metrics']['total_return'] for sd in range(1, 31)]
    s['mc_med'] = float(np.median(mc)); s['mc_p10'] = float(np.percentile(mc, 10))
    print(C.line(s), '| MC med %+.1f%% p10 %+.1f%%' % (s['mc_med'] * 100, s['mc_p10'] * 100), flush=True)
    out[k] = s
json.dump(out, open('/home/claude/w/r35_khop_lenh.json', 'w'), ensure_ascii=False, default=str)
