# -*- coding: utf-8 -*-
"""R38b — kiểm độ bền cho ứng viên score_volr (điểm CANSLIM + Vol/TB20, hạng phần trăm trong phiên).
  (1) bình nguyên: quét trọng số w*điểm + (1-w)*Vol/TB20, w = 0 .. 1, mỗi w có MC 100 lần lỡ 10% lệnh;
  (2) deal-level: deal nào PROD có mà score_volr không và ngược lại; bỏ top 1/3/5 deal tốt nhất của
      score_volr (đóng góp NAV) xem còn hơn PROD không;
  (3) bootstrap CÓ HOÀN LẠI ở mức deal (5.000 lần) cho lợi nhuận trung bình mỗi deal của hai bên;
  (4) walk-forward lồng: chọn w trên 2019-22, kiểm 2023-26.
Gốc so sánh = thứ tự CŨ (rank_mode='score'). Kết quả: evidence/r38b_verify.json."""
import os, sys, json
import numpy as np
from multiprocessing import get_context
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
NSEED = int(os.environ.get('NSEED', 100))
W = [0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]
_E = None; _P = None


def _init():
    global _E, _P
    import engine2 as E
    E.load(); _E = E
    from produce2 import PROD
    _P = PROD


def _seg(eq, a, b):
    v = np.array([x[1] for x in eq if a <= x[0][:4] <= b], float)
    return float(v[-1] / v[0] - 1)


def cfg(**k):
    C = dict(_E.CFG); C.update(_P); C.update(k); return C


def job(w):
    # goc so sanh = thu tu CU (rank_mode='score'), ghi ro — PROD tu 22/10 da la score_volr
    C = cfg(rank_mode='score_volr', rank_w=w) if w is not None else cfg(rank_mode='score')
    r = _E.run(C, log=False); m = _E.metrics(r)
    mc = np.array([_E.metrics(_E.run(dict(C, miss_prob=0.10, miss_seed=1000 + s), log=False))['total_return']
                   for s in range(NSEED)])
    return dict(w=w, ret=m['total_return'], dd=m['maxdd'], pf=m['pf'], sharpe=m['sharpe'],
                h1=_seg(r['eq'], '2019', '2022'), h2=_seg(r['eq'], '2023', '2026'),
                mc_p10=float(np.quantile(mc, .1)), mc_p50=float(np.median(mc)), mc_p90=float(np.quantile(mc, .9)))


def deals(C):
    from dealstats import deals as D
    r = _E.run(C, log=True)
    return D(r['trades']), r


def main():
    _init()
    with get_context('fork').Pool(int(os.environ.get('PROCS', 2))) as pool:
        sweep = pool.map(job, [None] + W)
    base = sweep[0]; sw = sweep[1:]
    for s in sw:
        print(f"w={s['w']:.1f} ret {s['ret']*100:+.0f}% DD {s['dd']*100:.2f}% PF {s['pf']} MC p10 {s['mc_p10']*100:+.0f}% "
              f"p50 {s['mc_p50']*100:+.0f}% | 19-22 {s['h1']*100:+.0f}% 23-26 {s['h2']*100:+.0f}%")
    wf = max(sw, key=lambda s: s['h1'])
    dP, rP = deals(cfg(rank_mode='score')); dV, rV = deals(cfg(rank_mode='score_volr', rank_w=None))
    kP = {(x['sym'], x['entry']): x for x in dP}; kV = {(x['sym'], x['entry']): x for x in dV}
    only_P = sorted([kP[k] for k in kP.keys() - kV.keys()], key=lambda x: -x['pnl_vnd'])
    only_V = sorted([kV[k] for k in kV.keys() - kP.keys()], key=lambda x: -x['pnl_vnd'])
    sl = lambda xs: [dict(sym=x['sym'], entry=x['entry'], pnl_pct=x.get('pnl_pct'), pnl_vnd=x['pnl_vnd']) for x in xs]
    # bo top deal cua score_volr: tru dong gop NAV (xap xi theo VND) khoi NAV cuoi
    navP = rP['eq'][-1][1]; navV = rV['eq'][-1][1]; nav0 = rP['eq'][0][1]
    topV = sorted(dV, key=lambda x: -x['pnl_vnd'])
    drop = {k: float((navV - sum(x['pnl_vnd'] for x in topV[:k])) / nav0 - 1) for k in (1, 3, 5)}
    topP = sorted(dP, key=lambda x: -x['pnl_vnd'])
    dropP = {k: float((navP - sum(x['pnl_vnd'] for x in topP[:k])) / nav0 - 1) for k in (1, 3, 5)}
    # bootstrap co hoan lai muc deal
    rng = np.random.default_rng(11)
    def boot(xs):
        a = np.array([x.get('pnl_pct') or 0.0 for x in xs], float)
        b = np.array([a[rng.integers(0, len(a), len(a))].mean() for _ in range(5000)])
        return dict(n=len(a), mean=float(a.mean()), p05=float(np.quantile(b, .05)), p50=float(np.median(b)), p95=float(np.quantile(b, .95)))
    # co che: lenh do bi ban vi khong xac nhan DK9 (chiem cho 'treo' toi T+3, chan lenh moi)
    def fail9(r):
        s_ = r['signals']; ok = [x for x in s_ if x.get('ordimb') is not None and x['ordimb'] >= _P['ordimb_min']]
        return dict(n_lenh=len(s_), n_dat_dk9=len(ok), ty_le=round(len(ok) / max(1, len(s_)), 3))
    mech = dict(prod=fail9(rP), volr=fail9(rV))
    print('lenh vao / dat DK9  cu:', mech['prod'], ' moi:', mech['volr'])
    out = dict(prod=base, sweep=sw, co_che_dk9=mech, walk_forward_w=dict(w=wf['w'], h1=wf['h1'], h2=wf['h2'], prod_h2=base['h2']),
               deals_only_prod=sl(only_P), deals_only_volr=sl(only_V),
               sum_only_prod=float(sum(x['pnl_vnd'] for x in only_P)), sum_only_volr=float(sum(x['pnl_vnd'] for x in only_V)),
               drop_top_volr=drop, drop_top_prod=dropP, boot_prod=boot(dP), boot_volr=boot(dV))
    json.dump(out, open('evidence/r38b_verify.json', 'w'), ensure_ascii=False, indent=1, default=str)
    print('WF w:', out['walk_forward_w'])
    print('chi PROD co:', len(only_P), f"{out['sum_only_prod']/1e6:+,.0f} tr", [(x['sym'], x['entry'], round(x['pnl_vnd']/1e6)) for x in only_P[:8]])
    print('chi score_volr co:', len(only_V), f"{out['sum_only_volr']/1e6:+,.0f} tr", [(x['sym'], x['entry'], round(x['pnl_vnd']/1e6)) for x in only_V[:8]])
    print('bo top deal  volr:', {k: round(v*100) for k, v in drop.items()}, ' prod:', {k: round(v*100) for k, v in dropP.items()})
    print('boot deal  prod:', out['boot_prod'], '\n           volr:', out['boot_volr'])


if __name__ == '__main__':
    main()
