# -*- coding: utf-8 -*-
"""R38 — Giải ngân cho danh mục khách hàng (Lọc port): 1 lần, 2 lần hay 3 lần? Đợi đi ngang bao lâu?
Lỡ giải ngân rồi cổ phiếu chạy luôn thì top-up thế nào?  (anh Sơn 15/10/2026)

Cách làm
  Sự kiện = ngày một mã lọt màn "tài sản tốt ở giá thấp" của port (không nhìn trước):
    GTGD trung vị 20 phiên ≥ 10 tỷ · ROE ≥ 12% · LN 4 quý > 0 và không giảm so với cùng kỳ ·
    P/E ÷ trung vị P/E 3 năm của chính mã ≤ 0,8 · giá thấp hơn đỉnh 250 phiên ≥ 25%.
    Mỗi mã cách nhau ≥ 120 phiên. Bộ đối chứng: chỉ điều kiện giá (giảm ≥ 30%), không lọc cơ bản.
  Mỗi sự kiện có ngân sách 1,0, theo dõi H phiên; tiền chưa giải ngân hưởng 5%/năm.
  Quyết định ở giá đóng cửa phiên t, khớp giá mở cửa phiên t+1. Không phí, không trượt giá (giống nhau mọi chiến lược).
  So từng cặp chiến lược trên CÙNG sự kiện; khoảng tin cậy bằng bootstrap theo khối tháng (sự kiện cùng tháng
  tương quan với nhau). Monte Carlo danh mục: rút ngẫu nhiên 8 sự kiện/danh mục × 10.000 lần.

Chạy: python research/r38_giai_ngan.py   → evidence/r38_giai_ngan.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_data as P  # noqa: E402

CASH_D = 1.05 ** (1 / 250) - 1
RNG = np.random.default_rng(38)


# ---------------------------------------------------------------- sự kiện
def su_kien(d, kieu='port', cooldown=120, H=250):
    C, TV = d['C'], d['TV']
    N, M = C.shape
    hi250 = P.roll_max(C, 250)
    with np.errstate(all='ignore'):
        dd = C / hi250 - 1
    tv20 = np.full_like(TV, np.nan)
    for i in range(20, N):
        with np.errstate(all='ignore'):
            tv20[i] = np.nanmedian(TV[i - 19:i + 1], axis=0)
    if kieu == 'port':
        ok = ((tv20 >= 10e9) & (d['roe'] >= 12) & (d['np_ttm'] > 0) & (d['np_ttm_yoy'] >= 0)
              & (d['pe_rel'] <= 0.8) & (dd <= -0.25))
    else:
        ok = (tv20 >= 10e9) & (dd <= -0.30)
    ok = np.nan_to_num(ok, nan=0).astype(bool)
    ev = []
    last = np.full(M, -10 ** 9)
    for i in range(260, N - 1):
        for j in np.where(ok[i])[0]:
            if i - last[j] >= cooldown:
                ev.append((i, j))
                last[j] = i
    vni = d['vni']
    hi_v = np.array([np.nanmax(vni[max(0, i - 249):i + 1]) for i in range(N)])
    out = []
    for i, j in ev:
        out.append(dict(i=i, j=j, ngay=str(d['cal'][i]), ma=str(d['sym'][j]), du_h=(i + H < N),
                        vni_dd=float(vni[i] / hi_v[i] - 1), dd=float(dd[i, j]),
                        pe_rel=float(d['pe_rel'][i, j]) if not np.isnan(d['pe_rel'][i, j]) else None))
    return out


# ---------------------------------------------------------------- mô phỏng một sự kiện
def mo_phong(d, e, cl, H=250, ma20=None):
    """cl: dict chiến lược. Trả về giá trị cuối, đường vốn, % giải ngân, giá vốn/giá đợt 1."""
    C, O = d['C'], d['O']
    i0, j = e['i'], e['j']
    N = C.shape[0]
    end = min(i0 + H, N - 1)
    c = C[i0:end + 1, j].astype(np.float64)
    o = O[i0:end + 1, j].astype(np.float64)
    c = P._ffill(c[:, None])[:, 0]
    o = np.where(np.isnan(o), c, o)
    m20 = ma20[i0:end + 1, j] if ma20 is not None else None
    T = len(c) - 1
    n_dot = cl['dot']
    phan = [1.0 / n_dot] * n_dot
    if cl.get('ty_le'):
        phan = cl['ty_le']
    cash, sh = 1.0, 0.0
    p1 = None
    cho = []          # các lệnh chờ khớp ở phiên sau: (tỷ lệ ngân sách)
    eq = np.empty(T + 1)
    trang = dict(chay=False, ngay_chay=None, base_hi=None, ngay_dot=[], dung=False)
    N_b, k_b = cl.get('N', 10), cl.get('k', 0.10)
    R = cl.get('R', 0.10)
    DL = cl.get('deadline', 120)
    stop = cl.get('stop')

    def mua(t, w):
        nonlocal cash, sh
        w = min(w, cash)
        if w <= 1e-9:
            return
        sh += w / o[t]
        cash -= w
        von_da_mua.append(w)
        trang['ngay_dot'].append(t)

    trang['xong'] = False
    von_da_mua = []
    trang['dot'] = 0                     # số đợt đã ĐẶT lệnh (để lấy tỷ lệ phan[])

    def dat(w, het=False):
        cho.append(w)
        trang['dot'] += 1
        if het or trang['dot'] >= n_dot:
            trang['xong'] = True

    if cl['kieu'] != 'doi_nen':
        dat(phan[0])
    for t in range(1, T + 1):
        if cho and not trang['dung']:
            for w in cho:
                mua(t, w)
                if p1 is None:
                    p1 = o[t]
            cho = []
        cash *= (1 + CASH_D)
        ref = (sum(von_da_mua) / sh) if (cl.get('stop_von') and sh > 0) else p1
        if stop and ref is not None and not trang['dung'] and c[t] < ref * (1 - stop):
            cash += sh * (o[t + 1] if t + 1 <= T else c[t])
            sh = 0.0
            trang['dung'] = True
        eq[t] = cash + sh * c[t]
        # dừng mua thêm khi giá dưới giá vốn bình quân −x% (rà lại luận điểm, không bình quân giá xuống)
        if cl.get('dung_mua') and sh > 0 and not trang['xong'] and c[t] < (sum(von_da_mua) / sh) * (1 - cl['dung_mua']):
            trang['xong'] = True
            trang['dung_mua'] = True
        if trang['dung'] or trang['xong'] or t >= T:
            continue
        k = cl['kieu']
        con = sum(phan[trang['dot']:])
        if k == 'dca':
            if t >= cl['gian'] * trang['dot']:
                dat(phan[trang['dot']])
            continue
        if k == 'trung_binh_gia':
            if p1 and c[t] <= p1 * (1 - cl['x'] * trang['dot']):
                dat(phan[trang['dot']])
            elif t >= DL:
                if cl.get('het_han') == 'mua':
                    dat(con, het=True)
                else:
                    trang['xong'] = True
            continue
        t_truoc = trang['ngay_dot'][-1] if trang['ngay_dot'] else 0
        nen = False
        if t - N_b + 1 > t_truoc:
            w = c[t - N_b + 1:t + 1]
            h = (N_b + 1) // 2
            # đi ngang = biên độ hẹp + không trôi (đầu–cuối) + KHÔNG tạo đáy mới ở nửa sau cửa sổ
            nen = ((w.max() / w.min() - 1) <= k_b and abs(w[-1] / w[0] - 1) <= k_b / 2
                   and w[-h:].min() >= w[:-h].min() if N_b > 1 else False)
        if p1 and not trang['chay'] and c[t] >= p1 * (1 + R):
            trang['chay'] = True
            trang['ngay_chay'] = t
            xu = cl.get('chay', 'skip')
            if xu == 'duoi':
                dat(con, het=True)
            elif xu == 'mot_nua':
                cho.append(con / 2)
                trang['con_lai'] = con / 2
            elif xu == 'skip':
                trang['xong'] = True
            else:
                trang['con_lai'] = con
            continue
        if trang['chay']:
            cl_ = trang.get('con_lai', con)
            if m20 is not None and not np.isnan(m20[t]) and c[t] <= m20[t] * 1.01:
                dat(cl_, het=True)
            elif t - trang['ngay_chay'] >= 60:
                if cl.get('het_han', 'mua') == 'mua':
                    dat(cl_, het=True)
                else:
                    trang['xong'] = True
            continue
        if k in ('nen', 'doi_nen'):
            if nen:
                if k == 'nen':
                    dat(phan[trang['dot']])
                else:
                    dat(con, het=True)
                trang['base_hi'] = c[t - N_b + 1:t + 1].max()
            elif t >= DL:
                if cl.get('het_han', 'mua') == 'mua':
                    dat(con, het=True)
                else:
                    trang['xong'] = True
            continue
        if k == 'nen_but_pha':
            if trang['dot'] == 1 and nen:
                dat(phan[1])
                trang['base_hi'] = c[t - N_b + 1:t + 1].max()
            elif trang['dot'] == 2 and trang['base_hi'] and c[t] > trang['base_hi'] * 1.02:
                dat(phan[2])
            elif t >= DL:
                if cl.get('het_han', 'mua') == 'mua':
                    dat(con, het=True)
                else:
                    trang['xong'] = True
            continue
    eq[0] = 1.0
    gia_von = (1 - cash) / sh if sh > 0 and not trang['dung'] else None
    giai_ngan = 1 - cash if not trang['dung'] else 0.0
    peak = np.maximum.accumulate(eq)
    return dict(v=float(eq[-1]), maxdd=float((1 - eq / peak).max()), giai_ngan=float(giai_ngan),
                gia_von_rel=(float(gia_von / p1) if (gia_von and p1) else None),
                dung=trang['dung'], chay=trang['chay'], T=T)


# ---------------------------------------------------------------- chiến lược
def chien_luoc():
    S = {}
    S['L1 · 1 lần'] = dict(kieu='mot_lan', dot=1)
    S['DCA3 · 3 lần, mỗi 20 phiên'] = dict(kieu='dca', dot=3, gian=20)
    S['TBG3 · 3 lần, mua thêm khi −7%/−14% (bắt dao rơi)'] = dict(kieu='trung_binh_gia', dot=3, x=0.07, het_han='mua', deadline=120)
    for N in (5, 10, 15, 20):
        for kb in (0.08, 0.12):
            S[f'N3 · 3 lần, đợt 2-3 sau đi ngang {N} phiên (biên {int(kb*100)}%)'] = dict(kieu='nen', dot=3, N=N, k=kb, chay='hoi_ma20', het_han='mua')
    for chay in ('skip', 'duoi', 'hoi_ma20', 'mot_nua'):
        S[f'N3/{chay} · đi ngang 10 phiên, chạy +10% → {chay}'] = dict(kieu='nen', dot=3, N=10, k=0.10, R=0.10, chay=chay, het_han='mua')
    S['N3/het_han_tien · đi ngang 10 phiên, hết hạn giữ tiền'] = dict(kieu='nen', dot=3, N=10, k=0.10, chay='hoi_ma20', het_han='tien')
    S['NB3 · 1/3 → đi ngang 10 phiên → vượt đỉnh nền +2%'] = dict(kieu='nen_but_pha', dot=3, N=10, k=0.10, chay='hoi_ma20', het_han='mua')
    for N in (10, 15):
        S[f'N2 · 2 lần 50/50, đợt 2 sau đi ngang {N} phiên'] = dict(kieu='nen', dot=2, N=N, k=0.10, chay='hoi_ma20', het_han='mua')
    S['N2b · 2 lần 60/40, đợt 2 sau đi ngang 10 phiên'] = dict(kieu='nen', dot=2, ty_le=[0.6, 0.4], N=10, k=0.10, chay='hoi_ma20', het_han='mua')
    S['W · chưa mua, đợi đi ngang 10 phiên rồi mua hết'] = dict(kieu='doi_nen', dot=1, N=10, k=0.10, het_han='mua')
    S['QT · QUY TẮC CHỐT: hoảng loạn 60/40, còn lại 3 đợt; nền 20 phiên ≤8%; chạy → nửa ngay nửa MA20'] = dict(
        kieu='nen', dot=3, N=20, k=0.08, R=0.10, chay='mot_nua', het_han='mua', theo_trang_thai=True)
    return S


# ---------------------------------------------------------------- thống kê
def boot_ci(diff, thang, B=4000):
    """Bootstrap theo khối tháng cho trung bình chênh lệch."""
    g = defaultdict(list)
    for x, m in zip(diff, thang):
        g[m].append(x)
    keys = list(g)
    arr = [np.array(g[k]) for k in keys]
    res = []
    for _ in range(B):
        pick = RNG.integers(0, len(keys), len(keys))
        s = np.concatenate([arr[p] for p in pick])
        res.append(s.mean())
    return float(np.percentile(res, 5)), float(np.percentile(res, 95))


def mc_danh_muc(R, k=8, B=10000):
    """R: dict tên → mảng lợi suất theo sự kiện (cùng thứ tự). Rút k sự kiện/danh mục."""
    n = len(next(iter(R.values())))
    idx = RNG.integers(0, n, (B, k))
    out = {}
    base = R['L1 · 1 lần'][idx].mean(1)
    for name, r in R.items():
        p = r[idx].mean(1)
        out[name] = dict(p5=round(float(np.percentile(p, 5)) * 100, 1), p50=round(float(np.percentile(p, 50)) * 100, 1),
                         p95=round(float(np.percentile(p, 95)) * 100, 1),
                         xs_lo_10=round(float((p < -0.10).mean()) * 100, 1),
                         hon_L1=round(float((p > base).mean()) * 100, 1))
    return out


def chay(H=250, kieu='port', stop=None, stop_von=False):
    d = P.load()
    ev = [e for e in su_kien(d, kieu, H=H) if e['du_h']]
    ma20 = P.roll_mean(d['C'].astype(np.float64), 20)
    S = chien_luoc()
    R, info = {}, {}
    for name, cl in S.items():
        cl = dict(cl)
        if stop:
            cl['stop'] = stop
            cl['stop_von'] = stop_von
        def _cl(e, cl=cl):
            if cl.get('theo_trang_thai') and e['vni_dd'] <= -0.20:
                return dict(cl, dot=2, ty_le=[0.6, 0.4])
            return cl
        rs = [mo_phong(d, e, _cl(e), H=H, ma20=ma20) for e in ev]
        R[name] = np.array([r['v'] - 1 for r in rs])
        gv = [r['gia_von_rel'] for r in rs if r['gia_von_rel']]
        info[name] = dict(
            tb=round(float(R[name].mean()) * 100, 2), trung_vi=round(float(np.median(R[name])) * 100, 2),
            p10=round(float(np.percentile(R[name], 10)) * 100, 1), p90=round(float(np.percentile(R[name], 90)) * 100, 1),
            maxdd_tb=round(float(np.mean([r['maxdd'] for r in rs])) * 100, 1),
            maxdd_p90=round(float(np.percentile([r['maxdd'] for r in rs], 90)) * 100, 1),
            giai_ngan_tb=round(float(np.mean([r['giai_ngan'] for r in rs])) * 100, 1),
            gia_von_vs_dot1=round((float(np.mean(gv)) - 1) * 100, 2) if gv else None,
            ty_le_chay=round(float(np.mean([r['chay'] for r in rs])) * 100, 1),
            ty_le_dung=round(float(np.mean([r['dung'] for r in rs])) * 100, 1))
    thang = [e['ngay'][:7] for e in ev]
    base = R['L1 · 1 lần']
    for name in S:
        diff = R[name] - base
        lo, hi = boot_ci(diff, thang) if name != 'L1 · 1 lần' else (0.0, 0.0)
        info[name]['chenh_L1'] = round(float(diff.mean()) * 100, 2)
        info[name]['chenh_L1_ci90'] = [round(lo * 100, 2), round(hi * 100, 2)]
        info[name]['thang_L1'] = round(float((diff > 0).mean()) * 100, 1)
        # rủi ro / lợi nhuận
        info[name]['loi_tren_dd'] = round(info[name]['tb'] / info[name]['maxdd_tb'], 2) if info[name]['maxdd_tb'] else None
        # theo giai đoạn và trạng thái thị trường
        for nhan, mask in (('2018_2021', [e['ngay'] < '2022' for e in ev]), ('2022_2025', [e['ngay'] >= '2022' for e in ev]),
                           ('hoang_loan', [e['vni_dd'] <= -0.20 for e in ev]), ('binh_thuong', [e['vni_dd'] > -0.20 for e in ev])):
            m = np.array(mask)
            if m.sum() >= 15:
                info[name][nhan] = dict(n=int(m.sum()), tb=round(float(R[name][m].mean()) * 100, 2),
                                        chenh_L1=round(float(diff[m].mean()) * 100, 2))
    return dict(H=H, kieu=kieu, stop=stop, stop_von=stop_von, n_su_kien=len(ev), n_thang=len(set(thang)),
                tu=ev[0]['ngay'] if ev else None, den=ev[-1]['ngay'] if ev else None,
                chien_luoc=info, monte_carlo=mc_danh_muc(R),
                su_kien_mau=[{k: e[k] for k in ('ngay', 'ma', 'dd', 'pe_rel', 'vni_dd')} for e in ev[:: max(1, len(ev) // 25)]])


if __name__ == '__main__':
    out = {}
    for H in (250, 120):
        out[f'port_H{H}'] = chay(H, 'port')
        print(f'port H{H}', out[f'port_H{H}']['n_su_kien'], 'sự kiện', flush=True)
    out['port_H250_stop7'] = chay(250, 'port', stop=0.07)
    out['port_H250_stop15'] = chay(250, 'port', stop=0.15)
    out['port_H250_stop15_von'] = chay(250, 'port', stop=0.15, stop_von=True)
    out['port_H120_stop15_von'] = chay(120, 'port', stop=0.15, stop_von=True)
    out['gia_H250'] = chay(250, 'gia')
    os.makedirs('evidence', exist_ok=True)
    json.dump(out, open('evidence/r38_giai_ngan.json', 'w'), ensure_ascii=False, indent=1)
    for k, v in out.items():
        print('\n==', k, v['n_su_kien'], 'sự kiện', v['tu'], '→', v['den'])
        for name, s in v['chien_luoc'].items():
            mc = v['monte_carlo'][name]
            print(f"{name[:58]:58s} TB {s['tb']:+6.1f}% TV {s['trung_vi']:+6.1f} p10 {s['p10']:+6.1f} DD {s['maxdd_tb']:5.1f} "
                  f"GN {s['giai_ngan_tb']:5.1f}% vốn {s['gia_von_vs_dot1']} | vs L1 {s['chenh_L1']:+5.2f} {s['chenh_L1_ci90']} thắng {s['thang_L1']}% "
                  f"| MC p5 {mc['p5']} p50 {mc['p50']} hơnL1 {mc['hon_L1']}%")
