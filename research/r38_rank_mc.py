# -*- coding: utf-8 -*-
"""R38 — THỨ TỰ ƯU TIÊN khi nhiều mã watchlist cùng nổ một phiên (anh Sơn 22/10/2026).

Bối cảnh: phiên 21/10 ORS, DIG, VSC cùng đủ điều kiện; PROD (max_unconf=1, rank_mode='score') chỉ vào
ORS — mã điểm CANSLIM cao nhất. Câu hỏi: xếp theo yếu tố nào thì cấu hình tốt nhất?

KHÓA mọi thứ như PROD (produce2.PROD). Chỉ đổi rank_mode. Mỗi tiêu chí chạy:
  * cả kỳ + hai nửa (2019-22 / 2023-26), trượt giá 0,2 %, khớp giá mở cửa T+1;
  * MC thực thi: NSEED lần lỡ ngẫu nhiên 10 % lệnh (miss_prob=0.10);
  * bootstrap khối 20 phiên (2000 đường) trên đường NAV — rút CÓ HOÀN LẠI;
  * đối chứng: xếp NGƯỢC điểm (rev_score) và xếp NGẪU NHIÊN (NRAND hạt giống) — nếu tiêu chí không
    thắng nổi ngẫu nhiên thì thứ tự ưu tiên không quan trọng.
Walk-forward: chọn tiêu chí tốt nhất CHỈ bằng 2019-22, xem nó làm gì ở 2023-26.
Tiêu chí chấp nhận đổi PROD = đúng bộ R37/R11 (MC trung vị ≥ +2 %, p10 không kém, DD p95 bootstrap không xấu
hơn >1 đ%, DD thực ≤ 12 %, 2023-26 không kém, 2019-22 không kém >10 %, cả kỳ không thấp hơn).
Thêm: phân tích phiên tranh chấp — trong các phiên có ≥ 2 ứng viên, yếu tố nào dự báo mã thắng
(tương quan hạng trong phiên với lãi 10/20 phiên sau).

OrdImb (ĐK9) KHÔNG quan sát được lúc chọn mã (mua dò ATC, tối mới có số) -> các tiêu chí có 'oi' chỉ để
tham khảo, ghi rõ NHÌN TRƯỚC, không bao giờ được đề xuất.
Kết quả: evidence/r38_rank_mc.json. KHÔNG đụng PROD, KHÔNG đăng web.
"""
import os, sys, json, time
import numpy as np
from multiprocessing import get_context

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
OUT = os.environ.get('OUT', 'evidence/r38_rank_mc.json')
NSEED = int(os.environ.get('NSEED', 30))
NRAND = int(os.environ.get('NRAND', 30))
PROCS = int(os.environ.get('PROCS', 2))

OBS = ['score', 'base', 'pct', 'volr', 'rs', 'mom', 'fund', 'tech', 'liq',
       'score_base', 'score_volr', 'score_rs', 'score_mom', 'score_pct', 'score_base_volr',
       'multi_obs', 'score_sector', 'score_wave']
LOOKAHEAD = ['oi', 'score_oi', 'score_base_oi', 'multi']
CONTROL = ['rev_score']

_E = None
_PROD = None


def _init():
    global _E, _PROD
    import engine2 as E
    E.load(); _E = E
    from produce2 import PROD
    _PROD = PROD
    # score_wave can mang song nganh R30 (E.EXTRA). PROD khong dung no (wave_base/wave_cap tat) nen
    # nap vao khong doi ket qua cua cac tieu chi khac.
    sys.path.insert(0, os.path.join(ROOT, 'research'))
    import r30_wave
    r30_wave.install()


def _cfg(over):
    C = dict(_E.CFG); C.update(_PROD); C.update(over)
    return C


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
                ret_p05=float(np.quantile(rets, .05)), ret_p50=float(np.median(rets)))


def _m(r):
    m = _E.metrics(r)
    return dict(ret=m['total_return'], cagr=m['cagr'], dd=m['maxdd'], pf=m['pf'], sharpe=m['sharpe'],
                trades=m['trades'], winrate=m.get('winrate'),
                h1=_seg(r['eq'], '2019', '2022'), h2=_seg(r['eq'], '2023', '2026'),
                y2026=_seg(r['eq'], '2026', '2026'))


