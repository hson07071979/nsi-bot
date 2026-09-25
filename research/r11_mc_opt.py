# -*- coding: utf-8 -*-
"""R11 — Coordinate-descent optimisation with Monte Carlo robustness (anh Son 25/09).
Order: base_range -> ordimb_min -> score_floor -> Cond1..Cond8. One knob at a time,
everything else held at the current best. A change is ACCEPTED only if it is robust:
  * MC-exec: median total return over N random-miss runs (10% of entries missed) beats
    the incumbent by >= 2% (relative), and its p10 is not worse;
  * plateau: the mean MC median of the two grid neighbours also beats the incumbent;
  * block bootstrap (20-day blocks, 2000 paths) DD p95 not worse by > 1.0 pp;
  * realised max DD not worse by > 1.0 pp and <= 12%;
  * 2023-26 return not worse than incumbent (recent regime must not pay for it),
    2019-22 not worse by > 10% relative, full-period return not lower.
Results cached in evidence/r11_cache.json (resumable)."""
import os, sys, json, time, hashlib
import numpy as np
from multiprocessing import Pool
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
CACHE = os.environ.get('CACHE', 'evidence/r11_cache.json')
OUT = os.environ.get('OUT', 'evidence/r11_progress.json')
NSEED = int(os.environ.get('NSEED', 60))

def _key(c): return hashlib.md5(json.dumps(c, sort_keys=True, default=str).encode()).hexdigest()[:16]

_E = None
def _init():
    global _E
    import engine2 as E; E.load(); _E = E

def _seg(eq, a, b):
    v = np.array([x[1] for x in eq if a <= x[0][:4] <= b], float)
    return float(v[-1] / v[0] - 1) if len(v) > 20 else None

def _boot(eq, n=2000, blk=20, seed=7):
    v = np.array([x[1] for x in eq], float); r = v[1:] / v[:-1] - 1; T = len(r)
    rng = np.random.default_rng(seed); dds = []; rets = []
    nb = T // blk + 1
    for _ in range(n):
        st = rng.integers(0, T - blk, nb); p = np.concatenate([r[s:s + blk] for s in st])[:T]
        nav = np.cumprod(1 + p); dd = 1 - nav / np.maximum.accumulate(nav)
        dds.append(dd.max()); rets.append(nav[-1] - 1)
    dds = np.array(dds); rets = np.array(rets)
    return dict(dd_p50=float(np.median(dds)), dd_p95=float(np.quantile(dds, .95)),
                p_dd20=float((dds > .20).mean()), ret_p05=float(np.quantile(rets, .05)), ret_p50=float(np.median(rets)))

def evaluate(over):
    E = _E
    from produce2 import PROD
    C = dict(E.CFG); C.update(PROD); C.update(over)
    r = E.run(C, log=False); m = E.metrics(r)
    try:
        from dealstats import stats as ds
        deals = ds(r['trades']).get('deals')
    except Exception:
        deals = None
    out = dict(over=over, ret=m['total_return'], cagr=m['cagr'], dd=m['maxdd'], pf=m['pf'], sharpe=m['sharpe'],
               trades=m['trades'], deals=deals, h1=_seg(r['eq'], '2019', '2022'), h2=_seg(r['eq'], '2023', '2026'))
    out.update(_boot(r['eq']))
    mc = []
    for s in range(NSEED):
        C2 = dict(C); C2.update(miss_prob=0.10, miss_seed=1000 + s)
        mc.append(E.metrics(E.run(C2, log=False))['total_return'])
    mc = np.array(mc)
    out.update(mc_p50=float(np.median(mc)), mc_p10=float(np.quantile(mc, .10)), mc_p90=float(np.quantile(mc, .90)))
    return out

def load_cache():
    try: return json.load(open(CACHE))
    except Exception: return {}

def run_grid(pool, cache, base, knob, grid, extra=None):
    todo = []
    for v in grid:
        o = dict(base); o[knob] = v
        if extra: o.update(extra(v))
        if _key(o) not in cache: todo.append(o)
    for res in pool.imap_unordered(evaluate, todo):
        cache[_key(res['over'])] = res
        json.dump(cache, open(CACHE, 'w'))
        print(f"  {knob}={res['over'][knob]}: ret {res['ret']*100:.1f}% dd {res['dd']*100:.2f}% pf {res['pf']} "
              f"mc50 {res['mc_p50']*100:.1f}% mc10 {res['mc_p10']*100:.1f}% ddp95 {res['dd_p95']*100:.1f}%", flush=True)
    rows = []
    for v in grid:
        o = dict(base); o[knob] = v
        if extra: o.update(extra(v))
        rows.append(cache[_key(o)])
    return rows

