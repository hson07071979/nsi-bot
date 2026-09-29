# -*- coding: utf-8 -*-
"""R32 — Monte Carlo cho KHOA LAI x DEN CAM (anh Son 29/09/2026: "chay Monte Carlo de chon cau hinh tot nhat").

Luoi: san cua nac 8% {+1, +2, +3, +4%} x san cua nac 12% {+4, +5, +6, +7%} x den Cam {bat, tat}
      + doi chung: khong khoa lai, khoa 8->4/10->5/12->6 (thu 29/09), S1 + nac 15->8.
Moi cau hinh (cung ham danh gia cua R11 — research/r11_mc_opt.evaluate):
  * backtest day du: tong LN, DD, PF, Sharpe, 2019-22 / 2023-26;
  * Monte Carlo lo lenh: NSEED lan, moi lan bo ngau nhien 10% lenh vao -> trung vi / p10 / p90;
  * block bootstrap 20 phien x 2000 duong: DD p95;
  * them: tru truot gia 0,2% moi chieu.
Chon (giong luat nhan R11, so voi S1 + den Cam dang la ung vien):
  MC trung vi >= +2% tuong doi, MC p10 khong kem, DD p95 khong kem > 1 diem, DD <= 12%,
  2023-26 khong kem, 2019-22 khong sut > 10%, co truot gia van khong kem, va VUNG PHANG:
  trung binh MC trung vi cua cac o ke ben (+-1 nac tren luoi) cung >= ung vien.
Ket qua: evidence/r32_mc_exit.json (+ bang in ra log). KHONG doi PROD — anh Son duyet sau."""
import os, sys, json, time
import numpy as np
from multiprocessing import Pool
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'research'))
import r11_mc_opt as R11

OUT = os.environ.get('OUT', 'evidence/r32_mc_exit.json')
A8 = [0.01, 0.02, 0.03, 0.04]
B12 = [0.04, 0.05, 0.06, 0.07]


def _job(item):
    name, over = item
    t = time.time()
    res = R11.evaluate(over)
    E = R11._E
    from produce2 import PROD
    C = dict(E.CFG); C.update(PROD); C.update(over); C['slip'] = 0.002
    res['ret_slip'] = E.metrics(E.run(C, log=False))['total_return']
    res['name'] = name; res['sec'] = round(time.time() - t)
    return res


def configs():
    out = []
    for cam in (True, False):
        for a in A8:
            for b in B12:
                out.append((f"L{int(a*100)}_{int(b*100)}_{'cam' if cam else 'khongcam'}",
                            dict(profit_lock=[[0.08, a], [0.12, b]], use_orange_cut=cam)))
        out.append((f"khong_khoa_{'cam' if cam else 'khongcam'}", dict(profit_lock=None, use_orange_cut=cam)))
    out.append(('khoa_moi_cam', dict(profit_lock=[[0.08, 0.04], [0.10, 0.05], [0.12, 0.06]], use_orange_cut=True)))
    out.append(('s1_15_cam', dict(profit_lock=[[0.08, 0.02], [0.12, 0.05], [0.15, 0.08]], use_orange_cut=True)))
    return out


def pick(rows):
    by = {r['name']: r for r in rows}
    inc = by['L2_5_cam']
    def nb(r):
        n = r['name']
        if not n.startswith('L'): return []
        a, b, cam = n[1:].split('_'); a, b = int(a), int(b)
        ks = [f'L{a+da}_{b+db}_{cam}' for da, db in ((-1, 0), (1, 0), (0, -1), (0, 1))]
        return [by[k]['mc_p50'] for k in ks if k in by]
    ok = []
    for r in rows:
        if r is inc: continue
        why = []
        if r['mc_p50'] < inc['mc_p50'] * 1.02: why.append('MC trung vị chưa hơn 2%')
        if r['mc_p10'] < inc['mc_p10']: why.append('MC p10 kém')
        if r['dd_p95'] > inc['dd_p95'] + 0.01: why.append('DD p95 kém')
        if r['dd'] > inc['dd'] + 0.01 or r['dd'] > 0.12: why.append('DD')
        if (r['h2'] or 0) < (inc['h2'] or 0): why.append('2023-26 kém')
        if (r['h1'] or 0) < (inc['h1'] or 0) * 0.9: why.append('2019-22 sụt')
        if r['ret_slip'] < inc['ret_slip']: why.append('có trượt giá kém')
        n_ = nb(r)
        if n_ and np.mean(n_) < inc['mc_p50']: why.append('không phải vùng phẳng')
        r['loai'] = why
        if not why: ok.append(r)
    best = max(ok, key=lambda r: r['mc_p50']) if ok else inc
    return best, inc


def main():
    cfgs = configs()
    rows = []
    with Pool(int(os.environ.get('PROCS', 3)), initializer=R11._init) as pool:
        for res in pool.imap_unordered(_job, cfgs):
            rows.append(res)
            print(f"{res['name']:18s} ret {res['ret']*100:7.1f}% slip {res['ret_slip']*100:6.1f}% dd {res['dd']*100:5.2f}% "
                  f"pf {res['pf']} sh {res['sharpe']} | MC p50 {res['mc_p50']*100:6.1f}% p10 {res['mc_p10']*100:6.1f}% "
                  f"ddp95 {res['dd_p95']*100:5.1f}% | 19-22 {(res['h1'] or 0)*100:6.1f}% 23-26 {(res['h2'] or 0)*100:6.1f}% "
                  f"({res['sec']}s)", flush=True)
            json.dump(dict(rows=rows), open(OUT, 'w'), ensure_ascii=False, indent=1, default=str)
    best, inc = pick(rows)
    from research.common import meta
    json.dump(dict(meta=meta(dict(research='R32 Monte Carlo khoa lai x den Cam', nseed=R11.NSEED)),
                   rows=sorted(rows, key=lambda r: -r['mc_p50']), incumbent=inc['name'], best=best['name']),
              open(OUT, 'w'), ensure_ascii=False, indent=1, default=str)
    print('\n==== XEP HANG THEO MC TRUNG VI ====')
    for r in sorted(rows, key=lambda r: -r['mc_p50']):
        print(f"{r['name']:18s} MC p50 {r['mc_p50']*100:6.1f}% p10 {r['mc_p10']*100:6.1f}% | ret {r['ret']*100:6.1f}% "
              f"slip {r['ret_slip']*100:6.1f}% dd {r['dd']*100:5.2f}% ddp95 {r['dd_p95']*100:5.1f}% sh {r['sharpe']} "
              f"| {'ĐẠT' if not r.get('loai') else 'loại: ' + ', '.join(r.get('loai') or [])}")
    print(f"\nUNG VIEN (S1 + den Cam): {inc['name']} · CHON: {best['name']}")


if __name__ == '__main__':
    main()
