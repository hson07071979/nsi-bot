# -*- coding: utf-8 -*-
"""R17 — universe size TOP-N 100..130 on PROD 26/09 (probe-buy, sell from T+3), with Monte Carlo."""
import os, sys, json
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
import engine2 as E
from produce2 import PROD
from dealstats import stats as DS
from research.common import meta
def pf(ts):
    gp = sum(t['pnl_vnd'] for t in ts if t['pnl_vnd'] > 0); gl = -sum(t['pnl_vnd'] for t in ts if t['pnl_vnd'] < 0)
    return gp / gl if gl else None
rows = []
for n in (100, 105, 110, 115, 120, 125, 130):
    C = dict(E.CFG); C.update(PROD); C['top_n'] = n
    r = E.run(C, log=False); m = E.metrics(r); T = r['trades']
    real = [t for t in T if not t['reason'].startswith('Cond9')]; pr = [t for t in T if t['reason'].startswith('Cond9')]
    dr = DS(real)
    eq = r['eq']; seg = lambda a, b: (lambda v: v[-1] / v[0] - 1)([x[1] for x in eq if a <= x[0][:4] <= b])
    mc = np.array([E.metrics(E.run(dict(C, miss_prob=0.1, miss_seed=12000 + s), log=False))['total_return'] for s in range(100)])
    sl = E.metrics(E.run(dict(C, slip_buy=0.002, slip_sell=0.008), log=False))
    row = dict(top_n=n, ret=m['total_return'], dd=m['maxdd'], pf=m['pf'], sharpe=m['sharpe'],
               deals_real=dr.get('deals'), wr_real=dr.get('winrate'), avg_win=dr.get('avg_win'), avg_loss=dr.get('avg_loss'),
               pf_real=pf(real), probes=len(pr), h1=seg('2019', '2022'), h2=seg('2023', '2026'),
               mc_p50=float(np.median(mc)), mc_p10=float(np.quantile(mc, .1)), mc_p90=float(np.quantile(mc, .9)),
               slip_real_ret=sl['total_return'], slip_real_dd=sl['maxdd'])
    rows.append(row)
    print('TOP %3d | lãi %6.1f%% DD %5.2f%% PF %.2f (lệnh thật %.2f) Sharpe %.2f | deal thật %d thắng %.1f%% lãiTB %+.1f%% lỗTB %+.2f%% | dò %d | 19-22 %6.1f%% 23-26 %6.1f%% | MC p50 %6.1f%% p10 %6.1f%% | trượt 0,2/0,8 %6.1f%% DD %.1f%%' % (
        n, row['ret']*100, row['dd']*100, row['pf'], row['pf_real'], row['sharpe'], row['deals_real'], row['wr_real']*100, row['avg_win'], row['avg_loss'],
        row['probes'], row['h1']*100, row['h2']*100, row['mc_p50']*100, row['mc_p10']*100, row['slip_real_ret']*100, row['slip_real_dd']*100), flush=True)
json.dump(dict(meta=meta(dict(experiment_version='audit-2026-09-26/r17')), rows=rows), open('evidence/audit_r17_topn.json', 'w'), ensure_ascii=False, indent=1, default=float)
