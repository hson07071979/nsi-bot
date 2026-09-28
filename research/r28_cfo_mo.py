"""R28 (28/09/2026): (A) CFO gate variants on TOP110+S1 PROD, (B) Momentum exit T+3..T+7.
Research only — PROD unchanged."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, numpy as np, datetime as dt
from collections import Counter
from common import pmap, line, run, meta
import engine2 as E, engine as EN
from dealstats import deals

def c(**k): return dict(k)
J = []
for sl, t in ((0.0, ''), (0.002, ' slip0.2%')):
    J += [('CFO_HARD (PROD)' + t, c(slip=sl)),
          ('CFO_OFF' + t, c(cfo_mode='off', slip=sl))]
    for m in (0.35, 0.5):
        J += [(f'V1 SECTOR x{m}' + t, c(cfo_mode='sector', cfo_warn_mul=m, slip=sl))]
        for g in (0.2, 0.3):
            J += [(f'V2 GROWTH>={int(g*100)}% x{m}' + t, c(cfo_mode='growth', cfo_warn_mul=m, cfo_growth_min=g, slip=sl)),
                  (f'V2b SECTOR+GROWTH>={int(g*100)}% x{m}' + t, c(cfo_mode='sector_growth', cfo_warn_mul=m, cfo_growth_min=g, slip=sl))]
        J += [(f'V3 REPEAT x{m}' + t, c(cfo_mode='repeat', cfo_warn_mul=m, slip=sl))]
    J += [('V3 REPEAT x1.0' + t, c(cfo_mode='repeat', cfo_warn_mul=1.0, slip=sl))]
# momentum
for sl, t in ((0.0, ''), (0.002, ' slip0.2%')):
    J += [('MO off' + t, c(mo_by=None, slip=sl))]
    for n in (3, 4, 5, 6, 7):
        J += [(f'MO T+{n} (van T+4)' + t, c(mo_by=n, slip=sl))]
        if n > 4:
            J += [(f'MO T+{n} + van T+{n}' + t, c(mo_by=n, t_valve=n, slip=sl))]
for n in (4, 5):
    J += [(f'MO T+{n} need2%', c(mo_by=n, mo_need=0.02))]
J += [('CFO_HARD next_open', c(entry_mode='next_open')), ('CFO_OFF next_open', c(cfo_mode='off', entry_mode='next_open'))]
for n in (4, 5, 6, 7):
    J += [(f'MO T+{n} next_open', c(mo_by=n, entry_mode='next_open'))]

R = pmap(J, 2)
for s in R: print(line(s), flush=True)

# ---- cohort + PET + robustness for key variants ----
d, I, tls, sect = E.load()
def blocked_by_cfo(sym, date):
    f = E.as_of(tls.get(sym), dt.date.fromisoformat(date)) if tls.get(sym) else None
    if f is None: return False
    EN.CFG['cfo_mode'] = 'hard'; b, w, _ = EN.risk_gate(sym, f)
    return b and w == 'CFO < 0'
def st(X):
    if not X: return dict(n=0)
    p = np.array([x['pnl_pct'] for x in X]); v = np.array([x['pnl_vnd'] for x in X])
    gp = v[v > 0].sum(); gl = -v[v < 0].sum(); w = sorted(v[v > 0], reverse=True)
    return dict(n=len(X), winrate=round(float((p > 0).mean()), 3), pf=round(float(gp / gl), 2) if gl else None,
                avg=round(float(p.mean()), 2), median=round(float(np.median(p)), 2), worst=round(float(p.min()), 2),
                best=round(float(p.max()), 2), top1_share=round(float(w[0] / gp), 3) if w else None,
                net_mvnd=round(float(v.sum() / 1e6)), years=dict(sorted(Counter(x['entry'][:4] for x in X).items())),
                sectors=dict(Counter(sect.get(x['sym'], 'Khác') for x in X).most_common(6)))
KEY = [('CFO_OFF', c(cfo_mode='off')), ('V1 SECTOR x0.5', c(cfo_mode='sector', cfo_warn_mul=0.5)),
       ('V2 GROWTH>=30% x0.5', c(cfo_mode='growth', cfo_warn_mul=0.5, cfo_growth_min=0.3)),
       ('V2b SECTOR+GROWTH>=30% x0.5', c(cfo_mode='sector_growth', cfo_warn_mul=0.5, cfo_growth_min=0.3)),
       ('V3 REPEAT x0.5', c(cfo_mode='repeat', cfo_warn_mul=0.5))]
s0, r0 = run({}, 'PROD', keep=True)
base_keys = {(x['sym'], x['entry']) for x in deals(r0['trades'])}
COH = {}
for name, o in KEY:
    s, r = run(o, name, keep=True)
    D = deals(r['trades'])
    new = [x for x in D if (x['sym'], x['entry']) not in base_keys]
    coh = [x for x in new if blocked_by_cfo(x['sym'], x['entry'])]
    lost = [x for x in deals(r0['trades']) if (x['sym'], x['entry']) not in {(y['sym'], y['entry']) for y in D}]
    pet = [x for x in D if x['sym'] == 'PET']
    top = sorted([x for x in D], key=lambda x: -x['pnl_vnd'])[:3]
    fm = [(x['sym'], x['entry']) for x in top]
    s_m1 = run(dict(o, force_miss=fm[:1]), name + ' -top1')
    s_m3 = run(dict(o, force_miss=fm), name + ' -top3')
    COH[name] = dict(new_cfo_cohort=st(coh), cohort_deals=sorted([(x['sym'], x['entry'], x['pnl_pct'], round(x['pnl_vnd'] / 1e6)) for x in coh], key=lambda z: -z[3]),
                     lost_from_prod=[(x['sym'], x['entry'], x['pnl_pct']) for x in lost], pet_deals=[(x['sym'], x['entry'], x['exit'] if 'exit' in x else None, x['pnl_pct']) for x in pet],
                     yearly=s['yearly'], minus_top1=s_m1['metrics'], minus_top3=s_m3['metrics'], top3=fm)
    print(name, json.dumps({k: v for k, v in COH[name].items() if k != 'cohort_deals'}, ensure_ascii=False, default=str), flush=True)
# PROD robustness reference
t0 = sorted(deals(r0['trades']), key=lambda x: -x['pnl_vnd'])[:3]; fm0 = [(x['sym'], x['entry']) for x in t0]
REF = dict(minus_top1=run(dict(force_miss=fm0[:1]), 'PROD -top1')['metrics'], minus_top3=run(dict(force_miss=fm0), 'PROD -top3')['metrics'], yearly=s0['yearly'], top3=fm0)
print('PROD ref', json.dumps(REF, default=str))
# Momentum: exit-reason mix per variant
MOX = {}
for n in (3, 4, 5, 6, 7):
    s, r = run(c(mo_by=n), f'MO{n}', keep=True)
    MOX[n] = dict(reasons=Counter(str(t.get('reason', ''))[:22] for t in r['trades']).most_common(10), yearly=s['yearly'], deal_metrics=s['deal_metrics'])
json.dump(dict(meta=meta(dict(base='PROD TOP110+S1', data_cut='2026-09-25')), runs=R, cohort=COH, prod_ref=REF, mo_exits=MOX),
          open('evidence/r28_cfo_mo.json', 'w'), ensure_ascii=False, indent=1, default=str)
print('DONE')