def job(args):
    kind, mode, extra, nseed = args
    C = _cfg(dict(rank_mode=mode, **extra))
    r = _E.run(C, log=False)
    out = dict(kind=kind, mode=mode, extra=extra, **_m(r))
    if nseed:
        out.update(_boot(r['eq']))
        mc = []
        for s in range(nseed):
            C2 = dict(C); C2.update(miss_prob=0.10, miss_seed=1000 + s)
            mc.append(_E.metrics(_E.run(C2, log=False))['total_return'])
        mc = np.array(mc)
        out.update(mc_p10=float(np.quantile(mc, .10)), mc_p50=float(np.median(mc)),
                   mc_p90=float(np.quantile(mc, .90)), nseed=nseed)
        sl = _E.run(dict(C, slip=0.002), log=False); out['slip02'] = _E.metrics(sl)['total_return']
        no = _E.run(dict(C, entry_mode='next_open'), log=False); nm = _E.metrics(no)
        out['next_open'] = nm['total_return']; out['next_open_dd'] = nm['maxdd']
    return out


def competition():
    """Phiên có >= 2 ứng viên dưới PROD: ai được vào, ai bị loại, vì sao; yếu tố nào dự báo mã thắng."""
    C = _cfg(dict(log_cands=True))
    r = _E.run(C, log=True)
    d = r.get('d') or _E.load()[0]
    AC = d['AdjClose']; S = [str(x) for x in d['sym']]; jm = {s: k for k, s in enumerate(S)}
    cal = [str(x) for x in d['cal']]; im = {c: k for k, c in enumerate(cal)}
    days = []
    for day in r.get('cands') or []:
        if len(day['cands']) < 2:
            continue
        i = day.get('i', im.get(str(day['date'])))
        rows = []
        for x in day['cands']:
            j = jm[x['sym']]
            def fw(n):
                k = min(i + n, len(AC) - 1)
                return float(AC[k, j] / AC[i, j] - 1) if AC[i, j] > 0 and not np.isnan(AC[k, j]) else None
            rows.append(dict(x, f10=fw(10), f20=fw(20)))
        days.append(dict(date=str(day['date']), light=day.get('light'), cands=rows))
    from collections import Counter
    why = Counter(c['why'] for dd in days for c in dd['cands'] if not c['taken'])
    bound = [dd for dd in days if any(not c['taken'] for c in dd['cands'])]

    def spearman(a, b):
        a = np.argsort(np.argsort(a)); b = np.argsort(np.argsort(b))
        if a.std() == 0 or b.std() == 0:
            return None
        return float(np.corrcoef(a, b)[0, 1])
    feats = dict(score=('sc', 1), base=('base', -1), pct=('pct', 1), volr=('volr', 1), rs=('rs', 1),
                 mom=('mom', 1), fund=('fund', 1), tech=(None, 1), oi_NHIN_TRUOC=('oi', 1))
    ic = {}
    for name, (k, sgn) in feats.items():
        for h in ('f10', 'f20'):
            vals = []
            for dd in days:
                xs = [c for c in dd['cands'] if c.get(h) is not None]
                if len(xs) < 2:
                    continue
                v = [(c['sc'] - c['fund']) if k is None else c[k] for c in xs]
                s_ = spearman(np.array(v, float) * sgn, np.array([c[h] for c in xs], float))
                if s_ is not None:
                    vals.append(s_)
            ic[f'{name}_{h}'] = dict(n=len(vals), mean=round(float(np.mean(vals)), 3) if vals else None,
                                     hit=round(float(np.mean([v > 0 for v in vals])), 3) if vals else None)
    tk = [c['f20'] for dd in bound for c in dd['cands'] if c['taken'] and c['f20'] is not None]
    nt = [c['f20'] for dd in bound for c in dd['cands'] if not c['taken'] and c['f20'] is not None]
    return dict(days_multi=len(days), days_bound=len(bound), skip_reasons=dict(why),
                taken_f20_mean=float(np.mean(tk)) if tk else None, skipped_f20_mean=float(np.mean(nt)) if nt else None,
                n_taken=len(tk), n_skipped=len(nt), ic=ic, days=days)


