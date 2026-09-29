# -*- coding: utf-8 -*-
"""R33 — Monte Carlo KHOA LAI theo TUNG NAM 2019..2026 (anh Son 30/09/2026).

CHI doi khoa lai (profit_lock). Moi dieu kien khac GIU NGUYEN nhu PROD dang chay
(den Cam bat, T+3, momentum, van T+4, MA10/MA30, cat lo, cong mua...).
Moi cau hinh khoa lai:
  * backtest day du -> loi nhuan tung nam;
  * Monte Carlo NSEED lan, moi lan bo ngau nhien 10% lenh vao (miss_prob=0.10) -> TRUNG VI
    va p10 loi nhuan TUNG NAM.
Chon: cau hinh thang PROD (S1 + 15%->+8%) o nhieu nam nhat theo MC trung vi, xem ca nam te nhat.
Ket qua: evidence/r33_lock_years.json + bang in ra log. KHONG doi PROD."""
import os, sys, json, time
import numpy as np
from multiprocessing import Pool
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)

OUT = os.environ.get('OUT', 'evidence/r33_lock_years.json')
NSEED = int(os.environ.get('NSEED', 60))
LOCKS = {'khong_khoa': None}
for a in (0.01, 0.02, 0.03, 0.04):
    for b in (0.04, 0.05, 0.06, 0.07):
        LOCKS[f'8→+{int(a*100)} 12→+{int(b*100)}'] = [[0.08, a], [0.12, b]]
for c in (0.07, 0.08, 0.10):
    LOCKS[f'S1 + 15→+{int(c*100)}'] = [[0.08, 0.02], [0.12, 0.05], [0.15, c]]
LOCKS['8→+2 12→+6 15→+8'] = [[0.08, 0.02], [0.12, 0.06], [0.15, 0.08]]
LOCKS['8→+4 10→+5 12→+6'] = [[0.08, 0.04], [0.10, 0.05], [0.12, 0.06]]
PROD_NAME = 'S1 + 15→+8'

_E = None


def _init():
    global _E
    import engine2 as E; E.load(); _E = E


def years(eq):
    d = {}
    for e in eq:
        d.setdefault(e[0][:4], []).append(float(e[1]))
    out, prev = {}, None
    for y in sorted(d):
        s = prev if prev is not None else d[y][0]
        out[y] = d[y][-1] / s - 1; prev = d[y][-1]
    return out


def job(item):
    name, lock = item
    t = time.time()
    E = _E
    from produce2 import PROD
    C = dict(E.CFG); C.update(PROD); C['profit_lock'] = lock
    r = E.run(C, log=False); m = E.metrics(r)
    base = years(r['eq'])
    mc = {y: [] for y in base}; mc_tot = []
    for s in range(NSEED):
        C2 = dict(C); C2.update(miss_prob=0.10, miss_seed=1000 + s)
        rr = E.run(C2, log=False); yy = years(rr['eq'])
        for y in mc:
            mc[y].append(yy.get(y, np.nan))
        mc_tot.append(E.metrics(rr)['total_return'])
    return dict(name=name, lock=lock, ret=m['total_return'], dd=m['maxdd'], sharpe=m['sharpe'], pf=m['pf'],
                base=base, mc_p50={y: float(np.nanmedian(v)) for y, v in mc.items()},
                mc_p10={y: float(np.nanquantile(v, .10)) for y, v in mc.items()},
                mc_tot_p50=float(np.median(mc_tot)), mc_tot_p10=float(np.quantile(mc_tot, .10)),
                sec=round(time.time() - t))


def main():
    rows = []
    with Pool(int(os.environ.get('PROCS', 3)), initializer=_init) as pool:
        for res in pool.imap_unordered(job, list(LOCKS.items())):
            rows.append(res)
            print(f"xong {res['name']:22s} ({res['sec']}s)", flush=True)
    by = {r['name']: r for r in rows}
    P = by[PROD_NAME]; ys = sorted(P['base'])
    for r in rows:
        r['thang_nam'] = sum(1 for y in ys if r['mc_p50'][y] > P['mc_p50'][y] + 1e-4)
        r['thua_nam'] = sum(1 for y in ys if r['mc_p50'][y] < P['mc_p50'][y] - 1e-4)
        r['nam_te_nhat'] = min(r['mc_p50'][y] for y in ys)
    # xep hang tung nam
    rank = {r['name']: [] for r in rows}
    for y in ys:
        srt = sorted(rows, key=lambda r: -r['mc_p50'][y])
        for k, r in enumerate(srt):
            rank[r['name']].append(k + 1)
    for r in rows:
        r['hang_tb'] = float(np.mean(rank[r['name']]))
    rows.sort(key=lambda r: r['hang_tb'])
    f = lambda x: f"{x*100:+6.1f}"
    print('\n==== MC TRUNG VI LOI NHUAN TUNG NAM (%) — chi doi khoa lai, moi thu khac nhu PROD ====')
    print(f"{'Khoá lãi':22s} " + ' '.join(f'{y:>7s}' for y in ys) + '   MC tổng  MCp10 tổng   DD   hạng TB  thắng/thua PROD (năm)')
    for r in rows:
        print(f"{r['name']:22s} " + ' '.join(f"{f(r['mc_p50'][y]):>7s}" for y in ys)
              + f"  {r['mc_tot_p50']*100:7.1f}%  {r['mc_tot_p10']*100:7.1f}%  {r['dd']*100:5.2f}%  {r['hang_tb']:5.1f}   "
              + f"{r['thang_nam']}/{r['thua_nam']}" + ('   <- PROD' if r['name'] == PROD_NAME else ''), flush=True)
    print('\n==== NAM NAO AI NHAT (MC trung vi) ====')
    for y in ys:
        b = max(rows, key=lambda r: r['mc_p50'][y])
        print(f"{y}: {b['name']:22s} {f(b['mc_p50'][y])}%   (PROD {f(P['mc_p50'][y])}%)")
    json.dump(dict(meta=dict(research='R33 MC khoa lai tung nam', nseed=NSEED, prod=PROD_NAME), rows=rows),
              open(OUT, 'w'), ensure_ascii=False, indent=1, default=str)


if __name__ == '__main__':
    main()
