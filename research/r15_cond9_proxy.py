# -*- coding: utf-8 -*-
"""R15 — Can Condition 9 be known DURING the session? The exact OrdImb needs order COUNTS
(published after the close). Order QUANTITIES may be observable intraday. Test proxies built
only from intraday-observable data (+ yesterday's counts) on the full history."""
import os, sys, json, datetime as dt
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
import engine2 as E
from produce2 import PROD
from dealstats import stats as DS
from research.common import meta
C0 = dict(E.CFG); C0.update(PROD)
d, I, tls, sect = E.load()
base_rng, base_ok, TOPN, trig = E.prep_masks(d, I, C0)
cal = [str(x) for x in d['cal']]
i0 = cal.index(next(c for c in cal if c >= '2019-01-02'))
P = {k: E._oi_arr(d, I, dict(oi_proxy=k)) for k in ('qty', 'qty_cr1', 'qty_cr5')}
rows = []
for i in range(i0, len(cal)):
    for r in E.screen(i, d, I, tls, sect, C0, TOPN, base_rng, base_ok, trig, dt.date.fromisoformat(cal[i]), ignore_ordimb=True):
        j = r['j']; t = float(I['ordimb'][i, j])
        if t != t: continue
        rows.append(dict(date=cal[i], sym=r['sym'], true=t, **{k: float(v[i, j]) for k, v in P.items()}))
def rank(a): return np.argsort(np.argsort(a))
out = dict(n_candidates=len(rows), pass_rate=float(np.mean([r['true'] >= 1.4 for r in rows])))
cls = {}
for k in P:
    x = np.array([r[k] for r in rows]); y = np.array([r['true'] for r in rows]); ok = ~np.isnan(x)
    rho = float(np.corrcoef(rank(x[ok]), rank(y[ok]))[0, 1])
    best = None
    for th in np.arange(0.8, 3.01, 0.05):
        pred = x[ok] >= th; tru = y[ok] >= 1.4
        acc = float((pred == tru).mean()); tp = int((pred & tru).sum()); fp = int((pred & ~tru).sum()); fn = int((~pred & tru).sum())
        prec = tp / max(1, tp + fp); rec = tp / max(1, tp + fn)
        f1 = 2 * prec * rec / max(1e-9, prec + rec)
        if best is None or f1 > best['f1']: best = dict(th=round(float(th), 2), acc=acc, prec=prec, rec=rec, f1=f1, fp=fp, fn=fn)
    cls[k] = dict(spearman=rho, coverage=float(ok.mean()), best=best)
out['classification'] = cls
print(json.dumps(out, indent=1))
bt = []
def run(o):
    C = dict(C0); C.update(o); r = E.run(C, log=False); m = E.metrics(r)
    eq = r['eq']; seg = lambda a, b: (lambda v: v[-1] / v[0] - 1)([x[1] for x in eq if a <= x[0][:4] <= b])
    return dict(o=o, ret=m['total_return'], dd=m['maxdd'], pf=m['pf'], sharpe=m['sharpe'], deals=DS(r['trades']).get('deals'),
                h1=seg('2019', '2022'), h2=seg('2023', '2026'))
bt.append(dict(run({}), name='PROD (OrdImb thật, sau phiên)'))
bt.append(dict(run(dict(use_ordimb=False)), name='Bỏ ĐK9'))
for k, grid in (('qty', [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0]), ('qty_cr1', [1.2, 1.3, 1.4, 1.5, 1.6]), ('qty_cr5', [1.2, 1.3, 1.4, 1.5, 1.6])):
    for th in grid:
        bt.append(dict(run(dict(oi_proxy=k, ordimb_min=th)), name=f'{k} ≥ {th}'))
for b in bt:
    print('%-32s ret %7.1f%% dd %5.2f%% pf %5.2f sh %4.2f deals %s | 19-22 %6.1f%% 23-26 %6.1f%%' % (
        b['name'], b['ret']*100, b['dd']*100, b['pf'], b['sharpe'], b['deals'], b['h1']*100, b['h2']*100), flush=True)
out['backtest'] = bt
json.dump(dict(meta=meta(dict(experiment_version='audit-2026-09-25/r15')), **out), open('evidence/audit_r15_cond9_proxy.json', 'w'), ensure_ascii=False, indent=1, default=str)
