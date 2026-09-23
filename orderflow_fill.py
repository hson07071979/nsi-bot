# -*- coding: utf-8 -*-
"""ORDER-FLOW FILL — Condition 9 must not depend on ONE late provider (audit 24/09/2026).

Measured 23-24/09/2026 (evidence/audit_orderflow_sources.json):
  * FireAnt publishes BuyCount/SellCount LATE: at 18:30 HOSE ~96%, HNX 0% of liquid
    names (and HNX BuyQuantity/SellQuantity were partial placeholders, 60-80% of final).
  * EXACT same definition (so lenh + KL dat mua/ban) is published by:
      HOSE -> Vietstock "Thong ke dat lenh" and CafeF ThongKeDL   (equal to FireAnt on 8/8, 2 days)
      HNX  -> hnx.vn "Thong ke cung cau" (the official upstream; equal on 8/8 + SHS 50/50 sessions)
    Vietstock/CafeF HNX numbers are a DIFFERENT series -> never used for HNX.

Runs after fa_prep.py. For the LAST session only:
  1. liquid names (GTGD >= 5 bn) whose FireAnt order flow is missing (BuyCount or
     SellCount <= 0) are filled from the exact official/secondary source for their
     exchange — all four fields together, never mixed;
  2. a cross-check sample where FireAnt HAS data is compared with the same source;
     |diff| > 1% on any field -> discrepancy listed (never silently resolved);
  3. provenance: data/orderflow_fill.json {sym: {source, fetched_at, fields}} and a
     data_health block. fa.npz is patched atomically.
Nothing is ever filled with zero; a failed lookup leaves the gap (verify_build then
refuses to publish if too many liquid names still miss order flow).
"""
import os, json, datetime as dt, time
import numpy as np
from concurrent.futures import ThreadPoolExecutor

F = ('BuyCount', 'BuyQuantity', 'SellCount', 'SellQuantity')


def _cur_exchange():
    """TODAY's listing (fa.npz `exch` is the INFERRED historical board, which labels
    e.g. ACV — UPCoM — as HOSE; the order-flow source must follow the real board)."""
    try:
        import csv
        return {r['symbol']: r['exchange'] for r in csv.DictReader(open('data/by_exchange.csv', encoding='utf-8'))}
    except Exception:
        return {}


def _srcs(exch):
    """Exact-definition sources for this exchange, in order of preference."""
    if exch in ('HNX', 'UPCOM'):
        from sources import hnx
        mk = 'NY' if exch == 'HNX' else 'UC'
        return [('hnx.vn TK_CungCau/' + mk, lambda s, d: hnx.probe(s, d, market=mk))]
    from sources import vietstock, cafef
    return [('vietstock gettradingresult', lambda s, d: (vietstock.probe(s, d) or [{}])[0]),
            ('cafef ThongKeDL', lambda s, d: (cafef.probe(s, d) or [{}])[0])]


def fetch(sym, exch, day):
    for name, fn in _srcs(exch):
        for a in range(3):
            try:
                r = fn(sym, day)
                f = r.get('fields') or r
                if r.get('available') and r.get('date') == day and all((f.get(k) or 0) > 0 for k in F):
                    return dict(source=name, fetched_at=r.get('fetched_at'), **{k: float(f[k]) for k in F})
                break                       # answered but no row for that day -> next source
            except Exception:
                time.sleep(1.5 * (a + 1))
    return None


def main(min_tv=5e9, sample=8):
    z = dict(np.load('data/fa.npz', allow_pickle=True))
    cal = [str(x) for x in z['cal']]; S = [str(x) for x in z['sym']]
    cur = _cur_exchange()
    ex = [{'HSX': 'HOSE'}.get(cur.get(s), cur.get(s)) or str(e) for s, e in zip(S, z['exch'])]
    i = len(cal) - 1; day = cal[i]
    TV = z['TotalValue'][i]
    liq = [j for j in range(len(S)) if TV[j] == TV[j] and TV[j] >= min_tv]
    miss = [j for j in liq if not ((z['BuyCount'][i, j] or 0) > 0 and (z['SellCount'][i, j] or 0) > 0)]
    have = [j for j in liq if j not in miss]
    rnd = np.random.default_rng(int(day.replace('-', '')))
    check = []
    for e in ('HOSE', 'HNX', 'UPCOM'):
        pool = [j for j in have if ex[j] == e]
        check += list(rnd.choice(pool, size=min(sample, len(pool)), replace=False)) if pool else []
    jobs = [(j, 'fill') for j in miss] + [(int(j), 'check') for j in check]
    try:
        from sources import vietstock as _v; _v._session()          # warm the CSRF session once
    except Exception as e:
        print('vietstock warm-up:', e)
    with ThreadPoolExecutor(4) as pool:
        res = list(pool.map(lambda jk: (jk, fetch(S[jk[0]], ex[jk[0]], day)), jobs))
    filled, disc, failed = {}, [], []
    for (j, kind), got in res:
        s = S[j]
        if got is None:
            if kind == 'fill': failed.append(s)
            continue
        if kind == 'fill':
            for k in F: z[k][i, j] = got[k]
            filled[s] = dict(exch=ex[j], date=day, **got)
        else:
            d = {k: (got[k] / float(z[k][i, j]) - 1) if z[k][i, j] else None for k in F}
            if any(v is None or abs(v) > 0.01 for v in d.values()):
                disc.append(dict(sym=s, exch=ex[j], date=day, source=got['source'],
                                 fireant={k: float(z[k][i, j]) for k in F}, other={k: got[k] for k in F}))
    if filled:
        tmp = 'data/fa.npz.tmp.npz'
        np.savez_compressed(tmp, **z)
        os.replace(tmp, 'data/fa.npz')
    after = [j for j in liq if (z['BuyCount'][i, j] or 0) > 0 and (z['SellCount'][i, j] or 0) > 0]
    by_ex = {}
    for e in ('HOSE', 'HNX', 'UPCOM'):
        L = [j for j in liq if ex[j] == e]
        by_ex[e] = dict(liquid=len(L), with_orderflow=sum(1 for j in L if j in after),
                        coverage=round(sum(1 for j in L if j in after) / max(1, len(L)), 4))
    out = dict(session=day, missing_before=len(miss), filled=len(filled), failed=sorted(failed),
               crosschecked=len(check), discrepancies=disc, by_exchange=by_ex, rows=filled)
    json.dump(out, open('data/orderflow_fill.json', 'w'), ensure_ascii=False, indent=1)
    try:
        import data_health as DH
        cov = min(v['coverage'] for k, v in by_ex.items() if k != 'UPCOM' and v['liquid'])
        DH.put('orderflow', dict(source='FireAnt + hnx.vn (HNX) + Vietstock (HOSE)',
                                 status='OK' if (cov >= 0.80 and not disc) else ('DISCREPANCY' if disc else 'DEGRADED'),
                                 coverage=cov, freshness=day, filled=len(filled), missing_count=len(failed),
                                 discrepancies=len(disc), by_exchange=by_ex))
    except Exception as e:
        print('data_health:', e)
    print(json.dumps({k: v for k, v in out.items() if k != 'rows'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
