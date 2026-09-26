# -*- coding: utf-8 -*-
"""PARITY: live signal_spec.evaluate() vs engine2.screen(), session by session.

For every session t of the window: export the spec from session t-1 (what the
nightly build publishes), build the session-t cross-section from the FireAnt rows
of t (what live_scan.py fetches: every symbol of U['xs']), feed evaluate() and
compare with engine2.screen(t).

HARD GATE (26/09/2026): production entry parity must be EXACT —
  engine_only == 0 AND live_only == 0 (an agreement percentage is informational
  only), and no production condition may disagree on any scanned symbol
  (cond_disagree == 0: a latent mismatch today is a false MUA tomorrow).
Every mismatch prints an ENGINE vs LIVE table: every condition, every CANSLIM
component, raw pre-rounding values, marked with <--.
Run: python3 tests/test_parity.py [start] [end]"""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from collections import Counter
import engine2 as E, engine as EN
import signal_spec as SP, spec_export as SX
from engine import canslim_score, as_of, risk_gate
from produce2 import PROD

F = ('PriceClose', 'PriceBasic', 'PriceHigh', 'PriceLow', 'Volume', 'TotalValue', 'MarketCap',
     'BuyQuantity', 'BuyCount', 'SellQuantity', 'SellCount', 'AdjClose', 'AdjHigh', 'AdjLow')
# research knobs evaluate() does not implement: must be OFF in PROD
UNSUPPORTED = ('ceil_vol_floor', 'pre_proxy', 'pre_set', 'oi_proxy', 'use_cond6', 'use_fnet', 'rs_min',
               'use_shelf', 'hard_ceiling', 'trig_pct')


def _fm(x):
    if isinstance(x, (bool, np.bool_)) or x is None or isinstance(x, str):
        return str(x)
    return '%.10g' % float(x)


class Ctx:
    def __init__(self, C):
        self.C = C
        self.d, self.I, self.tls, self.sect = E.load()
        self.base_rng, self.base_ok, self.TOPN, self.trig = E.prep_masks(self.d, self.I, C)
        self.OI = E._oi_arr(self.d, self.I, C)
        self.cal = [str(x) for x in self.d['cal']]
        self.S = [str(x) for x in self.d['sym']]
        self.JM = {s: k for k, s in enumerate(self.S)}
        AC = self.d['AdjClose']
        with np.errstate(divide='ignore', invalid='ignore'):
            self.r12 = np.full(AC.shape, np.nan, dtype=np.float32); self.r12[250:] = AC[250:] / AC[:-250] - 1
            self.r3 = np.full(AC.shape, np.nan, dtype=np.float32); self.r3[60:] = AC[60:] / AC[:-60] - 1

    def row(self, t, j):
        r = {k: (None if np.isnan(self.d[k][t, j]) else float(self.d[k][t, j])) for k in F}
        return None if all(v is None for v in r.values()) else r

    def engine(self, t, j, day):
        """Every production condition of engine2.screen() for (t, j), with values."""
        d, I, C = self.d, self.I, self.C
        AC, AH, AL, MC, TV = d['AdjClose'], d['AdjHigh'], d['AdjLow'], d['MarketCap'], d['TotalValue']
        s = self.S[j]
        tl = self.tls.get(s); f = as_of(tl, day) if tl else None
        ok = dict(uni=bool(self.TOPN[t, j]), pct=bool(self.trig[t, j]), vol=bool(I['volr'][t, j] >= C['vol_floor']),
                  gtgd=bool(TV[t, j] >= C['gtgd_min']), volat=bool(I['volat20'][t, j] >= C['volat_min']),
                  mcap=bool(MC[t, j] > C['min_mktcap']), hist=bool(I['nbars'][t, j] >= C['min_history']),
                  base=bool(self.base_ok[t, j]), cond8=not bool(AC[t, j] < (AH[t, j] + AL[t, j]) / 2),
                  ordimb=bool(self.OI[t, j] >= C['ordimb_min']))
        blk, why, _ = risk_gate(s, f) if f is not None else (True, 'Chua co BCTC', 0)
        ok['risk'] = not blk
        npg = f.get('npat_yoy') if f else None
        ok['dk5'] = not (npg is not None and C.get('dk5_lo', 0.0) <= npg < C.get('dk5_hi', 0.25))
        nh = float(AC[t, j] / I['hi52'][t, j] - 1) if I['hi52'][t, j] > 0 else None
        sc, pts = (canslim_score(f, I['rs'][t, j], I['mom3'][t, j], nh, float(I['volr'][t, j]),
                                 float(I['tvma20'][t, j])) if f else (None, {}))
        ok['score'] = sc is not None and not (sc < C['score_floor'])
        x = np.where(np.isnan(I['tvma20'][t]), -1.0, I['tvma20'][t]); m = min(int(C['top_n']), int((x > 0).sum()))
        v = dict(tvma20=float(I['tvma20'][t, j]), topn_cut=float(np.partition(x, -m)[-m]), pct=float(I['pct'][t, j]),
                 volr=float(I['volr'][t, j]), tv=float(TV[t, j]), volat=float(I['volat20'][t, j]),
                 mcap=float(MC[t, j]), nbars=int(I['nbars'][t, j]), base=float(self.base_rng[t, j]),
                 ordimb=float(self.OI[t, j]), rs=float(I['rs'][t, j]), mom=float(I['mom3'][t, j]),
                 r12=float(self.r12[t, j]), r3=float(self.r3[t, j]), near_high=nh,
                 score=(None if sc is None else float(sc)), pts=pts, risk_why=why if blk else '', npat_yoy=npg,
                 n_r12=int((~np.isnan(self.r12[t])).sum()), n_r3=int((~np.isnan(self.r3[t])).sum()))
        return ok, v


