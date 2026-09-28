# -*- coding: utf-8 -*-
"""KHOA CONG CFO (R29, 28/09/2026). engine.risk_gate co cac nut NGHIEN CUU
(cfo_mode = off / warn / sector / repeat / growth / sector_growth — R28). Chung chi duoc
ton tai cho research/. PROD, trang web, chuong va moi lop song PHAI la 'hard'.
Run: python3 tests/test_cfo_lock.py"""
import os, sys, re, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
T = []
def test(fn): T.append(fn); return fn

LIVE = ('produce2.py', 'alerts2.py', 'screener.py', 'watchlist.py', 'lookup.py', 'live_scan.py', 'signal_spec.py',
        'allocator.py', 'exit_rules.py', 'portfolio.py', 'observability.py', 'missed.py', 'build_site2.py',
        'publish.py', 'robustness.py', 'cong_b.py', 'vithe.py', 'verify_build.py')


@test
def test_defaults_are_hard():
    import engine as EN, engine2 as E
    assert EN.CFG.get('cfo_mode', 'hard') == 'hard'
    assert E.CFG['cfo_mode'] == 'hard'


@test
def test_prod_and_presets_hard():
    import produce2 as P
    assert P.PROD.get('cfo_mode', 'hard') == 'hard', 'PROD bat cfo_mode khac hard'
    for k, (_, ov) in P.PRESETS.items():
        assert 'cfo_mode' not in ov, f'preset {k} doi cfo_mode'
    assert 'cfo_mode' not in P.STRICT


@test
def test_no_live_file_sets_research_mode():
    # chi duoc DOC cfo_mode (ghi ra cfg_prod / kiem), khong duoc GAN gia tri khac 'hard'
    bad = re.compile(r"cfo_mode['\"]?\s*[:=]\s*['\"](?!hard)")
    for f in LIVE + tuple(glob.glob('site/*.js')):
        if not os.path.exists(f): continue
        src = open(f, encoding='utf-8').read()
        assert not bad.search(src), f'{f} gan cfo_mode khac hard'
    for f in glob.glob('site/*.js'):
        assert 'cfo_mode' not in open(f, encoding='utf-8').read() or f.endswith('p14.js'), f


@test
def test_run_does_not_leak_mode():
    """engine2.run ghi cfo_mode vao engine.CFG (bien toan cuc). Chay mot cau hinh nghien cuu
    xong, lan chay PROD ke tiep va risk_gate phai tro lai 'hard'."""
    import engine as EN, engine2 as E
    f = dict(cfo_ttm=-1e9, icr=10.0, de=0.5)
    try:
        if os.path.exists('data/fa.npz') and os.path.exists('data/funda_raw2.json'):
            from produce2 import PROD
            E.run(dict(PROD, cfo_mode='off', cfo_warn_mul=0.35), log=False)   # chay nghien cuu that
        else:
            EN.CFG['cfo_mode'] = 'off'; E.reset_research_state()
        assert EN.CFG['cfo_mode'] == 'hard', 'reset_research_state khong dua cfo_mode ve hard'
        assert EN.risk_gate('ABC', f)[0] is True, 'CFO am khong bi chan sau khi reset'
    finally:
        EN.CFG['cfo_mode'] = 'hard'


@test
def test_risk_gate_modes():
    import engine as EN
    f = dict(cfo_ttm=-1e9, icr=10.0, de=0.5, rev_yoy=0.5)
    try:
        EN.CFG['cfo_mode'] = 'hard'; assert EN.risk_gate('ABC', f)[:2] == (True, 'CFO < 0')
        EN.CFG['cfo_mode'] = 'growth'; EN.CFG['cfo_warn_mul'] = 0.5; EN.CFG['cfo_growth_min'] = 0.3
        assert EN.risk_gate('ABC', f)[0] is False
        assert EN.risk_gate('ABC', dict(f, rev_yoy=0.1))[0] is True
        EN.CFG['cfo_mode'] = 'nonsense'; assert EN.risk_gate('ABC', f)[0] is True   # mode la -> chan
    finally:
        EN.CFG['cfo_mode'] = 'hard'; EN.CFG['cfo_warn_mul'] = 0.5; EN.CFG['cfo_growth_min'] = 0.3


if __name__ == '__main__':
    ok = 0
    for fn in T:
        try:
            fn(); print('PASS', fn.__name__); ok += 1
        except Exception as e:
            print('FAIL', fn.__name__, type(e).__name__, e)
    print(f'{ok}/{len(T)} passed'); sys.exit(0 if ok == len(T) else 1)
