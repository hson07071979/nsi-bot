# -*- coding: utf-8 -*-
"""TOP110 + S1 production tests (anh Son approved 26/09/2026).
Run: python3 tests/test_s1_prod.py   (plain asserts; data-dependent tests skip without data/fa.npz;
the JS parity test needs `node`, present on GitHub ubuntu runners)."""
import os, sys, json, re, shutil, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
import exit_rules as ER

HAVE_DATA = os.path.exists('data/fa.npz') and os.path.exists('data/funda_raw2.json')
S1 = [[0.08, 0.02], [0.12, 0.05]]
T1 = 'Khoá lãi S1 (đỉnh ≥8% → sàn +2%)'
T2 = 'Khoá lãi S1 (đỉnh ≥12% → sàn +5%)'
RESULTS = []


def test(fn):
    RESULTS.append(fn); return fn


def _cfg():
    import engine2 as E
    from produce2 import PROD
    C = dict(E.CFG); C.update(PROD); return C


@test
def test_prod_is_top110_s1_without_breakeven():
    from produce2 import PROD
    assert PROD['top_n'] == 110 and PROD['profit_lock'] == S1 and PROD['use_be'] is False, PROD
    assert ER.tiers(PROD) == [(0.08, 0.02), (0.12, 0.05)]            # no E2 15% / 19% tiers


@test
def test_s1_boundaries_and_priority():
    C = _cfg()
    d = lambda pk, g, h=5, **kw: ER.decide(C, g, pk, h, **kw)
    assert d(0.079, 0.01)['floor'] is None and d(0.079, 0.01)['rule'] is None        # 1. 7,9% -> no floor
    assert d(0.08, 0.02)['rule'] == T1                                                  # 2. 8,0% -> +2%
    assert d(0.119, 0.03)['floor'] == 0.02 and d(0.119, 0.03)['rule'] is None          # 3. 11,9% -> still +2%
    assert d(0.119, 0.02)['rule'] == T1
    assert d(0.12, 0.05)['rule'] == T2 and d(0.12, 0.051)['rule'] is None               # 4. 12,0% -> +5%
    assert d(0.15, 0.06)['floor'] == 0.05 and d(0.15, 0.06)['rule'] is None            # 5. 15% -> +5% only
    assert d(0.25, 0.15, b10=2)['rule'] == 'Trailing MA10 (lãi lớn)'                   # 6. MA10 still works
    assert d(0.30, 0.20, b20=2)['rule'] == 'Trailing MA30'
    for h in (1, 2):                                                                    # 7. T+1/T+2 no sale
        x = d(0.13, 0.04, h)
        assert x['rule'] is None and not x['sellable'] and x['pending'] == T2, x
    assert d(0.13, 0.04, 3)['rule'] == T2                                               # 8. sold at T+3
    assert d(0.09, -0.11)['rule'] == 'Hard stop −10%' and d(0.09, -0.08)['rule'] == 'Cắt lỗ −7%'
    assert d(0.09, -0.01)['rule'] == T1
    assert d(0.005, 0.0, 4)['rule'].startswith('Momentum')
    assert d(0.02, -0.001, 4)['rule'].startswith('Van thời gian')


@test
def test_action_text_examples():
    C = _cfg()
    a = ER.action_text(ER.decide(C, 0.018, 0.09, 4))
    b = ER.action_text(ER.decide(C, 0.047, 0.134, 5))
    c = ER.action_text(ER.decide(C, 0.048, 0.13, 2))
    print('   A:', a); print('   B:', b); print('   C:', c)
    assert a == 'BÁN ATC — KHOÁ LÃI: từng đạt +9,0%, hiện còn +1,8%, sàn bảo vệ +2%'
    assert b == 'BÁN ATC — KHOÁ LÃI: từng đạt +13,4%, hiện còn +4,7%, sàn bảo vệ +5%'
    assert c.startswith('CHỜ T+3 — KHOÁ LÃI ĐÃ THỦNG: từng đạt +13,0%, hiện +4,8% ≤ sàn +5%')


@test
def test_engine_backtest_uses_top110_and_s1():
    if not HAVE_DATA:
        print('   SKIP no data'); return
    import engine2 as E
    C = _cfg(); d, I, _, _ = E.load()
    TOPN = E.prep_masks(d, I, C)[2]
    assert int(TOPN.sum(axis=1).max()) <= 111
    r = E.run(C, log=False); rs = [t['reason'] for t in r['trades']]
    assert not any(x.startswith('Về bờ') for x in rs), 'breakeven +1% still active'
    assert T1 in rs and T2 in rs
    assert all(t['held'] >= C['sell_from'] for t in r['trades'] if t['reason'].startswith('Khoá lãi S1'))


