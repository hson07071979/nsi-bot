# -*- coding: utf-8 -*-
"""Shared helpers for audit research runs: evidence metadata + split metrics."""
import os, sys, json, hashlib, subprocess, datetime as dt
from collections import defaultdict
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine2 as E
from produce2 import PROD
from dealstats import deals as _deals, stats as _dstats

EXPERIMENT_VERSION = 'audit-2026-09-23'

def cfg_hash(cfg=None):
    c = dict(E.CFG); c.update(PROD); c.update(cfg or {})
    return hashlib.sha256(json.dumps(c, sort_keys=True, default=str).encode()).hexdigest()[:12]

def meta(extra=None):
    try: sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=os.path.dirname(__file__)).decode().strip()
    except Exception: sha = None
    d, *_ = E.load()
    m = dict(git_sha=sha, data_asof=str(d['cal'][-1]), prod_config_hash=cfg_hash(),
             generated=dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z',
             experiment_version=EXPERIMENT_VERSION, status='CURRENT')
    m.update(extra or {}); return m

def _seg(eq, a, b):
    x = [(d, v) for d, v, *_ in eq if a <= d[:4] <= b]
    if len(x) < 20: return None
    v = np.array([q[1] for q in x]); r = np.diff(v) / v[:-1]
    dd = 1 - v / np.maximum.accumulate(v)
    return dict(ret=round(float(v[-1] / v[0] - 1), 4), maxdd=round(float(dd.max()), 4),
                sharpe=round(float(r.mean() / r.std() * np.sqrt(250)), 2) if r.std() > 0 else None)

def seg_pf(trades, a, b):
    t = [x for x in trades if a <= x['entry'][:4] <= b]
    gp = sum(x['pnl_vnd'] for x in t if x['pnl_vnd'] > 0); gl = -sum(x['pnl_vnd'] for x in t if x['pnl_vnd'] < 0)
    return round(gp / gl, 2) if gl > 0 else None

def yearly(eq):
    d = defaultdict(list)
    for dd, nv, *_ in eq: d[dd[:4]].append(float(nv))
    o = {}; p = None
    for y in sorted(d):
        s = p if p is not None else d[y][0]; o[y] = round(d[y][-1] / s - 1, 4); p = d[y][-1]
    return o

def concentration(trades):
    D = _deals(trades); w = sorted([x['pnl_vnd'] for x in D if x['pnl_vnd'] > 0], reverse=True)
    gp = sum(w) or 1
    return {f'top{k}': round(sum(w[:k]) / gp, 3) for k in (1, 3, 5, 6, 10, 20)}

def summarize(r, name=''):
    m = E.metrics(r); tr = r['trades']
    s1 = _seg(r['eq'], '2019', '2022'); s2 = _seg(r['eq'], '2023', '2026')
    if s1: s1['pf'] = seg_pf(tr, '2019', '2022')
    if s2: s2['pf'] = seg_pf(tr, '2023', '2026')
    return dict(name=name, metrics=m, deal_metrics=_dstats(tr),
                unique_deals=len({(t['sym'], t['entry']) for t in tr}),
                p2019_2022=s1, p2023_2026=s2, yearly=yearly(r['eq']), concentration=concentration(tr))

def run(over=None, name='', keep=False):
    c = dict(PROD); c.update(over or {})
    r = E.run(c, log=keep)
    s = summarize(r, name)
    return (s, r) if keep else s

def line(s):
    m = s['metrics']; a = s['p2019_2022'] or {}; b = s['p2023_2026'] or {}
    return (f"{s['name']:38s} {m['total_return']*100:+8.1f}% DD {m['maxdd']*100:5.2f}% PF {m['pf']!s:>5} "
            f"Sh {m['sharpe']!s:>4} deals {s['unique_deals']:3d} | 19-22 {a.get('ret',0)*100:+7.1f}% "
            f"PF {a.get('pf')} | 23-26 {b.get('ret',0)*100:+7.1f}% PF {b.get('pf')}")

def pmap(jobs, procs=4):
    """jobs: list of (name, overrides). Fork after load() so the cache is shared."""
    E.load()
    import multiprocessing as mp
    ctx = mp.get_context('fork')
    with ctx.Pool(procs) as pool:
        return pool.starmap(_job, [(n, o) for n, o in jobs])

def _job(n, o): return run(o, n)
