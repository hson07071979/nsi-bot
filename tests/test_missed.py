# -*- coding: utf-8 -*-
"""R29 missed-winner audit: chi do, khong doi luat. Run: python3 tests/test_missed.py"""
import os, sys, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
import missed as M

HAVE_DATA = os.path.exists('data/fa.npz') and os.path.exists('data/funda_raw2.json')
T = []
def test(fn): T.append(fn); return fn


@test
def test_groups_and_buckets():
    assert M._grp('vol', 1.73) == 'vol_1.6-1.8' and M._grp('vol', 1.99) == 'vol_1.8-2.0' and M._grp('vol', 1.2) == 'vol_1.2-1.4'
    assert M._grp('pct', 0.004) == 'pct_0-1' and M._grp('pct', 0.015) == 'pct_1-2'
    assert M._grp('base', 0.25) == 'base_24-28' and M._grp('base', 0.30) == 'base_28-32'
    assert M._grp('cond9', 1.3) == 'cond9_1.2-1.4' and M._grp('cond9', 0.9) == 'cond9_<1.2'
    assert M._grp('cfo', None) == 'cfo' and set(M.ORDER) == set(M.GROUP_VI)


@test
def test_outside_prod_and_rules():
    from produce2 import PROD
    assert not any(k in PROD for k in ('missed', 'missed_audit', 'NEAR', 'OOS_FROM'))
    for f in ('engine2.py', 'exit_rules.py', 'allocator.py', 'signal_spec.py', 'alerts2.py', 'portfolio.py', 'live_scan.py'):
        if os.path.exists(f):
            src = open(f, encoding='utf-8').read()
            assert 'import missed' not in src and 'missed_audit' not in src, f


@test
def test_signal_group_matches_engine_screen():
    """Nhom SIGNAL + hai nhom Cond9 cua R29 phai TRUNG KHOP engine2.screen tung phien
    (do toan ky 28/09/2026: 376/376 va 172/172). Test chay 150 phien cuoi."""
    if not HAVE_DATA: print('   SKIP no data'); return
    import engine2 as E
    from produce2 import PROD
    C = dict(E.CFG); C.update(PROD)
    d, I, tls, sect = E.load(); cal = [str(x) for x in d['cal']]
    start = cal[-150]; cd = M.COOLDOWN; M.COOLDOWN = 0
    try:
        ev = M.events(d, I, tls, C, start=start)
    finally:
        M.COOLDOWN = cd
    m8 = {(e['date'], e['sym']) for e in ev if e['group'] in ('SIGNAL', 'cond9_1.2-1.4', 'cond9_<1.2')}
    m9 = {(e['date'], e['sym']) for e in ev if e['group'] == 'SIGNAL'}
    b, bo, TOPN, trig = E.prep_masks(d, I, C); e8 = set(); e9 = set()
    for i in range(len(cal) - 150, len(cal)):
        for r in E.screen(i, d, I, tls, sect, C, TOPN, b, bo, trig, dt.date.fromisoformat(cal[i]), ignore_ordimb=True):
            if r['oi'] != r['oi']: continue
            e8.add((cal[i], r['sym']))
            if r['oi_ok']: e9.add((cal[i], r['sym']))
    assert e8 == m8, (sorted(e8 - m8)[:5], sorted(m8 - e8)[:5])
    assert e9 == m9
    assert all(e['group'] in M.GROUP_VI for e in ev)
    print(f'   150 phien: {len(e8)} du 8 cong, {len(e9)} tin hieu, khop 100%')


@test
def test_forward_returns_net_of_fees():
    if not HAVE_DATA: print('   SKIP no data'); return
    import engine2 as E
    from produce2 import PROD
    C = dict(E.CFG); C.update(PROD)
    d, I, tls, sect = E.load(); cal = [str(x) for x in d['cal']]
    ev = [e for e in M.events(d, I, tls, C, start=cal[-400]) if e['t3'] is not None][:5]
    S = [str(x) for x in d['sym']]
    for e in ev:
        i = cal.index(e['date']); j = S.index(e['sym'])
        want = d['AdjClose'][i + 3, j] * (1 - C['fee_sell']) / (d['AdjClose'][i, j] * (1 + C['fee_buy'])) - 1
        assert abs(e['t3'] - want) < 1e-3, (e, want)


if __name__ == '__main__':
    ok = 0
    for fn in T:
        try:
            fn(); print('PASS', fn.__name__); ok += 1
        except Exception as e:
            print('FAIL', fn.__name__, type(e).__name__, e)
    print(f'{ok}/{len(T)} passed'); sys.exit(0 if ok == len(T) else 1)
