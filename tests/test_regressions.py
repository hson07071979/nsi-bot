# -*- coding: utf-8 -*-
"""Regression tests for bugs found in this project (run: python3 tests/test_regressions.py).
Plain asserts, no pytest dependency. Tests that need market data skip when
data/fa.npz is absent."""
import os, sys, json, re, random, importlib, types, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import allocator as AL
import signal_spec as SP

HAVE_DATA = os.path.exists('data/fa.npz') and os.path.exists('data/funda_raw2.json')
RESULTS = []


def test(fn):
    RESULTS.append(fn)
    return fn


# ---------------------------------------------------------------- allocator
@test
def test_allocator_sector_cap_binds_before_base_size():
    A = AL.entry_target(1e9, 1e9, 0, 0, 0, 'XANH', cfg={})
    assert abs(A['actual'] - 0.30e9) < 1, A          # 42% theoretical, 30% sector cap
    assert A['binding'] == 'sector_cap' and 'sector_cap' in A['reasons']
    assert abs(A['theoretical'] - 0.42e9) < 1


@test
def test_allocator_nan_total_cap():          # NaN exposure must not silently drop caps
    A = AL.entry_target(1e9, 1e9, float('nan'), 0.0, 0, 'XANH', cfg={})
    assert A['actual'] <= 0.30e9 + 1


@test
def test_allocator_max_pos_n_and_min_size():
    assert not AL.entry_target(1e9, 1e9, 0, 0, 12, 'XANH', cfg={})['ok']
    A = AL.entry_target(1e9, 0.01e9, 0.99e9, 0, 3, 'XANH', cfg={})
    assert not A['ok'] and A['binding'] in ('cash', 'max_total')


@test
def test_pyramid_respects_max_total_and_sector_cap():
    room, why = AL.addon_capacity(1e9, 0.5e9, 0.95e9, 0.10e9, 0.10e9, cfg={})
    assert abs(room - 0.05e9) < 1 and why == 'max_total'
    room, why = AL.addon_capacity(1e9, 0.5e9, 0.40e9, 0.29e9, 0.29e9, cfg={})
    assert abs(room - 0.01e9) < 1 and why == 'sector_cap'


@test
def test_pyramid_respects_max_pos_and_cash():
    C = AL.cfg_of({})
    room, why = AL.addon_capacity(1e9, 0.5e9, 0.30e9, 0.10e9, C['max_pos'] * 1e9 - 0.02e9, cfg={})
    assert abs(room - 0.02e9) < 1 and why == 'max_pos'
    room, why = AL.addon_capacity(1e9, 0.003e9, 0.30e9, 0.10e9, 0.05e9, cfg={})
    assert abs(room - 0.003e9) < 1 and why == 'cash'
    assert AL.addon_capacity(1e9, -1.0, 0.30e9, 0.10e9, 0.05e9, cfg={})[0] == 0.0


# ---------------------------------------------------------------- signal spec / Cond9
def _sp():
    return dict(thr=0.058, vol_s19=19e6, vol_c19=19, tv_s19=19 * 30e9, tv_c19=19,
                rng_s19=19 * 0.03, rng_c19=19, hi52_249=11000, c250=6000, c60=8000,
                shares=1e9, nbars=900, base=0.10, blocked=False, npat_yoy=0.5,
                pts_static=dict(C1=15, C2=15, C3=0, A1=10, A2=0), sector='X', rmul=1.0)


CFG = dict(vol_floor=2.0, gtgd_min=15e9, volat_min=0.015, min_mktcap=1000e9, min_history=250,
           base_range=0.22, score_floor=45, ordimb_min=1.40, use_ordimb=True, use_cond8=False,
           top_n=120, use_top_liquid=True)
U = dict(topn_cut=10e9, r12=sorted(random.Random(1).uniform(-0.5, 0.5) for _ in range(600)),
         r3=sorted(random.Random(2).uniform(-0.3, 0.3) for _ in range(600)))


def _row(bc=3000, sc=3000, bq=9e6, sq=6e6):
    return dict(PriceClose=10600, PriceBasic=10000, PriceHigh=10700, PriceLow=10000,
                Volume=5e6, TotalValue=53e9, BuyCount=bc, SellCount=sc, BuyQuantity=bq, SellQuantity=sq)


@test
def test_cond9_missing_is_never_mua():
    r = SP.evaluate(_sp(), _row(bc=0, sc=0), U, CFG)
    lvl, why = SP.classify(r, CFG)
    assert lvl == 'SAP_DU' and why == 'WAITING_FOR_FLOW_CONFIRMATION', (lvl, why, r['missing'])


