# -*- coding: utf-8 -*-
"""R40 — Quản trị sụt giảm cho danh mục khách hàng (anh Sơn 15/10/2026: "sụt giảm to quá, có cách nào tốt hơn").

Khác R38 (đo từng sự kiện), R40 chạy một DANH MỤC THẬT theo lịch 2020→2026:
  · tối đa K vị thế cùng lúc; mỗi sự kiện "tài sản tốt, giá thấp" (màn R38) mở một vị thế nếu còn chỗ;
  · mỗi vị thế dùng quy tắc giải ngân đã chốt (hoảng loạn 60/40, còn lại 3 đợt, nền 20 phiên, chạy → nửa-nửa),
    giữ tối đa 250 phiên; tiền nhàn rỗi hưởng 5%/năm;
  · đo trên NAV cả danh mục: tổng lợi suất, lợi suất năm (CAGR), sụt giảm lớn nhất (max drawdown), tháng tệ nhất,
    so với VN-Index cùng kỳ.
Các lớp bảo vệ thử nghiệm (riêng và kết hợp):
  A. cắt lỗ cố định (giá vốn −15%, −10%) · B. bán nửa ở −8/−10%, phần còn lại ở −15%
  C. cắt lỗ theo biến động (k·σ·√20) · D. bảo vệ lợi nhuận (đã lãi ≥ 20% thì bán khi rơi 12–15% từ đỉnh)
  E. tỷ trọng theo rủi ro (mỗi vị thế mất tối đa r% NAV nếu chạm mức cắt) · F. chỉ mở vị thế mới khi thị trường
     căng thẳng/hoảng loạn (VNI ≤ −10% từ đỉnh 1 năm) · G. trần nhiệt danh mục
Chạy: python research/r40_rui_ro.py → evidence/r40_rui_ro.json
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_data as P  # noqa: E402
import r38_giai_ngan as R  # noqa: E402

CASH_D = 1.05 ** (1 / 250) - 1
QT = dict(kieu='nen', dot=3, N=20, k=0.08, R=0.10, chay='mot_nua', het_han='mua')


def cl_su_kien(e, extra):
    c = dict(QT, **extra)
    if e['vni_dd'] <= -0.20:
        c.update(dot=2, ty_le=[0.6, 0.4])
    return c


def danh_muc(d, ev, ma20, extra, K=8, H=250, chi_khi_cang=False, rui_ro=None, tran_ma=0.20, i_bat_dau=None,
             nhip=None, vni_tren_ma=None, dung_dm=None, k_mo=None):
    """rui_ro: % NAV tối đa mất ở mỗi vị thế nếu chạm mức cắt → tỷ trọng = rui_ro / khoảng cắt (≤ tran_ma)."""
    N = d['C'].shape[0]
    ev = sorted(ev, key=lambda e: e['i'])
    i0 = i_bat_dau if i_bat_dau is not None else ev[0]['i']
    by_day = {}
    for e in ev:
        by_day.setdefault(e['i'], []).append(e)
    cash = 1.0
    vni_all = d['vni']
    vma = {n: np.array([np.nanmean(vni_all[max(0, i - n + 1):i + 1]) for i in range(N)]) for n in (20, 50)}
    mo_gan = []       # ngày mở các vị thế gần đây (giới hạn nhịp)
    dinh_nav = 1.0
    act = []          # (ngày bắt đầu, phân bổ, đường eq, T)
    nav = np.empty(N - i0)
    dung, lo_ma, so_vt, dau_tu = 0, [], 0, []
    for t in range(i0, N):
        cash *= (1 + CASH_D)
        # đóng vị thế hết hạn
        con = []
        for a in act:
            s, A, eq, T, cl = a
            if t - s >= T:
                cash += A * eq[T]
                lo_ma.append(eq[T] - 1)
            else:
                con.append(a)
        act = con
        val = sum(A * eq[t - s] for s, A, eq, T, cl in act)
        V = cash + val
        dinh_nav = max(dinh_nav, V)
        # mở vị thế mới (quyết định cuối phiên t, mô phỏng con khớp từ phiên t+1)
        for e in by_day.get(t, []):
            if len(act) >= (k_mo or K):
                break
            if chi_khi_cang and e['vni_dd'] > -0.10:
                continue
            if vni_tren_ma and vni_all[t] < vma[vni_tren_ma][t]:
                continue                                   # thị trường chưa ngừng rơi: không mở mới
            if nhip and sum(1 for x in mo_gan if t - x < 20) >= nhip:
                continue                                   # giới hạn số vị thế mới mỗi 20 phiên
            if dung_dm and (1 - V / dinh_nav) > dung_dm and vni_all[t] < vma[50][t]:
                continue                                   # danh mục đang sụt sâu + VNI dưới MA50: dừng mở mới
            cl = cl_su_kien(e, extra)
            if rui_ro:
                kc = cl.get('stop') or 0.15
                if cl.get('stop_vol'):
                    kc = R._stop_vol(d['C'], e['i'], e['j'], cl['stop_vol'])
                w = min(tran_ma, rui_ro / kc)
            else:
                w = 1.0 / K
            A = min(V * w, cash)
            if A <= V * 0.02:
                continue
            r = R.mo_phong(d, e, cl, H=H, ma20=ma20)
            eq = r['eq']
            T_ra = len(eq) - 1 if r.get('ngay_ra') is None else min(len(eq) - 1, r['ngay_ra'] + 1)
            cash -= A
            act.append((t, A, eq, T_ra, cl))
            mo_gan.append(t)   # bán hết → giải phóng chỗ ngay phiên sau, tiền quay về quỹ
            so_vt += 1
            dung += int(r['dung'])
        val = sum(A * eq[t - s] for s, A, eq, T, cl in act)
        nav[t - i0] = cash + val
        # tỷ lệ đang thực sự nắm cổ phiếu ≈ phần đã giải ngân trong các vị thế (ước theo eq không có tiền: bỏ qua) → dùng số vị thế
        dau_tu.append(len(act) / K)
    cal = d['cal'][i0:]
    vni = d['vni'][i0:]
    return nav, cal, vni, dict(so_vi_the=so_vt, ty_le_dung=round(dung / max(so_vt, 1) * 100, 1),
                               lo_ma_xau_nhat=round(min(lo_ma) * 100, 1) if lo_ma else None,
                               lo_ma_p10=round(float(np.percentile(lo_ma, 10)) * 100, 1) if lo_ma else None,
                               ty_le_cho_dung=round(float(np.mean(dau_tu)) * 100, 1))


def chi_so(nav, cal, vni):
    n = len(nav)
    nam = n / 250
    tong = nav[-1] / nav[0] - 1
    cagr = (nav[-1] / nav[0]) ** (1 / nam) - 1
    pk = np.maximum.accumulate(nav)
    dd = 1 - nav / pk
    k = int(dd.argmax())
    k0 = int(np.argmax(nav[:k + 1]))
    m20 = nav[20:] / nav[:-20] - 1
    r = np.diff(np.log(nav))
    v_t = vni[-1] / vni[0] - 1
    v_dd = 1 - vni / np.maximum.accumulate(vni)
    theo_nam = {}
    for y in sorted({c[:4] for c in cal}):
        idx = [i for i, c in enumerate(cal) if c[:4] == y]
        a = max(idx[0] - 1, 0)
        theo_nam[y] = dict(danh_muc=round((nav[idx[-1]] / nav[a] - 1) * 100, 1), vni=round((vni[idx[-1]] / vni[a] - 1) * 100, 1))
    return dict(tu=str(cal[0]), den=str(cal[-1]), so_nam=round(nam, 2),
                tong_loi_suat=round(tong * 100, 1), loi_suat_nam=round(cagr * 100, 1),
                sut_giam_max=round(float(dd.max()) * 100, 1), sut_tu=str(cal[k0]), sut_den=str(cal[k]),
                thang_te_nhat=round(float(m20.min()) * 100, 1),
                sharpe=round(float((r.mean() * 250 - 0.05) / (r.std() * np.sqrt(250))), 2),
                calmar=round(cagr / dd.max(), 2) if dd.max() > 0 else None,
                vni_tong=round(v_t * 100, 1), vni_nam=round(((1 + v_t) ** (1 / nam) - 1) * 100, 1),
                vni_sut_giam_max=round(float(v_dd.max()) * 100, 1), theo_nam=theo_nam)


PHUONG_AN = {
    'A0 · không cắt lỗ': (dict(), {}),
    'A1 · bán −15% giá vốn + ngừng mua −7% (đang dùng)': (dict(stop=0.15, stop_von=True, dung_mua=0.07), {}),
    'A2 · bán −10% giá vốn + ngừng mua −5%': (dict(stop=0.10, stop_von=True, dung_mua=0.05), {}),
    'B1 · bán nửa −8%, còn lại −15%': (dict(stop=0.15, stop_von=True, ban_nua=0.08, dung_mua=0.07), {}),
    'B2 · bán nửa −10%, còn lại −15%': (dict(stop=0.15, stop_von=True, ban_nua=0.10, dung_mua=0.07), {}),
    'C1 · cắt theo biến động 2,0σ√20 (8–20%)': (dict(stop_vol=2.0, stop_von=True, dung_mua=0.07), {}),
    'D1 · −15% + bảo vệ lãi (lãi ≥20% → bán khi rơi 15% từ đỉnh)': (dict(stop=0.15, stop_von=True, dung_mua=0.07, trail=(0.20, 0.15)), {}),
    'D2 · −15% + bảo vệ lãi (lãi ≥15% → rơi 12%)': (dict(stop=0.15, stop_von=True, dung_mua=0.07, trail=(0.15, 0.12)), {}),
    'E1 · −15% + tỷ trọng theo rủi ro 1,5% NAV/mã': (dict(stop=0.15, stop_von=True, dung_mua=0.07), dict(rui_ro=0.015)),
    'E2 · bán nửa −10% + tỷ trọng rủi ro 1,5% NAV/mã': (dict(stop=0.15, stop_von=True, ban_nua=0.10, dung_mua=0.07), dict(rui_ro=0.015)),
    'F1 · −15% + chỉ mở mới khi VNI ≤ −10%': (dict(stop=0.15, stop_von=True, dung_mua=0.07), dict(chi_khi_cang=True)),
    'F2 · không cắt + chỉ mở mới khi VNI ≤ −10%': (dict(), dict(chi_khi_cang=True)),
    'G1 · bán nửa −10% + bảo vệ lãi + chỉ khi VNI ≤ −10%': (dict(stop=0.15, stop_von=True, ban_nua=0.10, dung_mua=0.07, trail=(0.20, 0.15)), dict(chi_khi_cang=True)),
    'G2 · bán nửa −10% + bảo vệ lãi + rủi ro 1,5%': (dict(stop=0.15, stop_von=True, ban_nua=0.10, dung_mua=0.07, trail=(0.20, 0.15)), dict(rui_ro=0.015)),
    'H1 · F1 + tối đa 2 vị thế mới/20 phiên': (dict(stop=0.15, stop_von=True, dung_mua=0.07), dict(chi_khi_cang=True, nhip=2)),
    'H2 · F1 + chỉ mở khi VNI ≥ MA20 (thị trường ngừng rơi)': (dict(stop=0.15, stop_von=True, dung_mua=0.07), dict(chi_khi_cang=True, vni_tren_ma=20)),
    'H3 · F1 + dừng mở mới khi danh mục sụt >10% và VNI < MA50': (dict(stop=0.15, stop_von=True, dung_mua=0.07), dict(chi_khi_cang=True, dung_dm=0.10)),
    'H4 · F1 + nhịp 2 + VNI ≥ MA20 + dừng khi sụt >10%': (dict(stop=0.15, stop_von=True, dung_mua=0.07), dict(chi_khi_cang=True, nhip=2, vni_tren_ma=20, dung_dm=0.10)),
    'H5 · H4 + bảo vệ lãi (≥15% → rơi 12%)': (dict(stop=0.15, stop_von=True, dung_mua=0.07, trail=(0.15, 0.12)), dict(chi_khi_cang=True, nhip=2, vni_tren_ma=20, dung_dm=0.10)),
    'H6 · H4 + tối đa 6 vị thế (giữ ≥25% tiền)': (dict(stop=0.15, stop_von=True, dung_mua=0.07), dict(chi_khi_cang=True, nhip=2, vni_tren_ma=20, dung_dm=0.10, k_mo=6)),
    'H7 · không cắt + nhịp 2 + VNI ≥ MA20 + chỉ khi VNI ≤ −10%': (dict(), dict(chi_khi_cang=True, nhip=2, vni_tren_ma=20)),
}


if __name__ == '__main__':
    d = P.load()
    ev = R.su_kien(d, 'port')        # gồm cả sự kiện chưa đủ 12 tháng: danh mục chạy tới phiên cuối
    ma20 = P.roll_mean(d['C'].astype(np.float64), 20)
    out = {}
    for name, (extra, kw) in PHUONG_AN.items():
        for K in (8,):
            nav, cal, vni, info = danh_muc(d, ev, ma20, extra, K=K, **kw)
            m = chi_so(nav, cal, vni)
            m.update(info)
            out[name] = m
            print(f"{name[:58]:58s} tổng {m['tong_loi_suat']:+7.1f}% năm {m['loi_suat_nam']:+5.1f}% sụt max {m['sut_giam_max']:5.1f}% "
                  f"({m['sut_tu']}→{m['sut_den']}) tháng tệ {m['thang_te_nhat']:+5.1f}% Sharpe {m['sharpe']} Calmar {m['calmar']} "
                  f"| mã xấu nhất {m['lo_ma_xau_nhat']} p10 {m['lo_ma_p10']} | VT {m['so_vi_the']} giữ chỗ {m['ty_le_cho_dung']}%", flush=True)
    m0 = next(iter(out.values()))
    print(f"\nVN-Index cùng kỳ {m0['tu']}→{m0['den']}: tổng {m0['vni_tong']:+.1f}% năm {m0['vni_nam']:+.1f}% sụt max {m0['vni_sut_giam_max']:.1f}%")
    os.makedirs('evidence', exist_ok=True)
    json.dump(out, open('evidence/r40_rui_ro.json', 'w'), ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- độ bền: lưới tham số, chia giai đoạn, Monte Carlo bỏ ngẫu nhiên sự kiện
def do_ben(d, ev, ma20):
    base = dict(stop=0.15, stop_von=True, dung_mua=0.07)
    out = {'luoi': [], 'giai_doan': {}, 'monte_carlo': {}}
    for nh in (1, 2, 3, None):
        for ng in (-0.08, -0.10, -0.15):
            for K in (6, 8, 10):
                ev2 = [dict(e, vni_dd=e['vni_dd'] - (ng + 0.10)) for e in ev]   # dời ngưỡng: điều kiện vni_dd ≤ ng
                nav, cal, vni, info = danh_muc(d, ev2, ma20, base, K=K, chi_khi_cang=True, nhip=nh)
                m = chi_so(nav, cal, vni)
                out['luoi'].append(dict(nhip=nh, nguong=ng, K=K, tong=m['tong_loi_suat'], nam=m['loi_suat_nam'],
                                        sut=m['sut_giam_max'], calmar=m['calmar'], so_vt=info['so_vi_the']))
    # chia giai đoạn: chạy riêng từ 2023
    i23 = int(np.searchsorted(d['cal'], '2023-01-01'))
    for nhan, kw, ex in (('A1', {}, base), ('H1', dict(chi_khi_cang=True, nhip=2), base), ('A0', {}, {})):
        for tu, ten in ((None, '2020_2026'), (i23, '2023_2026')):
            evx = [e for e in ev if tu is None or e['i'] >= tu]
            nav, cal, vni, info = danh_muc(d, evx, ma20, ex, K=8, i_bat_dau=tu, **kw)
            m = chi_so(nav, cal, vni)
            out['giai_doan'][f'{nhan}_{ten}'] = {k: m[k] for k in ('tong_loi_suat', 'loi_suat_nam', 'sut_giam_max', 'calmar', 'vni_tong', 'vni_sut_giam_max')}
    # Monte Carlo: mỗi lần bỏ ngẫu nhiên 30% sự kiện (mô phỏng không bắt được mọi cơ hội / chọn khác thứ tự)
    rng = np.random.default_rng(40)
    for nhan, kw, ex in (('A1 · −15% (đang dùng)', {}, base), ('H1 · −15% + chỉ khi VNI ≤ −10% + nhịp 2', dict(chi_khi_cang=True, nhip=2), base),
                         ('A0 · không cắt', {}, {})):
        T, S = [], []
        for _ in range(300):
            evx = [e for e in ev if rng.random() > 0.30]
            nav, cal, vni, info = danh_muc(d, evx, ma20, ex, K=8, i_bat_dau=ev[0]['i'], **kw)
            m = chi_so(nav, cal, vni)
            T.append(m['loi_suat_nam']); S.append(m['sut_giam_max'])
        out['monte_carlo'][nhan] = dict(nam_p5=round(float(np.percentile(T, 5)), 1), nam_p50=round(float(np.percentile(T, 50)), 1),
                                       nam_p95=round(float(np.percentile(T, 95)), 1), sut_p50=round(float(np.percentile(S, 50)), 1),
                                       sut_p95=round(float(np.percentile(S, 95)), 1), thua_vni_nam=round(float(np.mean(np.array(T) < 9.3)) * 100, 1))
    return out


if __name__ == '__main__' and os.environ.get('R40_DO_BEN', '1') == '1':
    d = P.load()
    ev = R.su_kien(d, 'port')
    ma20 = P.roll_mean(d['C'].astype(np.float64), 20)
    db = do_ben(d, ev, ma20)
    o = json.load(open('evidence/r40_rui_ro.json'))
    o['_do_ben'] = db
    json.dump(o, open('evidence/r40_rui_ro.json', 'w'), ensure_ascii=False, indent=1)
    for r in db['luoi']:
        print(r)
    print(json.dumps({k: db[k] for k in ('giai_doan', 'monte_carlo')}, ensure_ascii=False, indent=1))
