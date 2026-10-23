# -*- coding: utf-8 -*-
"""Luat toi da 1 lenh do treo (PROD 03/10/2026). Chay: python tests/test_max_unconf.py"""
import os, sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import allocator as AL
from produce2 import PROD

def test_prod_flag():
    assert PROD.get('max_unconf') == 1 and PROD.get('unconf_count') == 'both'

def test_allocator_helpers():
    assert not AL.unconf_blocked(0, PROD) and AL.unconf_blocked(1, PROD)
    assert not AL.unconf_blocked(5, {})                               # khong co luat -> khong chan
    assert AL.probe_hanging(dict(probe_fail=True, held=1), 3)
    assert not AL.probe_hanging(dict(probe_fail=True, held=2), 3, days_ahead=1)   # ban ATC hom nay
    assert not AL.probe_hanging(dict(probe_fail=False, held=0), 3)

def test_engine_never_two_hanging():
    # CI (tests.yml) khong cao du lieu -> bo qua phan chay bo may khi thieu data/fa.npz
    if not os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'fa.npz')):
        print('SKIP test_engine_never_two_hanging (chua co du lieu)'); return
    import engine2 as E
    r = E.run(PROD, log=True); tr = r['trades']
    ent = {}
    for t in tr: ent.setdefault(t['entry'], set()).add(t['sym'])
    # (a) khong bao gio mua 2 lenh do trong cung phien
    assert all(len(v) == 1 for v in ent.values()), [k for k, v in ent.items() if len(v) > 1][:5]
    # (b) khong mua khi dang giu mot lenh do da truot DK9 chua ban
    R = 'Cond9 không xác nhận'
    fail = [t for t in tr if t['reason'].startswith(R)]
    for t in tr:
        for f in fail:
            if f['sym'] != t['sym'] and f['entry'] < t['entry'] < f['exit']:
                raise AssertionError(f"mua {t['sym']} {t['entry']} khi {f['sym']} truot DK9 chua ban")

if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_'): f(); print('PASS', k); n += 1
    print(f'{n}/{n} passed')
