# -*- coding: utf-8 -*-
"""Luat toi da 2 lenh do treo (PROD 23/10/2026; max 1 tu 03/10). Chay: python tests/test_max_unconf.py"""
import os, sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import allocator as AL
from produce2 import PROD

LIM = 2


def test_prod_flag():
    assert PROD.get('max_unconf') == LIM and PROD.get('unconf_count') == 'both'


def test_allocator_helpers():
    assert not AL.unconf_blocked(0, PROD) and not AL.unconf_blocked(1, PROD)
    assert AL.unconf_blocked(2, PROD) and AL.unconf_blocked(3, PROD)
    assert AL.unconf_blocked(1, dict(max_unconf=1))                   # nam van dung khi cfg = 1
    assert not AL.unconf_blocked(5, {})                               # khong co luat -> khong chan
    assert AL.probe_hanging(dict(probe_fail=True, held=1), 3)
    assert not AL.probe_hanging(dict(probe_fail=True, held=2), 3, days_ahead=1)   # ban ATC hom nay
    assert not AL.probe_hanging(dict(probe_fail=False, held=0), 3)


def test_engine_never_over_limit():
    # CI (tests.yml) khong cao du lieu -> bo qua phan chay bo may khi thieu data/fa.npz
    if not os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'fa.npz')):
        print('SKIP test_engine_never_over_limit (chua co du lieu)'); return
    import engine2 as E
    r = E.run(PROD, log=True); tr = r['trades']
    R = 'Cond9 không xác nhận'
    fail = [t for t in tr if t['reason'].startswith(R)]
    first = {}
    for t in tr:                                    # moi deal tinh mot lan (dong lenh ban tung phan)
        first.setdefault((t['sym'], t['entry']), t)
    deals = list(first.values())
    for t in deals:
        # so lenh do treo luc mua t: mua cung phien truoc t + da truot DK9 chua ban
        cung_phien = [d for d in deals if d['entry'] == t['entry'] and d['sym'] != t['sym']]
        treo = [f for f in fail if f['sym'] != t['sym'] and f['entry'] < t['entry'] < f['exit']]
        assert len({d['sym'] for d in cung_phien}) + len({f['sym'] for f in treo}) < LIM, \
            f"mua {t['sym']} {t['entry']} khi da co {len(cung_phien)} cung phien + {len(treo)} truot DK9"
    # moi phien mua toi da LIM lenh do
    ent = {}
    for d in deals: ent.setdefault(d['entry'], set()).add(d['sym'])
    assert all(len(v) <= LIM for v in ent.values()), [k for k, v in ent.items() if len(v) > LIM][:5]


if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_'): f(); print('PASS', k); n += 1
    print(f'{n}/{n} passed')
