# -*- coding: utf-8 -*-
"""PARITY: live signal_spec.evaluate() vs engine2.screen(), session by session.

For every session t in the window, export the spec from session t-1 (what the
nightly build publishes), feed evaluate() the session-t FireAnt row rebuilt from
the data matrices, and compare the set of symbols passing ALL production
conditions with engine2.screen(t). Mismatches are listed by condition.
Run: python3 tests/test_parity.py [start] [end]"""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from collections import Counter
import engine2 as E, engine as EN
import signal_spec as SP, spec_export as SX
from produce2 import PROD

def main(start='2023-01-01', end=None, cfg=None, verbose=True):
    C = dict(E.CFG); C.update(PROD); C.update(cfg or {})
    EN.CFG['cfo_mode'] = C.get('cfo_mode', 'hard')
    d, I, tls, sect = E.load()
    base_rng, base_ok, TOPN, trig = E.prep_masks(d, I, C)
    cal = [str(x) for x in d['cal']]; S = [str(x) for x in d['sym']]
    t0 = next(k for k, c in enumerate(cal) if c >= start)
    t1 = len(cal) if not end else next((k for k, c in enumerate(cal) if c > end), len(cal))
    both = only_eng = only_live = 0; why = Counter(); ex = []
    F = ('PriceClose', 'PriceBasic', 'PriceHigh', 'PriceLow', 'Volume', 'TotalValue',
         'BuyQuantity', 'BuyCount', 'SellQuantity', 'SellCount', 'AdjClose', 'AdjHigh', 'AdjLow')
    for t in range(t0, t1):
        day = dt.date.fromisoformat(cal[t])
        eng = {r['sym'] for r in E.screen(t, d, I, tls, sect, C, TOPN, base_rng, base_ok, trig, day)}
        spec, U = SX.export(d, I, tls, sect, C, t - 1, next_day=day, syms_extra=eng)
        live = set()
        for s, sp in spec.items():
            j = JM[s]
            row = {k: (None if np.isnan(d[k][t, j]) else float(d[k][t, j])) for k in F}
            if row['PriceClose'] is None: continue
            res = SP.evaluate(sp, row, U, C)
            if res['all_ok']: live.add(s)
            elif s in eng:
                why.update(res['missing'])
                if len(ex) < 25: ex.append((cal[t], s, res['missing']))
        both += len(eng & live); only_eng += len(eng - live); only_live += len(live - eng)
        for s in live - eng:
            if len(ex) < 25: ex.append((cal[t], s, 'live-only'))
    out = dict(window=[start, end or cal[-1]], both=both, engine_only=only_eng, live_only=only_live,
               engine_only_reasons=dict(why), examples=ex)
    if verbose: print(json.dumps(out, ensure_ascii=False, indent=1))
    return out

d_, *_ = E.load(); JM = {str(s): k for k, s in enumerate(d_['sym'])}
if __name__ == '__main__':
    r = main(*(sys.argv[1:3] if len(sys.argv) > 1 else []))
    tot = r['both'] + r['engine_only'] + r['live_only']
    agree = r['both'] / tot if tot else 1.0
    print(f'PARITY agreement {agree:.1%}')
    sys.exit(0 if agree >= 0.95 else 1)