@test
def test_cond9_below_threshold_is_not_mua():
    r = SP.evaluate(_sp(), _row(bq=6e6, sq=6e6), U, CFG)      # OrdImb 1.0
    assert 'ordimb' in r['missing'] and SP.classify(r, CFG)[0] != 'MUA'


@test
def test_all_conditions_is_mua():
    r = SP.evaluate(_sp(), _row(), U, CFG)                      # OrdImb 1.5
    assert r['all_ok'], r['missing']
    assert SP.classify(r, CFG) == ('MUA', None)


@test
def test_volume_ratio_includes_today_like_engine():
    sp = _sp()                      # prior 19 sessions average 1e6
    r = SP.evaluate(sp, dict(_row(), Volume=2.0e6), U, CFG)   # 2x prior mean but 1.905x incl. today
    assert not r['ok']['vol']
    r = SP.evaluate(sp, dict(_row(), Volume=2.2e6), U, CFG)
    assert r['ok']['vol']


@test
def test_publish_has_no_hardcoded_thresholds():
    src = open('publish.py', encoding='utf-8').read()
    assert 'ordimb_min=1.40' not in src and "ordimb_min=CF['ordimb_min']" in src


# ---------------------------------------------------------------- ranking
@test
def test_ranking_same_session_is_deterministic():
    import engine2 as E
    rows = [dict(sc=60.0, sym=s, base=0.1, oi=1.5, volr=3, rs=80, pct=0.07, sector='A') for s in 'ZYXWV']
    a = [r['sym'] for r in E.rank_rows(list(rows), 'score')]
    random.Random(3).shuffle(rows)
    b = [r['sym'] for r in E.rank_rows(list(rows), 'score')]
    assert a == b == sorted(a), (a, b)


# ---------------------------------------------------------------- frontend parity (static)
@test
def test_frontend_mua_requires_server_confirmation():
    p13 = open('site/p13.js', encoding='utf-8').read()
    assert 'svMua[sym]' in p13 and "if (cho && du5) lvl = 'MUA'" not in p13
    p11 = open('site/p11.js', encoding='utf-8').read()
    assert "if (cho && n === 5) lvl = 'MUA'" not in p11


@test
def test_holdings_rows_carry_own_book_and_nav():
    # System book (engine) is the main "current holdings"; paper book rows keep
    # THEIR OWN NAV as the % denominator (never the other book's NAV).
    p12 = open('site/p12.js', encoding='utf-8').read()
    for b in ("book_id: 'HE_THONG'", "book_id: 'SO_GHI_TIEN'", "book_id: 'TAY'"):
        assert b in p12, b
    assert "navGoc: ((D.prod || {}).metrics || {}).final_nav" in p12
    assert "navGoc: (F && F.nav) || null" in p12


@test
def test_no_stale_rule_numbers_in_site():
    for f in os.listdir('site'):
        if not f.endswith('.js'):
            continue
        s = open('site/' + f, encoding='utf-8').read()
        assert 'cỡ lệnh bán 20%' not in s, f
        assert "'Bán hết, áp dụng mọi phiên'" not in s, f


@test
def test_midnight_bell_guard_present():
    src = open(os.path.join(ROOT, '..', 'nguyensoninvest', 'live_scan.py'), encoding='utf-8').read() \
        if os.path.exists(os.path.join(ROOT, '..', 'nguyensoninvest', 'live_scan.py')) else None
    if src is None:
        return
    assert '9.0 <= t_bao <= 21.5' in src      # 09h-15h trong phien + xac nhan sau phien toi 21h30
    assert "h['level'] == 'MUA' and h.get('prod_ok')" in src


# ---------------------------------------------------------------- data-dependent
@test
def test_nan_total_cap_fix_default_on():
    import engine2 as E
    assert E.CFG['nan_tot_fix'] is True


@test
def test_prod_universe_top_n_single_source():
    from produce2 import PROD
    src = open('verify_build.py', encoding='utf-8').read()
    assert not re.search(r'^TOP_N\s*=\s*\d', src, re.M) and PROD['top_n'] == 110   # 105 -> 110 ngay 26/09/2026 (TOP110 + S1)


