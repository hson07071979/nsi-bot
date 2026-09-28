"""R28b: stress-test V1 (CFO sector warn) vs PROD. Research only."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, numpy as np
from common import pmap, line, run, meta
import engine2 as E
from dealstats import deals

V1 = lambda m: dict(cfo_mode='sector', cfo_warn_mul=m)
J = [('PROD', {})]
for m in (0.2, 0.25, 0.35, 0.5, 0.65, 0.8, 1.0):
    J.append((f'V1 x{m}', V1(m)))
for n, o in (('PROD', {}), ('V1 x0.35', V1(0.35)), ('V1 x0.5', V1(0.5))):
    J += [(n + ' next_open', dict(o, entry_mode='next_open')), (n + ' next_vwap', dict(o, entry_mode='next_vwap')),
          (n + ' slip0.8%', dict(o, slip=0.008))]
U = [('VIX', '2025-07-02'), ('GAS', '2025-12-29'), ('TCM', '2020-11-06'), ('PLX', '2026-01-07'), ('PLX', '2026-01-06')]
for n, o in (('PROD', {}), ('V1 x0.35', V1(0.35)), ('V1 x0.5', V1(0.5))):
    J += [(n + ' -union5', dict(o, force_miss=U))]
# Monte Carlo: miss 10% of signals, 40 seeds
for sd in range(1, 41):
    J += [(f'MC PROD {sd}', dict(miss_prob=0.10, miss_seed=sd)), (f'MC V1 {sd}', dict(V1(0.35), miss_prob=0.10, miss_seed=sd))]
R = pmap(J, 2)
for s in R:
    if not s['name'].startswith('MC'): print(line(s), flush=True)
mc = {}
for k in ('PROD', 'V1'):
    X = [s for s in R if s['name'].startswith(f'MC {k} ')]
    ret = np.array([s['metrics']['total_return'] for s in X]); dd = np.array([s['metrics']['maxdd'] for s in X]); pf = np.array([s['metrics']['pf'] for s in X])
    mc[k] = dict(ret=ret.tolist(), dd=dd.tolist(), pf=pf.tolist(),
                 summ=dict(ret_p10=float(np.percentile(ret, 10)), ret_med=float(np.median(ret)), ret_p90=float(np.percentile(ret, 90)),
                           dd_med=float(np.median(dd)), dd_max=float(dd.max()), pf_med=float(np.median(pf)), pf_min=float(pf.min())))
    print('MC', k, json.dumps(mc[k]['summ']), flush=True)
pr = [s for s in R if s['name'].startswith('MC PROD ')]; vr = [s for s in R if s['name'].startswith('MC V1 ')]
wins = sum(1 for a, b in zip(pr, vr) if b['metrics']['total_return'] > a['metrics']['total_return'])
wpf = sum(1 for a, b in zip(pr, vr) if b['metrics']['pf'] > a['metrics']['pf'])
wdd = sum(1 for a, b in zip(pr, vr) if b['metrics']['maxdd'] <= a['metrics']['maxdd'])
print(f'MC paired: V1 wins ret {wins}/40, PF {wpf}/40, DD<= {wdd}/40')
# PLX + 2026 path detail
_, r0 = run({}, 'PROD', keep=True); _, r1 = run(V1(0.35), 'V1', keep=True)
D0 = {(x['sym'], x['entry']): x for x in deals(r0['trades'])}; D1 = {(x['sym'], x['entry']): x for x in deals(r1['trades'])}
only0 = sorted([(k, D0[k]['pnl_pct'], round(D0[k]['pnl_vnd'] / 1e6)) for k in D0 if k not in D1], key=lambda z: z[0][1])
only1 = sorted([(k, D1[k]['pnl_pct'], round(D1[k]['pnl_vnd'] / 1e6)) for k in D1 if k not in D0], key=lambda z: z[0][1])
print('ONLY PROD:', only0); print('ONLY V1:', only1)
json.dump(dict(meta=meta(dict(base='PROD TOP110+S1')), runs=[s for s in R if not s['name'].startswith('MC')], mc=mc,
               mc_paired=dict(ret=wins, pf=wpf, dd=wdd), only_prod=only0, only_v1=only1),
          open('evidence/r28b_verify.json', 'w'), ensure_ascii=False, indent=1, default=str)
print('DONE')
