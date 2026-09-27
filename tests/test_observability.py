# -*- coding: utf-8 -*-
"""R27A lop quan sat: chi hien thi, khong doi luat. Run: python3 tests/test_observability.py"""
import os, sys, json, datetime as dt
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
import observability as O

HAVE_DATA = os.path.exists('data/fa.npz') and os.path.exists('data/funda_raw2.json')
T = []
def test(fn): T.append(fn); return fn


def arr(closes, highs=None, lows=None):
    c = np.array(closes, dtype=float)[:, None]
    h = np.array(highs if highs else closes, dtype=float)[:, None]
    l = np.array(lows if lows else closes, dtype=float)[:, None]
    return c, h, l, c * 1000


@test
def test_path_t1_t3_mfe_mae_peak():
    AC, AH, AL, PX = arr([10, 10.5, 11, 11.5, 11.2], [10, 10.8, 11.2, 11.9, 11.4], [10, 9.8, 10.6, 11.1, 11.0])
    p = O.path_block(AC, AH, AL, PX, 0, 0, 4, 0.0015, cond9=True)
    assert p['ret_t1'] == 0.05 and p['ret_t2'] == 0.1 and p['ret_t3'] == 0.15 and p['ret_t5'] is None
    assert abs(p['mfe_since_entry'] - (11.9 / 10.015 - 1)) < 1e-3 and abs(p['mae_since_entry'] - (9.8 / 10.015 - 1)) < 1e-3
    assert abs(p['peak_gain'] - (11.5 / 10.015 - 1)) < 1e-3 and p['peak_gain'] >= p['gain_now']
    assert p['above_breakout_close'] and p['new_high_since_breakout'] and p['days_since_last_high'] == 1
    assert p['diagnostic_label'] == 'RUN_FAST' and p['diagnostic_only'] is True


@test
def test_path_missing_session_is_none_and_weak_label():
    AC, AH, AL, PX = arr([10, np.nan, 9.8, 9.7])
    p = O.path_block(AC, AH, AL, PX, 0, 0, 3, 0.0015)
    assert p['ret_t1'] is None and p['ret_t2'] == -0.02
    assert p['diagnostic_label'] == 'WEAK_BREAKOUT' and p['cond9_confirmed'] is None


@test
def test_path_stall_and_new():
    AC, AH, AL, PX = arr([10, 10.1, 10.05, 10.1, 10.12])
    assert O.path_block(AC, AH, AL, PX, 0, 0, 4, 0.0015)['diagnostic_label'] == 'STALL'
    assert O.path_block(AC, AH, AL, PX, 4, 0, 4, 0.0015)['diagnostic_label'] == 'NEW'


@test
def test_observability_outside_prod_and_rules():
    from produce2 import PROD
    assert not any(k in PROD for k in ('show_path', 'show_7of8', 'path', 'OBS', 'observability'))
    for f in ('engine2.py', 'exit_rules.py', 'allocator.py', 'signal_spec.py', 'publish.py', 'alerts2.py'):
        src = open(f, encoding='utf-8').read()
        assert 'observability' not in src and 'watch78' not in src and 'diagnostic_label' not in src, f
    js = open('site/exit_rules.js', encoding='utf-8').read() + open('site/p15.js', encoding='utf-8').read()
    assert 'diagnostic_label' not in js and 'obsPath' not in js      # nhan khong vao "Viec can lam"


@test
def test_watch78_matches_engine_and_never_buy():
    if not HAVE_DATA: print('   SKIP no data'); return
    import engine2 as E
    from produce2 import PROD
    C = dict(E.CFG); C.update(PROD)
    d, I, tls, sect = E.load(); b, bo, TOPN, trig = E.prep_masks(d, I, C); N = len(d['cal']); n78 = 0
    for i in range(N - 40, N):
        day = dt.date.fromisoformat(str(d['cal'][i]))
        rows = E.screen(i, d, I, tls, sect, C, TOPN, b, bo, trig, day, held=(), blocked=None, ignore_ordimb=True)
        e8 = {r['sym'] for r in rows}; e9 = {r['sym'] for r in rows if r['oi_ok']}
        W, _ = O.watch78(d, I, tls, sect, C, i)
        near = [r for r in W if r['kind'] == 'NEAR']; n78 += len(near)
        assert {r['symbol'] for r in W if r['kind'] == 'COND9_FAIL'} == e8 - e9          # 8/8 + Cond9 truot: dung bo may
        assert not ({r['symbol'] for r in near} & e8)                                    # 7/8 khong bao gio la tin hieu
        for r in near:
            bad = [g for g in r['gates'] if not g['ok']]
            assert len(bad) == 1 and bad[0]['gate'] in O.SOFT and r['passed'] == 7 and r['status'] == 'WATCH_ONLY'
            assert r['score'] >= C['score_floor']
        W2, _ = O.watch78(d, I, tls, sect, C, i, held=set(e8))
        assert not ({r['symbol'] for r in W2} & e8)
    print(f'   40 phien, {n78} luot gan dat')


@test
def test_watch78_not_in_published_signals():
    if not os.path.exists('data/site_data2.json'): print('   SKIP no build'); return
    D = json.load(open('data/site_data2.json'))
    ob = D.get('observability') or {}
    if ob.get('error'): raise AssertionError(ob['error'])
    w = {r['symbol'] for r in ob.get('watch78', [])}
    assert not (w & {s['sym'] for s in D.get('signals_today') or []})
    assert not (w & {p['sym'] for p in D.get('open_positions') or []})


if __name__ == '__main__':
    ok = 0
    for fn in T:
        try:
            fn(); print('PASS', fn.__name__); ok += 1
        except Exception as e:
            print('FAIL', fn.__name__, type(e).__name__, e)
    print(f'{ok}/{len(T)} passed'); sys.exit(0 if ok == len(T) else 1)
