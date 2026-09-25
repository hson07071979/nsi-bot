# -*- coding: utf-8 -*-
"""R16 — Predict Condition 9 (OrdImb_t >= 1.40) from data a trader can see BEFORE the ATC
of the signal session, for the candidates that already pass Cond1-8. Time split:
train 2019-2022, test 2023-2026 (and the reverse) -> honest out-of-sample AUC.
Feature sets:
  LAG   : yesterday's / 5-day OrdImb and count ratio (published last night)      - always available
  LIVE  : foreign net buy share, avg matched-trade size vs 20d, close location, pct, volume ratio
          (on every price board during the session)                              - available
  QTY   : today's order QUANTITY ratio BuyQuantity/SellQuantity                  - availability to be measured 28/09"""
import os, sys, json, datetime as dt
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
import engine2 as E
from produce2 import PROD
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score
C0 = dict(E.CFG); C0.update(PROD)
d, I, tls, sect = E.load()
base_rng, base_ok, TOPN, trig = E.prep_masks(d, I, C0)
cal = [str(x) for x in d['cal']]
BQ, SQ, BC, SC = d['BuyQuantity'], d['SellQuantity'], d['BuyCount'], d['SellCount']
V, TT = d['Volume'], d['TotalTrade']; FB, FS = d['BuyForeignQuantity'], d['SellForeignQuantity']
AC, AH, AL = d['AdjClose'], d['AdjHigh'], d['AdjLow']
OI = I['ordimb']; CR = SC / np.where(BC > 0, BC, np.nan)
ats = V / np.where(TT > 0, TT, np.nan)
L = lambda x: np.log(np.clip(x, 1e-6, None)) if x == x else np.nan
rows = []
for i in range(cal.index(next(c for c in cal if c >= '2019-01-02')), len(cal)):
    for r in E.screen(i, d, I, tls, sect, C0, TOPN, base_rng, base_ok, trig, dt.date.fromisoformat(cal[i]), ignore_ordimb=True):
        j = r['j']; y = OI[i, j]
        if y != y: continue
        a20 = np.nanmean(ats[max(0, i - 20):i, j])
        rng = AH[i, j] - AL[i, j]
        f = dict(
            lag_oi1=L(OI[i - 1, j]), lag_oi5=L(np.nanmean(OI[i - 5:i, j])), lag_cr1=L(CR[i - 1, j]),
            live_fnet=float(((FB[i, j] or 0) - (FS[i, j] or 0)) / V[i, j]) if V[i, j] > 0 else 0.0,
            live_ats=L(ats[i, j] / a20) if a20 == a20 and a20 > 0 else 0.0,
            live_cl=float((AC[i, j] - AL[i, j]) / rng) if rng > 0 else 1.0,
            live_pct=float(I['pct'][i, j]), live_volr=L(I['volr'][i, j]),
            qty=L(BQ[i, j] / SQ[i, j]) if SQ[i, j] > 0 else np.nan)
        rows.append(dict(date=cal[i], sym=r['sym'], y=int(y >= 1.4), oi=float(y), **f))
SETS = {'LAG': ['lag_oi1', 'lag_oi5', 'lag_cr1'],
        'LIVE': ['live_fnet', 'live_ats', 'live_cl', 'live_pct', 'live_volr'],
        'LAG+LIVE': ['lag_oi1', 'lag_oi5', 'lag_cr1', 'live_fnet', 'live_ats', 'live_cl', 'live_pct', 'live_volr'],
        'QTY': ['qty'],
        'QTY+LAG+LIVE': ['qty', 'lag_oi1', 'lag_oi5', 'lag_cr1', 'live_fnet', 'live_ats', 'live_cl', 'live_pct', 'live_volr']}
def X(rs, cols):
    a = np.array([[r[c] for c in cols] for r in rs], float); return np.nan_to_num(a, nan=0.0)
A = [r for r in rows if r['date'] < '2023-01-01']; B = [r for r in rows if r['date'] >= '2023-01-01']
out = dict(n=len(rows), n_2019_22=len(A), n_2023_26=len(B), base_rate=float(np.mean([r['y'] for r in rows])), models={})
prob = {}
for name, cols in SETS.items():
    res = {}
    for mname, mk in (('logit', lambda: LogisticRegression(max_iter=2000, C=0.5)),
                      ('gbm', lambda: GradientBoostingClassifier(n_estimators=150, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=1))):
        m1 = mk().fit(X(A, cols), [r['y'] for r in A]); p_B = m1.predict_proba(X(B, cols))[:, 1]
        m2 = mk().fit(X(B, cols), [r['y'] for r in B]); p_A = m2.predict_proba(X(A, cols))[:, 1]
        res[mname] = dict(auc_test_2023_26=float(roc_auc_score([r['y'] for r in B], p_B)),
                          auc_test_2019_22=float(roc_auc_score([r['y'] for r in A], p_A)))
        prob[(name, mname)] = {(r['date'], r['sym']): float(p) for r, p in list(zip(A, p_A)) + list(zip(B, p_B))}
    out['models'][name] = res
    print(name, json.dumps(res))
json.dump(dict(out=out, prob={f'{k[0]}|{k[1]}': {f'{a}|{b}': v for (a, b), v in pv.items()} for k, pv in prob.items()}),
          open('/home/claude/r16_prob.json', 'w'))
json.dump(out, open('evidence/r16_cond9_model.json', 'w'), indent=1)
print('rows', len(rows), 'base rate', out['base_rate'])