def accept(rows, inc, knob):
    """Return (best_row, reason). inc = incumbent row (current value)."""
    best, why = inc, 'giữ (không biến thể nào vượt đủ điều kiện bền vững)'
    for k, r in enumerate(rows):
        if r is inc or r['over'].get(knob) == inc['over'].get(knob): continue
        if r['mc_p50'] < inc['mc_p50'] * 1.02: continue
        if r['mc_p10'] < inc['mc_p10']: continue
        if r['dd_p95'] > inc['dd_p95'] + 0.01: continue
        # realised max drawdown: at most +1.0 pp vs incumbent and never above 12% (15% pain limit incl. slippage)
        if r['dd'] > inc['dd'] + 0.010 or r['dd'] > 0.12: continue
        # must not lose in the RECENT half (2023-26) and not collapse in 2019-22
        if (r['h2'] or 0) < (inc['h2'] or 0) or (r['h1'] or 0) < (inc['h1'] or 0) * 0.9: continue
        if r['ret'] < inc['ret']: continue
        nb = [rows[j]['mc_p50'] for j in (k - 1, k + 1) if 0 <= j < len(rows)]
        if not nb or np.mean(nb) < inc['mc_p50']: continue
        if best is inc or r['mc_p50'] > best['mc_p50']:
            best, why = r, f"đổi: MC trung vị {inc['mc_p50']*100:.1f}% → {r['mc_p50']*100:.1f}%"
    return best, why

STEPS = [
    ('base_range', [round(float(x), 2) for x in np.arange(0.16, 0.305, 0.01)] + [0.32, 0.35, 0.40]),
    ('ordimb_min', [round(float(x), 2) for x in np.arange(1.20, 1.605, 0.02)]),
    ('score_floor', [35, 37.5, 40, 42.5, 45, 47.5, 50, 52.5, 55, 57.5, 60]),
    ('trig_hose', [0.050, 0.052, 0.054, 0.056, 0.058, 0.060, 0.062, 0.064, 0.066]),        # Cond1 HOSE
    ('trig_hnx', [0.080, 0.084, 0.088, 0.092, 0.096]),                                     # Cond1 HNX
    ('vol_floor', [round(float(x), 1) for x in np.arange(1.5, 3.05, 0.1)]),                       # Cond2
    ('gtgd_min', [5e9, 7.5e9, 10e9, 12.5e9, 15e9, 17.5e9, 20e9, 25e9, 30e9]),               # Cond3
    ('base_len', [20, 25, 30, 35, 40, 45]),                                                # Cond4
    ('dk5_hi', [0.0, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]),                                 # Cond5 (0.0 = tắt)
    ('vol_ceil', [None, 3.0, 4.0, 4.5, 5.0, 6.0, 8.0]),                                    # Cond6 (None = tắt)
    ('volat_min', [0.0, 0.010, 0.0125, 0.015, 0.0175, 0.020, 0.025]),                      # Cond7
    ('use_cond8', [False, True]),                                                          # Cond8
]
DEF = dict(base_range=0.22, ordimb_min=1.40, score_floor=45, trig_hose=0.058, trig_hnx=0.088, vol_floor=2.0,
           gtgd_min=15e9, base_len=30, dk5_hi=0.25, vol_ceil=None, volat_min=0.015, use_cond8=False)

def extra_for(knob):
    if knob == 'vol_ceil':
        return lambda v: dict(use_cond6=(v is not None))
    return None

def main():
    cache = load_cache(); base = json.loads(os.environ.get('START', '{}'))
    log = []
    with Pool(2, initializer=_init) as pool:
        _st = dict(base); _k0 = next(iter(_st), 'base_range'); _v0 = _st.pop(_k0, DEF.get(_k0))
        base0 = run_grid(pool, cache, _st, _k0, [_v0])[0]   # baseline = START (PROD if empty)
        for pas in range(1, int(os.environ.get('PASSES', 3)) + 1):
            before = dict(base)
            for knob, grid in STEPS:
                print(f'== pass {pas} {knob}', flush=True)
                ex = extra_for(knob)
                rows = run_grid(pool, cache, base, knob, grid, ex)
                cur = dict(base); cur[knob] = base.get(knob, DEF[knob])
                if ex: cur.update(ex(cur[knob]))
                incr = cache.get(_key(cur)) or run_grid(pool, cache, base, knob, [cur[knob]], ex)[0]
                best, why = accept(rows, incr, knob)
                if best is not incr:
                    base = dict(best['over'])
                log.append(dict(pas=pas, knob=knob, grid=[dict(v=r['over'].get(knob), ret=r['ret'], dd=r['dd'], pf=r['pf'],
                                sharpe=r['sharpe'], deals=r['deals'], mc_p50=r['mc_p50'], mc_p10=r['mc_p10'],
                                dd_p95=r['dd_p95'], h1=r['h1'], h2=r['h2']) for r in rows],
                                chosen=base.get(knob, DEF[knob]), why=why))
                print(f'   -> pass {pas} {knob}: {why}; base now {base}', flush=True)
                json.dump(dict(log=log, base=base), open(OUT, 'w'), ensure_ascii=False, indent=1, default=str)
            if base == before:
                print(f'pass {pas}: không đổi gì nữa -> dừng', flush=True)
                break
    final = cache[_key(base)] if base else base0
    json.dump(dict(log=log, base=base, baseline=base0, final=final), open(OUT, 'w'),
              ensure_ascii=False, indent=1, default=str)
    print('DONE', base, final['ret'], final['mc_p50'], flush=True)

if __name__ == '__main__':
    main()