@test
def test_exit_rules_replay_reproduces_every_engine_exit():
    """exit_rules.decide (portfolio.py / live_scan / website) replayed on the engine's own price
    paths must reproduce the engine exit day AND reason for every deal (pyramids excluded)."""
    if not HAVE_DATA:
        print('   SKIP no data'); return
    import engine2 as E, numpy as np
    C = _cfg(); r = E.run(C, log=False)
    d, I, R = r['d'], r['I'], r['R']; cal = [str(x) for x in r['cal']]
    J = {str(s): j for j, s in enumerate(d['sym'])}; AC = d['AdjClose']
    g = {}
    for t in r['trades']:
        g.setdefault((t['sym'], t['entry']), []).append(t)
    bad = []; n = 0
    for (sym, ent), rows in g.items():
        if any(t.get('pyr_date') for t in rows):
            continue
        j = J[sym]; ei = cal.index(ent); epx = AC[ei, j] * (1 + C['fee_buy'])
        probe = rows[-1]['reason'].startswith('Cond9')
        peak = 0.0; b10 = b20 = 0; part = False; fired = []
        for i in range(ei + 1, len(cal)):
            px = AC[i, j]
            if np.isnan(px):
                continue
            held = i - ei; gain = px / epx - 1; peak = max(peak, gain)
            m30, m10 = I['ma30'][i, j], I['ma10'][i, j]
            b20 = b20 + 1 if (not np.isnan(m30) and px < m30) else 0
            b10 = b10 + 1 if (not np.isnan(m10) and px < m10) else 0
            x = ER.decide(C, gain, peak, held, probe_fail=probe, b10=b10, b20=b20,
                          light_today=R['light'][i], light_entry=R['light'][ei], part=part)
            if x['rule']:
                fired.append((cal[i], x['rule']))
                if x['phan'] < 1:
                    part = True; continue
                break
        want = [(t['exit'], t['reason']) for t in sorted(rows, key=lambda t: t['exit'])]
        n += 1
        if fired != want:
            bad.append((sym, ent, want, fired))
    print(f'   replay {n} deals, {len(bad)} differ')
    assert not bad, f'{len(bad)}/{n} deals differ: {bad[:3]}'


@test
def test_js_exit_rules_match_python():
    """site/exit_rules.js (Việc cần làm) must give the SAME decision and SAME text as exit_rules.py."""
    if not shutil.which('node'):
        print('   SKIP node not installed'); return
    C = _cfg(); cases = []
    for pk in (0.0, 0.005, 0.02, 0.079, 0.08, 0.1, 0.119, 0.12, 0.134, 0.15, 0.19, 0.25):
        for gn in (-0.11, -0.08, -0.03, 0.0, 0.018, 0.02, 0.021, 0.047, 0.048, 0.05, 0.051, 0.09, 0.2):
            if gn > pk:
                continue
            for h in (1, 2, 3, 4, 6):
                for o in ({}, {'b10': 2}, {'b20': 2}, {'probe_fail': True}, {'light_today': 'CAM', 'light_entry': 'XANH'}):
                    cases.append(dict(pk=pk, g=gn, h=h, o=o))
    js = open('site/exit_rules.js', encoding='utf-8').read()
    tail = ("\nconst C=" + json.dumps(C, default=str) + ";\nconst K=" + json.dumps(cases) + ";\n"
            "process.stdout.write(JSON.stringify(K.map(k => { const d = erDecide(C, k.g, k.pk, k.h, k.o);"
            " return [d.rule, d.pending, d.sellable, d.floor, erActionText(d)]; })));")
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
        f.write(js + tail); fn = f.name
    try:
        out = json.loads(subprocess.run(['node', fn], capture_output=True, text=True, check=True).stdout)
    finally:
        os.unlink(fn)
    bad = []
    for k, jv in zip(cases, out):
        dd = ER.decide(C, k['g'], k['pk'], k['h'], **k['o'])
        pv = [dd['rule'], dd['pending'], dd['sellable'], dd['floor'], ER.action_text(dd)]
        if pv != jv:
            bad.append((k, pv, jv))
    print(f'   {len(cases)} cases compared')
    assert not bad, f'{len(bad)}/{len(cases)} differ, first: {bad[0]}'


@test
def test_no_stale_top105_or_breakeven_in_active_layers():
    for f in ('produce2.py', 'screener.py', 'alerts2.py', 'lookup.py', 'spec_export.py', 'verify_build.py'):
        assert not re.search(r'top_n\s*[=:]\s*105\b', open(f, encoding='utf-8').read()), f
    for f in ('site/p15.js', 'site/part6.js', 'site/p3.js', 'site/p12.js', 'site/part2.js', 'site/exit_rules.js'):
        src = open(f, encoding='utf-8').read()
        assert 'TOP 105' not in src and 'TOP105' not in src, f
    assert 'luật về bờ' not in open('site/p15.js', encoding='utf-8').read()
    assert "'exit_rules.py'" in open('publish.py', encoding='utf-8').read()
    assert 'exit_rules.py' in open('.github/workflows/daily.yml', encoding='utf-8').read()
    assert "'exit_rules.js'" in open('build_site2.py', encoding='utf-8').read()


if __name__ == '__main__':
    bad = 0
    for fn in RESULTS:
        try:
            fn(); print('PASS', fn.__name__)
        except Exception as e:
            bad += 1; print('FAIL', fn.__name__, type(e).__name__, e)
    print(f'{len(RESULTS) - bad}/{len(RESULTS)} passed')
    sys.exit(1 if bad else 0)