@test
def test_base_threshold_no_one_session_lag():
    if not HAVE_DATA:
        return
    import engine2 as E, spec_export as SX
    from produce2 import PROD
    C = dict(E.CFG); C.update(PROD)
    d, I, tls, sect = E.load()
    base_rng, *_ = E.prep_masks(d, I, C)
    t = len(d['cal']) - 5
    spec, U_ = SX.export(d, I, tls, sect, C, t - 1)
    S = [str(x) for x in d['sym']]
    k = 0
    for s, sp in spec.items():
        j = S.index(s)
        if sp['base'] is not None and base_rng[t, j] == base_rng[t, j]:
            assert abs(sp['base'] - float(base_rng[t, j])) < 1e-5, (s, sp['base'], base_rng[t, j])
            k += 1
    assert k > 50


@test
def test_cfo_only_cohort_classification():
    if not os.path.exists('data/site_data2.json'):
        return
    D = json.load(open('data/site_data2.json', encoding='utf-8'))
    for s, v in D['lookup'].items():
        if v.get('cfo_only'):
            assert v['block'] == 'CFO < 0' and not v['miss'], s


@test
def test_evidence_is_versioned():
    for f in os.listdir('evidence'):
        if f.startswith('audit_'):
            m = json.load(open('evidence/' + f, encoding='utf-8')).get('meta') or {}
            for k in ('git_sha', 'data_asof', 'prod_config_hash', 'generated', 'experiment_version'):
                assert k in m, (f, k)


@test
def test_cong_b_counts_unique_entries():
    src = open('cong_b.py', encoding='utf-8').read()
    assert 'DEALS = _deals(r0' in src and 'for t in DEALS:' in src


# ---------------------------------------------------------------- 25/09/2026 PROD change
@test
def test_cond1_threshold_single_source():
    import fa_ind
    from produce2 import PROD
    assert abs(PROD['trig_hose'] - fa_ind.THR_HOSE) < 1e-9 and abs(PROD['trig_hnx'] - fa_ind.THR_HNX) < 1e-9


@test
def test_dk5_off_is_not_required_and_never_blocks():
    off = dict(CFG, dk5_lo=0.0, dk5_hi=0.0)
    assert 'dk5' not in SP.required_conditions(off) and 'dk5' in SP.required_conditions(CFG)
    sp = dict(_sp(), npat_yoy=0.10)                       # inside the old weak band
    assert 'dk5' in SP.evaluate(sp, _row(), U, CFG)['missing']
    assert SP.evaluate(sp, _row(), U, off)['all_ok']


@test
def test_alerts_layer_reads_prod_not_hand_typed():
    src = open('alerts2.py', encoding='utf-8').read()
    assert 'CFG_LIVE = dict(base_range=' not in src and "_PM[k] for k in ('base_range'" in src


@test
def test_momentum_exit_rule():
    if not HAVE_DATA:
        return
    import engine2 as E
    from produce2 import PROD
    C = dict(E.CFG); C.update(PROD)
    r = E.run(C, log=False)
    mo = [t for t in r['trades'] if t['reason'].startswith('Momentum')]
    assert mo, 'momentum rule never fired'
    for t in mo:      # fired exactly at T+mo_by (or later only if not sellable), never after a +1% close
        assert t['held'] >= PROD['mo_by'] and t['peak'] < PROD['mo_need'] * 100 + 1e-6, t


@test
def test_probe_scheme_sells_only_when_shares_arrive():
    """PROD 25/09: buy at ATC without Cond9, confirm in the evening, sell failures at the T+2
    CLOSE (shares arrive the afternoon of T+2) — never earlier, never at an open."""
    if not HAVE_DATA:
        return
    import engine2 as E
    from produce2 import PROD
    assert PROD.get('stage1') == 1.0 and PROD.get('probe_exit') == 'close'
    sf = PROD.get('sell_from', 2); assert sf == 3 and PROD.get('hs_from') == 3
    C = dict(E.CFG); C.update(PROD)
    r = E.run(C, log=False)
    assert all(t['held'] >= sf for t in r['trades']), min(t['held'] for t in r['trades'])
    pr = [t for t in r['trades'] if t['reason'].startswith('Cond9')]
    assert pr and all(t['held'] == sf for t in pr), [t for t in pr if t['held'] != sf][:3]


if __name__ == '__main__':
    bad = 0
    for fn in RESULTS:
        try:
            fn(); print('PASS', fn.__name__)
        except Exception as e:
            bad += 1; print('FAIL', fn.__name__, type(e).__name__, e)
    print(f'{len(RESULTS) - bad}/{len(RESULTS)} passed')
    sys.exit(1 if bad else 0)