def main():
    t0 = time.time()
    _init()
    comp = competition()
    print(f"phien >=2 ung vien: {comp['days_multi']} · phien co ma bi loai: {comp['days_bound']} · ly do {comp['skip_reasons']}")
    jobs = [('obs', m, {}, NSEED) for m in OBS] + [('lookahead', m, {}, NSEED) for m in LOOKAHEAD] \
         + [('control', m, {}, NSEED) for m in CONTROL] \
         + [('random', 'random', dict(rank_seed=s), 0) for s in range(NRAND)]
    ctx = get_context('fork')
    with ctx.Pool(PROCS) as pool:
        res = []
        for k, o in enumerate(pool.imap_unordered(job, jobs)):
            res.append(o)
            print(f"[{k+1}/{len(jobs)}] {o['kind']:9s} {o['mode']:16s} {o['extra']} ret {o['ret']*100:+.1f}% DD {o['dd']*100:.2f}% "
                  f"PF {o['pf']}" + (f" MC p50 {o['mc_p50']*100:+.1f}%" if 'mc_p50' in o else ''), flush=True)
            json.dump(dict(trang_thai='dang chay', ket_qua=res), open(OUT, 'w'), ensure_ascii=False, default=str)
    rnd = [o['ret'] for o in res if o['kind'] == 'random']
    base = next(o for o in res if o['mode'] == 'score')
    for o in res:
        if o['kind'] != 'random':
            o['vuot_ngau_nhien'] = float(np.mean([o['ret'] > x for x in rnd])) if rnd else None
    # walk-forward: chon tren 2019-22, kiem 2023-26
    obs = [o for o in res if o['kind'] == 'obs']
    wf_pick = max(obs, key=lambda o: o['h1'] or -9)
    # chap nhan theo bo R37
    acc = []
    for o in obs:
        if o['mode'] == 'score':
            continue
        fail = []
        if o['mc_p50'] < base['mc_p50'] * 1.02: fail.append('MC trung vị chưa hơn 2%')
        if o['mc_p10'] < base['mc_p10']: fail.append('MC p10 kém hơn')
        if o['dd_p95'] > base['dd_p95'] + 0.01: fail.append('DD p95 bootstrap xấu hơn >1đ%')
        if o['dd'] > base['dd'] + 0.01 or o['dd'] > 0.12: fail.append('DD thực vượt ngưỡng')
        if (o['h2'] or 0) < (base['h2'] or 0): fail.append('2023-26 kém hơn')
        if (o['h1'] or 0) < (base['h1'] or 0) * 0.9: fail.append('2019-22 kém hơn >10%')
        if o['ret'] < base['ret']: fail.append('cả kỳ thấp hơn')
        if o['next_open'] < base['next_open']: fail.append('khớp mở cửa T+1 kém hơn')
        o['loai_vi'] = fail
        if not fail:
            acc.append(o)
    best = max(acc, key=lambda o: o['mc_p50']) if acc else None
    out = dict(trang_thai='xong', chay_phut=round((time.time() - t0) / 60, 1), nseed=NSEED, nrand=NRAND,
               prod=dict(rank_mode=_PROD.get('rank_mode', _E.CFG.get('rank_mode')), max_unconf=_PROD.get('max_unconf')),
               random=dict(n=len(rnd), p10=float(np.quantile(rnd, .1)) if rnd else None,
                           p50=float(np.median(rnd)) if rnd else None, p90=float(np.quantile(rnd, .9)) if rnd else None,
                           all=rnd),
               walk_forward=dict(chon_tren_2019_22=wf_pick['mode'], h1=wf_pick['h1'], h2=wf_pick['h2'],
                                 prod_h2=base['h2']),
               de_xuat=(best['mode'] if best else 'giữ score'), ket_qua=res,
               competition={k: v for k, v in comp.items() if k != 'days'}, competition_days=comp['days'])
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1, default=str)
    print('XONG', out['de_xuat'], out['walk_forward'], f"{out['chay_phut']} phut")


if __name__ == '__main__':
    main()
