# -*- coding: utf-8 -*-
"""R13 — joint 2-D scans for the momentum-exit idea and the ceiling-volume idea
(one-knob descent cannot see combinations). Base = R11 optimum. Same metrics as R11."""
import os, sys, json, itertools
os.environ.setdefault('CACHE', 'evidence/r12_cache.json')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r11_mc_opt as R
from multiprocessing import Pool
BASE = dict(trig_hose=0.056, dk5_hi=0.0, base_range=0.24)
GRIDS = {
  'mo_need_x_by': [dict(mo_by=b, mo_need=g) for b in (2, 3, 4, 5) for g in (0.005, 0.01, 0.015, 0.02, 0.03)],
  'mo_stop_x_until': [dict(mo_stop=x, mo_stop_until=u) for x in (-0.02, -0.025, -0.03, -0.04) for u in (2, 3, 5, 6)],
  'valve_x_min': [dict(t_valve=t, valve_min=v) for t in (3, 4, 5) for v in (0.0, 0.005, 0.01, 0.02)],
  'ceil_vol': [dict(ceil_vol_floor=v) for v in (0.8, 1.0, 1.2, 1.4, 1.6, 1.8)],
}
if __name__ == '__main__':
    cache = R.load_cache(); out = {}
    todo = []
    for name, g in GRIDS.items():
        for o in g:
            c = dict(BASE); c.update(o)
            if R._key(c) not in cache: todo.append(c)
    with Pool(2, initializer=R._init) as pool:
        for res in pool.imap_unordered(R.evaluate, todo):
            cache[R._key(res['over'])] = res; json.dump(cache, open(R.CACHE, 'w'))
    b = cache.get(R._key(BASE)) or R.evaluate(BASE)
    for name, g in GRIDS.items():
        rows = []
        for o in g:
            c = dict(BASE); c.update(o); r = cache[R._key(c)]
            rows.append(dict(o, ret=r['ret'], dd=r['dd'], pf=r['pf'], sharpe=r['sharpe'], deals=r['deals'],
                             mc_p50=r['mc_p50'], mc_p10=r['mc_p10'], dd_p95=r['dd_p95'], h1=r['h1'], h2=r['h2']))
        out[name] = rows
    out['base'] = {k: b[k] for k in ('ret', 'dd', 'pf', 'sharpe', 'deals', 'mc_p50', 'mc_p10', 'dd_p95', 'h1', 'h2')}
    json.dump(out, open('evidence/r13_joint.json', 'w'), ensure_ascii=False, indent=1)
    B = out['base']; print('BASE', {k: round(v, 3) if isinstance(v, float) else v for k, v in B.items()})
    for name in GRIDS:
        print('==', name)
        for r in out[name]:
            k = {x: r[x] for x in r if x in ('mo_by', 'mo_need', 'mo_stop', 'mo_stop_until', 't_valve', 'valve_min', 'ceil_vol_floor')}
            print('  %-40s ret %6.1f dd %5.2f pf %5.2f deals %s mc50 %6.1f mc10 %6.1f h1 %6.1f h2 %6.1f' % (
                k, r['ret']*100, r['dd']*100, r['pf'], r['deals'], r['mc_p50']*100, r['mc_p10']*100, r['h1']*100, r['h2']*100))
