# -*- coding: utf-8 -*-
"""DIAGNOSTIC ONLY (not a gate): locate the exact live<->engine parity mismatch.

For every session t of the window it replays tests/test_parity.py exactly
(spec exported at t-1, FireAnt row of t) and additionally:
  * prints, for EVERY mismatch, an ENGINE vs LIVE table of every condition and
    every CANSLIM component with raw (pre-rounding) values;
  * counts condition-level disagreements over ALL scanned symbols, even where the
    final verdict happens to agree (latent mismatches);
  * replays hypotheses: H_RSMOM = live, but RS / Mom taken from the engine's
    session-t cross-section; H_TOPN = live, but TOP-N from the engine's session-t
    ranking; H_BOTH = both;
  * audits fa_ind.pct_rank (argsort-argsort / (n-1)) against the min-rank
    definition (bisect_left over the OTHER symbols / (n-1)) for ties.
Run: python3 tests/parity_diag.py [start] [end]
"""
import sys, os, json, bisect, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from collections import Counter
import engine2 as E, engine as EN
import signal_spec as SP, spec_export as SX
from engine import canslim_score, as_of, risk_gate
from produce2 import PROD

F = ('PriceClose', 'PriceBasic', 'PriceHigh', 'PriceLow', 'Volume', 'TotalValue',
     'BuyQuantity', 'BuyCount', 'SellQuantity', 'SellCount', 'AdjClose', 'AdjHigh', 'AdjLow')


def f32(x):
    return float(np.float32(x))


