# -*- coding: utf-8 -*-
"""Paired 200-seed miss MC + slippage + remove-top-added-deals for candidate vs reference."""
import os, sys, json
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
import engine2 as E
from produce2 import PROD
from dealstats import deals as DL, stats as DS
REF = json.loads(os.environ['REF']); NEW = json.loads(os.environ['NEW'])
def run(o): C = dict(E.CFG); C.update(PROD); C.update(o); return E.run(C, log=False)
def m(r):
    x = E.metrics(r); d = DS(r['trades'])
    return dict(ret=x['total_return'], dd=x['maxdd'], pf=x['pf'], sharpe=x['sharpe'], deals=d.get('deals'))
rr, rn = run(REF), run(NEW)
o = dict(ref=REF, new=NEW, m_ref=m(rr), m_new=m(rn))
o['slip0.002'] = dict(ref=m(run(dict(REF, slip=0.002))), new=m(run(dict(NEW, slip=0.002))))
b, n = [], []
for s in range(200):
    b.append(E.metrics(run(dict(REF, miss_prob=0.1, miss_seed=7000 + s)))['total_return'])
    n.append(E.metrics(run(dict(NEW, miss_prob=0.1, miss_seed=7000 + s)))['total_return'])
b, n = np.array(b), np.array(n)
o['mc'] = dict(ref_p50=float(np.median(b)), new_p50=float(np.median(n)), ref_p10=float(np.quantile(b, .1)),
               new_p10=float(np.quantile(n, .1)), p_new_gt_ref=float((n > b).mean()))
kr = {(t['sym'], t['entry']) for t in DL(rr['trades'])}
tn = DL(rn['trades']); tr = DL(rr['trades'])
# per-deal change for deals present in both
mp = {(t['sym'], t['entry']): t for t in tr}
ch = sorted([(t['pnl_vnd'] - mp[(t['sym'], t['entry'])]['pnl_vnd'], t['sym'], t['entry'], mp[(t['sym'], t['entry'])]['pnl_pct'], t['pnl_pct'])
             for t in tn if (t['sym'], t['entry']) in mp], key=lambda x: x[0])
o['biggest_losses_from_change'] = ch[:6]; o['biggest_gains_from_change'] = ch[-6:]
o['n_changed'] = sum(1 for x in ch if abs(x[0]) > 1)
print(json.dumps(o, indent=1, default=str))
json.dump(o, open(os.environ.get('OUTF', 'evidence/r13_verify.json'), 'w'), indent=1, default=str)