def table(ctx, tag, day, s, eok, ev, res, sp, X):
    """ENGINE vs LIVE, every condition and component; <-- marks a difference."""
    C = ctx.C
    lv = res.get('values') or {}; lok = res.get('ok') or {}
    lp = lv.get('pts') or {}; ep = ev.get('pts') or {}
    rows = [
        ('TOP%d' % C['top_n'], eok['uni'], lok.get('uni')),
        ('tvma20 (ty)', ev['tvma20'] / 1e9, None if lv.get('tvma20') is None else lv['tvma20'] / 1e9),
        ('TOP-N cut (ty)', ev['topn_cut'] / 1e9,
         (X['tv'][min(int(C['top_n']), len(X['tv'])) - 1] / 1e9) if X and X['tv'] else None),
        ('Pct', ev['pct'], lv.get('pct')), ('  thr', float(ctx.I['thr'][ctx.JM[s]]), sp['thr']),
        ('pct ok', eok['pct'], lok.get('pct')),
        ('VolRatio', ev['volr'], lv.get('volr')), ('vol ok', eok['vol'], lok.get('vol')),
        ('GTGD (ty)', ev['tv'] / 1e9, None), ('gtgd ok', eok['gtgd'], lok.get('gtgd')),
        ('Volat20', ev['volat'], lv.get('volat')), ('volat ok', eok['volat'], lok.get('volat')),
        ('MCap (ty)', ev['mcap'] / 1e9, None if lv.get('mcap') is None else lv['mcap'] / 1e9),
        ('mcap ok', eok['mcap'], lok.get('mcap')),
        ('nbars', ev['nbars'], lv.get('nbars')), ('hist ok', eok['hist'], lok.get('hist')),
        ('Base', ev['base'], sp.get('base')), ('base ok', eok['base'], lok.get('base')),
        ('OrdImb', ev['ordimb'], lv.get('ordimb')), ('ordimb ok', eok['ordimb'], lok.get('ordimb')),
        ('risk ok', eok['risk'], lok.get('risk')), ('  risk why', ev['risk_why'] or None, sp.get('block_why')),
        ('dk5 ok', eok['dk5'], lok.get('dk5')),
        ('r12 raw', ev['r12'], lv.get('r12')), ('RS', ev['rs'], lv.get('rs')),
        ('  n ranked r12', ev['n_r12'], len(X['r12']) if X else None),
        ('r3 raw', ev['r3'], lv.get('r3')), ('Mom pct', ev['mom'], lv.get('mom')),
        ('  n ranked r3', ev['n_r3'], len(X['r3']) if X else None),
        ('near 52w high', ev['near_high'], lv.get('near_high')),
    ]
    for k in SP.PTS_ORDER:
        rows.append(('%s points' % k, ep.get(k), lp.get(k)))
    rows += [('CANSLIM', ev['score'], lv.get('score')), ('score ok', eok['score'], lok.get('score'))]
    out = [f'{day} {s} {tag}', f'{"":22s}{"ENGINE":>22s}{"LIVE":>22s}']
    for name, a, b in rows:
        diff = b is not None and _fm(a) != _fm(b) and not name.startswith('  n ranked')
        out.append(f'{name:22s}{_fm(a):>22s}{_fm(b):>22s}' + ('   <--' if diff else ''))
    return '\n'.join(out)