def main(start, end, max_tables=40):
    C = dict(E.CFG); C.update(PROD)
    EN.CFG['cfo_mode'] = C.get('cfo_mode', 'hard')
    d, I, tls, sect = E.load()
    base_rng, base_ok, TOPN, trig = E.prep_masks(d, I, C)
    OI = E._oi_arr(d, I, C)
    cal = [str(x) for x in d['cal']]; S = [str(x) for x in d['sym']]; JM = {s: k for k, s in enumerate(S)}
    AC, AH, AL, MC, TV = d['AdjClose'], d['AdjHigh'], d['AdjLow'], d['MarketCap'], d['TotalValue']
    r12A = np.full(AC.shape, np.nan, dtype=np.float32); r12A[250:] = AC[250:] / AC[:-250] - 1
    r3A = np.full(AC.shape, np.nan, dtype=np.float32); r3A[60:] = AC[60:] / AC[:-60] - 1
    print('data', cal[0], '->', cal[-1], 'syms', len(S), 'PROD top_n', C.get('top_n'),
          'use_cond6', C.get('use_cond6'), 'use_fnet', C.get('use_fnet'), 'rs_min', C.get('rs_min'),
          'use_shelf', C.get('use_shelf'), 'oi_proxy', C.get('oi_proxy'), flush=True)
    t0 = next(k for k, c in enumerate(cal) if c >= start)
    t1 = len(cal) if not end else next((k for k, c in enumerate(cal) if c > end), len(cal))
    req = SP.required_conditions(C)
    cnt = Counter(); cond_dis = Counter(); cond_ex = {}
    tables = 0

    def eng_cond(t, j, day):
        s = S[j]
        tl = tls.get(s); f = as_of(tl, day) if tl else None
        ok = dict(uni=bool(TOPN[t, j]), pct=bool(trig[t, j]), vol=bool(I['volr'][t, j] >= C['vol_floor']),
                  gtgd=bool(TV[t, j] >= C['gtgd_min']), volat=bool(I['volat20'][t, j] >= C['volat_min']),
                  mcap=bool(MC[t, j] > C['min_mktcap']), hist=bool(I['nbars'][t, j] >= C['min_history']),
                  base=bool(base_ok[t, j]), cond8=bool(AC[t, j] >= (AH[t, j] + AL[t, j]) / 2),
                  ordimb=bool(OI[t, j] >= C['ordimb_min']))
        blk, why, _ = risk_gate(s, f) if f is not None else (True, 'Chua co BCTC', 0)
        ok['risk'] = not blk
        npg = f.get('npat_yoy') if f else None
        ok['dk5'] = not (npg is not None and C.get('dk5_lo', 0.0) <= npg < C.get('dk5_hi', 0.25))
        sc, pts = (canslim_score(f, I['rs'][t, j], I['mom3'][t, j],
                                 float(AC[t, j] / I['hi52'][t, j] - 1) if I['hi52'][t, j] > 0 else None,
                                 float(I['volr'][t, j]), float(I['tvma20'][t, j])) if f else (None, {}))
        ok['score'] = sc is not None and sc >= C['score_floor']
        x = np.where(np.isnan(I['tvma20'][t]), -1.0, I['tvma20'][t]); m = min(int(C['top_n']), int((x > 0).sum()))
        cut = float(np.partition(x, -m)[-m])
        v = dict(tvma20=float(I['tvma20'][t, j]), topn_cut=cut, pct=float(I['pct'][t, j]), thr=None,
                 volr=float(I['volr'][t, j]), tv=float(TV[t, j]), volat=float(I['volat20'][t, j]),
                 mcap=float(MC[t, j]), nbars=int(I['nbars'][t, j]), base=float(base_rng[t, j]),
                 ordimb=float(OI[t, j]), rs=float(I['rs'][t, j]), mom=float(I['mom3'][t, j]),
                 r12=float(r12A[t, j]), r3=float(r3A[t, j]),
                 near_high=(float(AC[t, j] / I['hi52'][t, j] - 1) if I['hi52'][t, j] > 0 else None),
                 score=sc, pts=pts, risk_why=why if blk else '', npat_yoy=npg,
                 n_r12=int((~np.isnan(r12A[t])).sum()), n_r3=int((~np.isnan(r3A[t])).sum()))
        return ok, v

    def table(tag, day, s, eok, ev, lres, sp, U):
        lv = lres.get('values') or {}; lok = lres.get('ok') or {}
        lp = lv.get('pts') or {}; ep = ev.get('pts') or {}
        r12l = (float(lres['_ac']) / sp['c250'] - 1) if sp.get('c250') else None
        r3l = (float(lres['_ac']) / sp['c60'] - 1) if sp.get('c60') else None
        rows = [
            ('TOP%d' % C['top_n'], eok['uni'], lok.get('uni')),
            ('tvma20 (ty)', ev['tvma20'] / 1e9, (lv.get('tvma20') or float('nan')) / 1e9),
            ('TOP-N cut (ty)', ev['topn_cut'] / 1e9, U['topn_cut'] / 1e9),
            ('Pct', ev['pct'], lv.get('pct')), ('  thr', float(I['thr'][JM[s]]), sp['thr']),
            ('pct ok', eok['pct'], lok.get('pct')),
            ('VolRatio', ev['volr'], lv.get('volr')), ('vol ok', eok['vol'], lok.get('vol')),
            ('GTGD (ty)', ev['tv'] / 1e9, None), ('gtgd ok', eok['gtgd'], lok.get('gtgd')),
            ('Volat20', ev['volat'], lv.get('volat')), ('volat ok', eok['volat'], lok.get('volat')),
            ('MCap (ty)', ev['mcap'] / 1e9, (lv.get('mcap') or 0) / 1e9), ('mcap ok', eok['mcap'], lok.get('mcap')),
            ('nbars', ev['nbars'], sp.get('nbars')), ('hist ok', eok['hist'], lok.get('hist')),
            ('Base', ev['base'], sp.get('base')), ('base ok', eok['base'], lok.get('base')),
            ('OrdImb', ev['ordimb'], lv.get('ordimb')), ('ordimb ok', eok['ordimb'], lok.get('ordimb')),
            ('risk ok', eok['risk'], lok.get('risk')), ('  risk why', ev['risk_why'], sp.get('block_why')),
            ('dk5 ok', eok['dk5'], lok.get('dk5')), ('  npat_yoy', ev['npat_yoy'], sp.get('npat_yoy')),
            ('r12 raw', ev['r12'], r12l), ('RS', ev['rs'], lv.get('rs')),
            ('  n ranked r12', ev['n_r12'], len(U.get('r12') or [])),
            ('r3 raw', ev['r3'], r3l), ('Mom pct', ev['mom'], lres.get('_mom')),
            ('  n ranked r3', ev['n_r3'], len(U.get('r3') or [])),
            ('near 52w high', ev['near_high'], lv.get('near_high')),
        ]
        for k in ('C1', 'C2', 'C3', 'A1', 'A2', 'N', 'S', 'L', 'I', 'Mom'):
            rows.append(('%s points' % k, ep.get(k), lp.get(k)))
        rows += [('CANSLIM', ev['score'], lv.get('score')), ('score ok', eok['score'], lok.get('score'))]
        print(f'\n{day} {s} {tag}\n{"":22s}{"ENGINE":>22s}{"LIVE":>22s}')
        for name, a, b in rows:
            def fm(x):
                if isinstance(x, (bool, np.bool_)) or x is None or isinstance(x, str):
                    return str(x)
                return '%.10g' % x
            diff = (fm(a) != fm(b)) and b is not None and not name.startswith('  n ranked')
            print(f'{name:22s}{fm(a):>22s}{fm(b):>22s}' + ('   <--' if diff else ''))

    ties = dict(rows_with_ties=0, cells_rank_differs=0, cand_L_flip=0, cand_mom_diff=0)
    for t in range(t0, t1):
        day = dt.date.fromisoformat(cal[t])
        eng = {r['sym'] for r in E.screen(t, d, I, tls, sect, C, TOPN, base_rng, base_ok, trig, day)}
        spec, U = SX.export(d, I, tls, sect, C, t - 1, next_day=day, syms_extra=eng)
        live = set(); hR = set(); hT = set(); hB = set()
        res_all = {}
        for s, sp in spec.items():
            j = JM[s]
            row = {k: (None if np.isnan(d[k][t, j]) else float(d[k][t, j])) for k in F}
            if row['PriceClose'] is None:
                continue
            res = SP.evaluate(sp, row, U, C)
            if not res.get('valid'):
                continue
            res['_ac'] = row['AdjClose'] or row['PriceClose']
            r3l = (res['_ac'] / sp['c60'] - 1) if sp.get('c60') else None
            res['_mom'] = SP._pct_rank(r3l, U.get('r3'))
            res_all[s] = res
            if res['all_ok']:
                live.add(s)
            # hypotheses: swap in the engine's session-t cross-sectional values
            pts = dict(res['values']['pts'])
            miss = set(res['missing'])
            def verdict(p, uni_ok):
                sc = sum(p.values()); m = set(miss) - {'score', 'uni'}
                if sc < C['score_floor']: m.add('score')
                if not uni_ok: m.add('uni')
                return not m
            pR = dict(pts)
            rs_e = I['rs'][t, j]; mo_e = I['mom3'][t, j]
            pR['L'] = 15 if (not np.isnan(rs_e) and rs_e >= 70) else 0
            pR['Mom'] = round(5 * (float(mo_e) if not np.isnan(mo_e) else 0.0), 1)
            if verdict(pR, res['ok']['uni']): hR.add(s)
            if verdict(pts, bool(TOPN[t, j])): hT.add(s)
            if verdict(pR, bool(TOPN[t, j])): hB.add(s)
            # condition-level parity on every scanned symbol
            eok, ev = eng_cond(t, j, day)
            for k in req + ['cond8']:
                if k in eok and k in res['ok'] and bool(eok[k]) != bool(res['ok'][k]):
                    cond_dis[k] += 1
                    cond_ex.setdefault(k, []).append((cal[t], s))
            if (res['values']['pts'] or {}) and ev['pts']:
                for k in ('L', 'Mom', 'N', 'S', 'I'):
                    if ev['pts'].get(k) != res['values']['pts'].get(k):
                        cond_dis['pts_' + k] += 1
                        if len(cond_ex.setdefault('pts_' + k, [])) < 30:
                            cond_ex['pts_' + k].append((cal[t], s, ev['pts'].get(k), res['values']['pts'].get(k)))
        cnt['both'] += len(eng & live); cnt['engine_only'] += len(eng - live); cnt['live_only'] += len(live - eng)
        for tag, H in (('H_RSMOM', hR), ('H_TOPN', hT), ('H_BOTH', hB)):
            cnt[tag + '_both'] += len(eng & H); cnt[tag + '_eng_only'] += len(eng - H); cnt[tag + '_live_only'] += len(H - eng)
        for s in sorted(eng ^ live):
            j = JM[s]
            eok, ev = eng_cond(t, j, day)
            tag = 'LIVE_ONLY' if s in live else 'ENGINE_ONLY'
            if tables < max_tables:
                table(tag, cal[t], s, eok, ev, res_all.get(s, {}), spec[s], U); tables += 1
        # tie audit (engine pct_rank vs min-rank over the other symbols)
        for A, key in ((r12A, 'rs'), (r3A, 'mom3')):
            row = A[t]; m = ~np.isnan(row)
            if m.sum() < 40: continue
            v = row[m]
            if len(np.unique(v)) != len(v):
                ties['rows_with_ties'] += 1
                sv = np.sort(v)
                mn = np.searchsorted(sv, v, side='left') / (len(v) - 1)
                cur = v.argsort().argsort() / (len(v) - 1)
                dif = (mn.astype(np.float32) != cur.astype(np.float32))
                ties['cells_rank_differs'] += int(dif.sum())
    print('\n==== RESULT', json.dumps(dict(window=[cal[t0], cal[t1 - 1]], **cnt), indent=1))
    print('==== condition-level disagreements over ALL scanned symbols:', dict(cond_dis))
    for k, v in cond_ex.items():
        print('  ', k, v[:30])
    print('==== tie audit', ties, flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    for w in (a[0].split(',') if a else ['2023-01-01']):
        st, _, en = w.partition(':')
        print('\n\n######## WINDOW', st, en or 'latest', flush=True)
        main(st, en or None)
