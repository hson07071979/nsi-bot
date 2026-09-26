# -*- coding: utf-8 -*-
"""Verify the R11 winner against PROD: 200-seed miss MC, slippage, removal of the
best NEW deals (luck check), per-year, deal-level paired bootstrap."""
import os, sys, json
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
import engine2 as E
from produce2 import PROD
from dealstats import deals as DL, stats as DS
from research.common import yearly
P = json.load(open('evidence/r11_progress.json'))
NEW = {k: v for k, v in P['base'].items()}
def cfg(o): C = dict(E.CFG); C.update(PROD); C.update(o); return C
def run(o): return E.run(cfg(o), log=False)
def m(r):
    x = E.metrics(r); d = DS(r['trades'])
    return dict(ret=x['total_return'], cagr=x['cagr'], dd=x['maxdd'], pf=x['pf'], sharpe=x['sharpe'],
                deals=d.get('deals'), wr_deal=d.get('winrate'))
out = dict(new_cfg=NEW)
rb, rn = run({}), run(NEW)
out['base'], out['new'] = m(rb), m(rn)
out['yearly'] = dict(base=yearly(rb['eq']), new=yearly(rn['eq']))
for sl in (0.001, 0.002):
    out[f'slip{sl}'] = dict(base=m(run(dict(slip=sl))), new=m(run(dict(NEW, slip=sl))))
mc = {'base': [], 'new': []}
for s in range(200):
    mc['base'].append(E.metrics(run(dict(miss_prob=0.10, miss_seed=5000 + s)))['total_return'])
    mc['new'].append(E.metrics(run(dict(NEW, miss_prob=0.10, miss_seed=5000 + s)))['total_return'])
b, n = np.array(mc['base']), np.array(mc['new'])
out['mc_miss10_200'] = dict(base_p50=float(np.median(b)), new_p50=float(np.median(n)), base_p10=float(np.quantile(b, .1)),
                            new_p10=float(np.quantile(n, .1)), p_new_gt_base=float((n > b).mean()))
# deals only in NEW (by sym+entry), ranked by pnl
kb = {(t['sym'], t['entry']) for t in DL(rb['trades'])}
dn = sorted([t for t in DL(rn['trades']) if (t['sym'], t['entry']) not in kb], key=lambda t: -t['pnl_vnd'])
db = [t for t in DL(rb['trades']) if (t['sym'], t['entry']) not in {(x['sym'], x['entry']) for x in DL(rn['trades'])}]
out['deals_added'] = [dict(sym=t['sym'], entry=t['entry'], pnl_pct=t.get('pnl_pct'), pnl_vnd=t['pnl_vnd']) for t in dn]
out['deals_removed'] = [dict(sym=t['sym'], entry=t['entry'], pnl_pct=t.get('pnl_pct'), pnl_vnd=t['pnl_vnd']) for t in db]
for k in (1, 2, 3):
    fm = [(t['sym'], t['entry']) for t in dn[:k]]
    out[f'new_minus_top{k}_added'] = m(run(dict(NEW, force_miss=fm)))
from research.common import meta as _meta
out = {'meta': _meta(dict(experiment_version='audit-2026-09-25/r11', note='research only, PROD unchanged')), **out}
json.dump(out, open('evidence/audit_r11_verify.json', 'w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: out[k] for k in ('base', 'new', 'mc_miss10_200', 'new_minus_top1_added', 'new_minus_top2_added', 'new_minus_top3_added')}, indent=1))
print('added', len(dn), 'removed', len(db)); print(out['deals_added'][:6])