def main(start='2023-01-01', end=None, cfg=None, verbose=True, max_tables=25, ctx=None):
    C = dict(E.CFG); C.update(PROD); C.update(cfg or {})
    for k in UNSUPPORTED:
        assert not C.get(k), f'{k} is on but signal_spec.evaluate() does not implement it'
    EN.CFG['cfo_mode'] = C.get('cfo_mode', 'hard')
    ctx = ctx or Ctx(C)
    cal, JM = ctx.cal, ctx.JM
    t0 = next(k for k, c in enumerate(cal) if c >= start)
    t1 = len(cal) if not end else next((k for k, c in enumerate(cal) if c > end), len(cal))
    req = SP.required_conditions(C)
    both = only_eng = only_live = 0
    why = Counter(); ex = []; tables = []; cond = Counter(); cond_ex = []; und = 0
    for t in range(t0, t1):
        day = dt.date.fromisoformat(cal[t])
        eng = {r['sym'] for r in E.screen(t, ctx.d, ctx.I, ctx.tls, ctx.sect, C, ctx.TOPN, ctx.base_rng,
                                          ctx.base_ok, ctx.trig, day)}
        spec, U = SX.export(ctx.d, ctx.I, ctx.tls, ctx.sect, C, t - 1, next_day=day, syms_extra=eng)
        rows = {s: ctx.row(t, JM[s]) for s in U['xs']}
        X = SP.cross_section(U, rows)
        live = set(); res_all = {}
        for s, sp in spec.items():
            row = rows.get(s) if s in rows else ctx.row(t, JM[s])
            if not row or row.get('PriceClose') is None:
                continue
            res = SP.evaluate(sp, row, U, C, X)
            res_all[s] = res
            und += bool(res.get('undetermined'))
            if res['all_ok']:
                live.add(s)
            elif s in eng:
                why.update(res['missing'])
            if res.get('valid'):
                eok, _ = ctx.engine(t, JM[s], day)
                for k in req:
                    if bool(eok[k]) != (res['ok'].get(k) is True):
                        cond[k] += 1
                        if len(cond_ex) < 40:
                            cond_ex.append((cal[t], s, k, bool(eok[k]), res['ok'].get(k)))
        both += len(eng & live); only_eng += len(eng - live); only_live += len(live - eng)
        for s in sorted(eng ^ live):
            tag = 'LIVE_ONLY' if s in live else 'ENGINE_ONLY'
            eok, ev = ctx.engine(t, JM[s], day)
            miss = res_all.get(s, {}).get('missing', ['no_row'])
            ex.append((cal[t], s, tag, [k for k in req if bool(eok[k]) != (res_all.get(s, {}).get('ok', {}).get(k) is True)] or miss))
            if len(tables) < max_tables:
                tables.append(table(ctx, tag, cal[t], s, eok, ev, res_all.get(s, {}), spec[s], X))
    tot = both + only_eng + only_live
    out = dict(window=[cal[t0], cal[t1 - 1]], both=both, engine_only=only_eng, live_only=only_live,
               agreement=(both / tot if tot else 1.0), engine_only_reasons=dict(why), examples=ex,
               cond_disagree=sum(cond.values()), cond_disagree_by=dict(cond), cond_examples=cond_ex,
               undetermined=und, tables=tables)
    out['ok'] = (only_eng == 0 and only_live == 0 and out['cond_disagree'] == 0 and und == 0)
    if verbose:
        for tb in tables:
            print('\n' + tb)
        print(json.dumps({k: v for k, v in out.items() if k != 'tables'}, ensure_ascii=False, indent=1))
    return out


if __name__ == '__main__':
    r = main(*(sys.argv[1:3] if len(sys.argv) > 1 else []))
    print(f"PARITY {r['window'][0]}..{r['window'][1]}: {r['both']} khop, {r['engine_only']} chi engine, "
          f"{r['live_only']} chi live, {r['cond_disagree']} lech dieu kien "
          f"(thong tin: {r['agreement']:.1%}) -> {'DAT' if r['ok'] else 'TRUOT'}")
    sys.exit(0 if r['ok'] else 1)
