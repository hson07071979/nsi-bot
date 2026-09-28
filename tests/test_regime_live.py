# -*- coding: utf-8 -*-
"""Den tam tinh (regime_live.step) = DUNG vong lap regime2 (28/09/2026). exit_rules chiu duoc cfg co null.
Run: python3 tests/test_regime_live.py"""
import os, sys, json, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); os.chdir(ROOT)
import regime_live as RL, exit_rules as ER
HAVE = os.path.exists('data/fa.npz') and os.path.exists('data/funda_raw2.json') and os.path.exists('data/VNINDEX.json')
ok = 0; T = []
def test(f): T.append(f); return f

@test
def replay_khop_regime2_100pct():
    if not HAVE: print('   SKIP no data'); return True
    import numpy as np, engine2 as E
    from produce2 import PROD
    from regime2 import build_regime, _ffill
    d, I, _, _ = E.load(); C = dict(E.CFG); C.update(PROD); R = build_regime(d, I, C); cal = [str(x) for x in d['cal']]
    V = json.load(open('data/VNINDEX.json'))
    vm = {dt.datetime.utcfromtimestamp(t).date().isoformat(): v for t, v in zip(V['t'], V['v'])}
    vv = _ffill(np.array([vm.get(x, np.nan) for x in cal], dtype=float))
    g = R['g1']; eq = np.r_[0.0, g[1:] / g[:-1] - 1]
    L, _ = RL.replay(eq, R['vni'], vv, C)
    bad = [(cal[i], R['light'][i], L[i]) for i in range(len(cal)) if L[i] != R['light'][i]]
    print(f'   {len(cal)} phien, lech {len(bad)}', bad[:3])
    return not bad

@test
def export_import_giu_nguyen():
    st = RL.empty_state(dict(use_ftd=True)); st.update(dd=[(3, 1800.0)], g1_hist=[1.0] * 199, vc_hist=[2.0] * 49)
    o = json.loads(json.dumps(RL.state_for_export(st, '2026-09-25')))
    b = RL.state_from_export(o)
    return b['dd'] == [(3, 1800.0)] and len(b['g1_hist']) == 199 and o['session'] == '2026-09-25'

@test
def exit_rules_cfg_null():
    C = dict(sell_from=3, mo_by=3, mo_need=0.01, mo_window=None, valve_min=None, t_valve=4)
    return ER.decide(C, 0.0, 0.005, 3)['rule'].startswith('Momentum') and ER.decide(C, -0.001, 0.02, 4)['rule'].startswith('Van')

for f in T:
    try:
        r = f(); print('PASS' if r else 'FAIL', f.__name__); ok += bool(r)
    except Exception as e:
        print('FAIL', f.__name__, type(e).__name__, e)
print(f'{ok}/{len(T)} passed'); sys.exit(0 if ok == len(T) else 1)
