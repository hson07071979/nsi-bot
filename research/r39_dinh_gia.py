# -*- coding: utf-8 -*-
"""R39 — Giá hợp lý, giá có thể vào, và mục tiêu: cách nào thật sự có hiệu lực? (anh Sơn 15/10/2026)

Câu hỏi
  A. "Rẻ so với chính nó" (P/E, P/B ÷ trung vị 3 năm) có dự báo được lợi suất vượt VN-Index 12 tháng không?
  B. 70% pitching / 30% kết quả kinh doanh: nhóm đặc trưng "thiết lập" (rẻ, bị bán quá, thị trường hoảng loạn)
     so với nhóm "kết quả" (tăng LN, tăng DT, ROE) — nhóm nào dự báo tốt hơn? (IC xếp hạng theo tháng)
  C. Mục tiêu theo "P/E tại đỉnh lợi nhuận cũ" có trúng không? So với MA200, đỉnh cũ 250 phiên, về trung vị P/E.
  D. Ba hạn chế anh Sơn nêu: (1) cổ phiếu vượt đỉnh, (2) không có gì bảo đảm lặp lại (P/E ở các đỉnh khác nhau
     đến đâu), (3) dòng tiền/nhà đầu tư mới làm thay đổi mặt bằng định giá.
  E. Thay thế: mục tiêu XÁC SUẤT theo các ca tương tự trong quá khứ (k láng giềng, chỉ dùng ca ĐÃ xảy ra trước) —
     kiểm tra độ hiệu chỉnh ngoài mẫu.
Chạy: python research/r39_dinh_gia.py  → evidence/r39_dinh_gia.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_data as P  # noqa: E402
import r38_giai_ngan as R38  # noqa: E402

RNG = np.random.default_rng(39)


def _rank(x):
    o = np.argsort(np.argsort(x))
    return o / max(len(x) - 1, 1)


def _spear(a, b):
    m = ~(np.isnan(a) | np.isnan(b))
    if m.sum() < 20:
        return np.nan
    return float(np.corrcoef(_rank(a[m]), _rank(b[m]))[0, 1])


def bang(d, H=250, step=20):
    C, TV = d['C'].astype(np.float64), d['TV']
    N, M = C.shape
    vni = d['vni']
    hi250 = P.roll_max(C, 250)
    ma200 = P.roll_mean(C, 200)
    hi_v = np.array([np.nanmax(vni[max(0, i - 249):i + 1]) for i in range(N)])
    rows = []
    for i in range(500, N - 1, step):
        with np.errstate(all='ignore'):
            tv20 = np.nanmedian(TV[i - 19:i + 1], axis=0)
        ok = (tv20 >= 10e9) & ~np.isnan(C[i])
        e = min(i + H, N - 1)
        full = (i + H) < N
        for j in np.where(ok)[0]:
            c0 = C[i, j]
            if np.isnan(c0):
                continue
            path = C[i:e + 1, j]
            path = path[~np.isnan(path)]
            if len(path) < 10:
                continue
            fwd = path[-1] / c0 - 1
            fv = vni[e] / vni[i] - 1
            rows.append(dict(
                i=i, j=j, ngay=str(d['cal'][i]), ma=str(d['sym'][j]), full=full,
                pe=float(d['pe'][i, j]), pe_rel=float(d['pe_rel'][i, j]), pb_rel=float(d['pb_rel'][i, j]),
                dd=float(c0 / hi250[i, j] - 1), roe=float(d['roe'][i, j]), np_yoy=float(d['np_ttm_yoy'][i, j]),
                rv_yoy=float(d['rev_ttm_yoy'][i, j]), mom120=float(c0 / C[max(0, i - 120), j] - 1) if not np.isnan(C[max(0, i - 120), j]) else np.nan,
                vni_dd=float(vni[i] / hi_v[i] - 1), ma200=float(ma200[i, j]), hi250=float(hi250[i, j]),
                fwd=float(fwd), fwd_x=float((1 + fwd) / (1 + fv) - 1), fwd_max=float(path.max() / c0 - 1)))
    return rows


def A_quintile(rows, key):
    by = defaultdict(list)
    for r in rows:
        if r['full'] and not np.isnan(r[key]):
            by[r['i']].append(r)
    spreads, qmeans = [], defaultdict(list)
    for i, rs in by.items():
        if len(rs) < 25:
            continue
        v = np.array([r[key] for r in rs])
        y = np.array([r['fwd_x'] for r in rs])
        q = np.minimum((_rank(v) * 5).astype(int), 4)
        for k in range(5):
            qmeans[k].append(y[q == k].mean())
        spreads.append(y[q == 0].mean() - y[q == 4].mean())
    s = np.array(spreads)
    n_eff = max(len(s) / 12, 1)   # cửa sổ 12 tháng chồng lấn → ~1 quan sát độc lập/năm
    return dict(key=key, thang=len(s), q=[round(float(np.mean(qmeans[k])) * 100, 1) for k in range(5)],
                q1_tru_q5=round(float(s.mean()) * 100, 1), t_xap_xi=round(float(s.mean() / (s.std(ddof=1) / np.sqrt(n_eff))), 2) if len(s) > 2 else None,
                ty_le_thang_q1_hon_q5=round(float((s > 0).mean()) * 100, 1))


def B_ic(rows, feats):
    by = defaultdict(list)
    for r in rows:
        if r['full']:
            by[r['i']].append(r)
    out = {}
    for name, (key, sign) in feats.items():
        ics = []
        for i, rs in by.items():
            if len(rs) < 25:
                continue
            a = np.array([sign * r[key] for r in rs], dtype=float)
            b = np.array([r['fwd_x'] for r in rs], dtype=float)
            ic = _spear(a, b)
            if not np.isnan(ic):
                ics.append(ic)
        x = np.array(ics)
        n_eff = max(len(x) / 12, 1)
        out[name] = dict(ic_tb=round(float(x.mean()), 3), t_xap_xi=round(float(x.mean() / (x.std(ddof=1) / np.sqrt(n_eff))), 2),
                         thang_duong=round(float((x > 0).mean()) * 100, 1), n_thang=len(x))
    return out


def B_ic_theo_ky(rows, feats, tach='2022-01-01'):
    o = {}
    for nhan, f in (('2019_2021', lambda r: r['ngay'] < tach), ('2022_2025', lambda r: r['ngay'] >= tach)):
        o[nhan] = B_ic([r for r in rows if f(r)], feats)
    return o


def C_muc_tieu(d, ev, H=250):
    C = d['C'].astype(np.float64)
    pe = d['pe']
    npt = d['np_ttm']
    N = C.shape[0]
    ma200 = P.roll_mean(C, 200)
    hi250 = P.roll_max(C, 250)
    out = defaultdict(list)
    for e in ev:
        i, j = e['i'], e['j']
        if i + H >= N:
            continue
        c0 = C[i, j]
        path = C[i + 1:i + H + 1, j]
        path = path[~np.isnan(path)]
        if len(path) < 50:
            continue
        mx = path.max()
        fin = path[-1]
        # đỉnh LN TTM trong 5 năm trước (đến i−60 để đỉnh đã "xác nhận"), P/E trung vị quanh lúc đó
        lo = max(0, i - 1250)
        w = npt[lo:max(lo + 1, i - 60), j]
        if np.all(np.isnan(w)):
            t_pk = None
        else:
            k = int(np.nanargmax(w)) + lo
            pe_pk = np.nanmedian(pe[max(0, k - 20):k + 21, j])
            t_pk = c0 * pe_pk / pe[i, j] if (pe[i, j] > 0 and pe_pk > 0) else None
        tgts = {'P/E tại đỉnh LN cũ': t_pk, 'MA200': ma200[i, j], 'Đỉnh 250 phiên': hi250[i, j],
                'P/E về trung vị 3 năm': (c0 / d['pe_rel'][i, j]) if d['pe_rel'][i, j] > 0 else None}
        for name, t in tgts.items():
            if t is None or np.isnan(t) or t <= c0 * 1.02:
                continue
            up = t / c0 - 1
            hit = np.where(path >= t)[0]
            out[name].append(dict(up=up, hit=len(hit) > 0, t_hit=int(hit[0]) + 1 if len(hit) else None,
                                  fin=fin / c0 - 1, mx=mx / c0 - 1))
    res = {}
    for name, xs in out.items():
        up = np.array([x['up'] for x in xs]); fin = np.array([x['fin'] for x in xs]); mx = np.array([x['mx'] for x in xs])
        th = [x['t_hit'] for x in xs if x['t_hit']]
        res[name] = dict(n=len(xs), upside_tv=round(float(np.median(up)) * 100, 1),
                         ty_le_cham=round(float(np.mean([x['hit'] for x in xs])) * 100, 1),
                         phien_cham_tv=int(np.median(th)) if th else None,
                         ic_upside_vs_loi_suat=round(_spear(up, fin), 3), ic_upside_vs_dinh=round(_spear(up, mx), 3),
                         loi_suat_tv=round(float(np.median(fin)) * 100, 1))
    return res


def D_han_che(d, rows, ev, H=250):
    C = d['C'].astype(np.float64)
    N = C.shape[0]
    hi250 = P.roll_max(C, 250)
    # (1) vượt đỉnh cũ
    vuot, vuot_bao_nhieu = [], []
    for e in ev:
        i, j = e['i'], e['j']
        if i + H >= N:
            continue
        mx = np.nanmax(C[i + 1:i + H + 1, j])
        vuot.append(mx > hi250[i, j])
        if mx > hi250[i, j]:
            vuot_bao_nhieu.append(mx / hi250[i, j] - 1)
    # (2) P/E tại đỉnh giá từng năm của từng mã — có lặp lại không?
    pe = d['pe']
    cal = d['cal']
    years = sorted({c[:4] for c in cal})
    pe_pk = defaultdict(dict)
    for y in years:
        idx = [k for k, c in enumerate(cal) if c[:4] == y]
        if len(idx) < 150:
            continue
        a, b = idx[0], idx[-1] + 1
        with np.errstate(all='ignore'):
            k = np.nanargmax(np.where(np.isnan(C[a:b]), -np.inf, C[a:b]), axis=0) + a
        for j in range(C.shape[1]):
            v = pe[k[j], j]
            if not np.isnan(v):
                pe_pk[j][y] = float(v)
    cv, ratio = [], []
    for j, m in pe_pk.items():
        v = np.array(list(m.values()))
        if len(v) >= 4:
            cv.append(v.std() / v.mean())
            ys = sorted(m)
            for a, b in zip(ys, ys[1:]):
                ratio.append(m[b] / m[a])
    ratio = np.array(ratio)
    # (3) mặt bằng định giá + thanh khoản theo năm
    TV = d['TV']
    nam = {}
    for y in years:
        idx = [k for k, c in enumerate(cal) if c[:4] == y]
        if not idx:
            continue
        with np.errstate(all='ignore'):
            _m = float(np.nanmedian(pe[idx]))
            nam[y] = dict(pe_trung_vi=None if np.isnan(_m) else round(_m, 1),
                          gtgd_tb_ngay_ty=round(float(np.nansum(TV[idx]) / len(idx) / 1e9)),
                          so_ma_gtgd_10ty=int(np.nanmean(np.sum(TV[idx] >= 10e9, axis=1))))
    return dict(
        vuot_dinh_cu=dict(n=len(vuot), ty_le=round(float(np.mean(vuot)) * 100, 1),
                          vuot_tv=round(float(np.median(vuot_bao_nhieu)) * 100, 1) if vuot_bao_nhieu else None),
        pe_tai_dinh=dict(so_ma=len(cv), he_so_bien_thien_tv=round(float(np.median(cv)), 2),
                         ty_le_nam_sau_tren_duoi=[round(float(np.percentile(ratio, p)), 2) for p in (10, 25, 50, 75, 90)],
                         ty_le_lech_qua_30pct=round(float(np.mean((ratio < 0.77) | (ratio > 1.3))) * 100, 1)),
        theo_nam=nam)


def E_xac_suat(rows, k=40, H=250):
    """Mục tiêu xác suất theo ca tương tự: đặc trưng chuẩn hóa xếp hạng; chỉ láng giềng có ngày + H < ngày hiện tại."""
    feats = ['pe_rel', 'pb_rel', 'dd', 'np_yoy', 'roe', 'vni_dd', 'mom120']
    X = np.array([[r[f] for f in feats] for r in rows], dtype=float)
    ok = ~np.isnan(X).any(1)
    rows = [r for r, o in zip(rows, ok) if o]
    X = X[ok]
    # chuẩn hóa thô bằng phân vị toàn mẫu (chỉ dùng để đo khoảng cách)
    lo, hi = np.percentile(X, 5, 0), np.percentile(X, 95, 0)
    Z = np.clip((X - lo) / np.maximum(hi - lo, 1e-9), 0, 1)
    idx_i = np.array([r['i'] for r in rows])
    fwd = np.array([r['fwd'] for r in rows]); mx = np.array([r['fwd_max'] for r in rows])
    full = np.array([r['full'] for r in rows])
    order = np.argsort(idx_i)
    cover50, cover75, cover25, ics, preds, reals = [], [], [], [], [], []
    hit_t = []
    for n, q in enumerate(order):
        if not full[q]:
            continue
        past = np.where((idx_i + H < idx_i[q]) & full)[0]
        if len(past) < 300:
            continue
        dist = np.abs(Z[past] - Z[q]).sum(1)
        nb = past[np.argsort(dist)[:k]]
        p25, p50, p75 = np.percentile(fwd[nb], [25, 50, 75])
        tgt = np.percentile(mx[nb], 50)       # mức đỉnh mà một nửa ca tương tự đã chạm
        cover25.append(fwd[q] >= p25); cover50.append(fwd[q] >= p50); cover75.append(fwd[q] >= p75)
        hit_t.append(mx[q] >= tgt)
        preds.append(p50); reals.append(fwd[q])
    preds, reals = np.array(preds), np.array(reals)
    return dict(n=len(preds), ty_le_vuot_p25=round(float(np.mean(cover25)) * 100, 1),
                ty_le_vuot_p50=round(float(np.mean(cover50)) * 100, 1), ty_le_vuot_p75=round(float(np.mean(cover75)) * 100, 1),
                ty_le_cham_muc_tieu_tv=round(float(np.mean(hit_t)) * 100, 1),
                ic_du_bao=round(_spear(preds, reals), 3),
                ghi_chu='Hiệu chỉnh tốt khi tỷ lệ vượt p25/p50/p75 gần 75/50/25%. Láng giềng chỉ lấy ca đã kết thúc trước ngày dự báo.')


def F_hoang_loan(rows):
    """Buffett: tài sản tốt ở giá thấp khi thị trường hoảng loạn. So lợi suất vượt VNI 12 tháng."""
    good = lambda r: (r['roe'] >= 15) and (r['np_yoy'] >= 0) and r['full']
    out = {}
    for nhan, f in (('hoang_loan (VNI ≤ −20% từ đỉnh 1 năm)', lambda r: r['vni_dd'] <= -0.20),
                    ('cang thang (−20% < VNI ≤ −10%)', lambda r: -0.20 < r['vni_dd'] <= -0.10),
                    ('binh thuong (VNI > −10%)', lambda r: r['vni_dd'] > -0.10)):
        xs = [r for r in rows if good(r) and f(r)]
        ys = [r for r in rows if r['full'] and f(r)]
        re = [r for r in xs if r['pe_rel'] <= 0.8]
        if len(xs) >= 20:
            out[nhan] = dict(
                tot_n=len(xs), tot_loi_suat_tb=round(float(np.mean([r['fwd'] for r in xs])) * 100, 1),
                tot_vuot_vni_tb=round(float(np.mean([r['fwd_x'] for r in xs])) * 100, 1),
                tot_re_n=len(re), tot_re_loi_suat_tb=round(float(np.mean([r['fwd'] for r in re])) * 100, 1) if re else None,
                tot_re_vuot_vni_tb=round(float(np.mean([r['fwd_x'] for r in re])) * 100, 1) if re else None,
                ca_thi_truong_loi_suat_tb=round(float(np.mean([r['fwd'] for r in ys])) * 100, 1),
                so_thang=len({r['i'] for r in xs}))
    return out


if __name__ == '__main__':
    d = P.load()
    rows = bang(d)
    print('bảng', len(rows), 'dòng', flush=True)
    ev = [e for e in R38.su_kien(d, 'port') if e['du_h']]
    feats = {'Thiết lập: P/E rẻ so với chính nó (−pe_rel)': ('pe_rel', -1),
             'Thiết lập: P/B rẻ so với chính nó (−pb_rel)': ('pb_rel', -1),
             'Thiết lập: bị bán sâu từ đỉnh (−dd)': ('dd', -1),
             'Thiết lập: động lượng 6 tháng yếu (−mom120)': ('mom120', -1),
             'Kết quả: LN 4 quý tăng (np_yoy)': ('np_yoy', 1),
             'Kết quả: DT 4 quý tăng (rv_yoy)': ('rv_yoy', 1),
             'Kết quả: ROE cao (roe)': ('roe', 1),
             'Đối chứng: động lượng 6 tháng mạnh (+mom120)': ('mom120', 1)}
    out = dict(
        n_dong=len(rows), tu=rows[0]['ngay'], den=rows[-1]['ngay'],
        A=[A_quintile(rows, k) for k in ('pe_rel', 'pb_rel', 'dd')],
        B=B_ic(rows, feats), B_theo_ky=B_ic_theo_ky(rows, feats),
        C=C_muc_tieu(d, ev), D=D_han_che(d, rows, ev), E=E_xac_suat(rows), F=F_hoang_loan(rows))
    json.dump(out, open('evidence/r39_dinh_gia.json', 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------- G. xác suất chạm mục tiêu (thay cho "điểm" mục tiêu)
def G_xac_suat_cham(d, ev, H=120):
    """Xác suất chạm mục tiêu trong H phiên theo bước ngẫu nhiên KHÔNG trôi (nguyên lý phản xạ):
       p = 2·(1 − Φ(ln(T/P) / (σ·√H))), σ = độ lệch chuẩn lợi suất ngày 60 phiên trước.
       Kiểm tra hiệu chỉnh: nhóm theo xác suất dự báo, so với tần suất chạm thực tế."""
    from math import erf, sqrt, log
    Phi = lambda x: 0.5 * (1 + erf(x / sqrt(2)))
    C = d['C'].astype(np.float64)
    N = C.shape[0]
    ma200 = P.roll_mean(C, 200)
    hi250 = P.roll_max(C, 250)
    pr, hit = [], []
    for e in ev:
        i, j = e['i'], e['j']
        if i + H >= N or i < 61:
            continue
        c0 = C[i, j]
        r = np.diff(np.log(C[i - 60:i + 1, j]))
        r = r[~np.isnan(r)]
        if len(r) < 40:
            continue
        sd = r.std()
        path = C[i + 1:i + H + 1, j]
        for T in (ma200[i, j], hi250[i, j], c0 * 1.10, c0 * 1.20, c0 * 1.30):
            if np.isnan(T) or T <= c0 * 1.02:
                continue
            p = 2 * (1 - Phi(log(T / c0) / (sd * sqrt(H))))
            pr.append(p)
            hit.append(bool(np.nanmax(path) >= T))
    pr, hit = np.array(pr), np.array(hit)
    out = []
    for a, b in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)):
        m = (pr >= a) & (pr < b)
        if m.sum() >= 20:
            out.append(dict(nhom=f'{int(a*100)}–{int(min(b,1)*100)}%', n=int(m.sum()),
                            du_bao_tb=round(float(pr[m].mean()) * 100, 1), thuc_te=round(float(hit[m].mean()) * 100, 1)))
    return dict(H=H, n=len(pr), bang=out, brier=round(float(np.mean((pr - hit) ** 2)), 3),
                brier_doan_mo=round(float(np.mean((hit.mean() - hit) ** 2)), 3))


def H_ic_theo_trang_thai(rows):
    """IC của tổ hợp 'thiết lập' và tổ hợp 'kết quả' theo trạng thái thị trường."""
    by = defaultdict(list)
    for r in rows:
        if r['full']:
            by[r['i']].append(r)
    res = defaultdict(lambda: defaultdict(list))
    for i, rs in by.items():
        if len(rs) < 25:
            continue
        st = 'hoang_loan' if rs[0]['vni_dd'] <= -0.20 else ('cang_thang' if rs[0]['vni_dd'] <= -0.10 else 'binh_thuong')
        y = np.array([r['fwd_x'] for r in rs])
        def comp(keys):
            Z = []
            for k, s in keys:
                v = np.array([s * r[k] for r in rs], dtype=float)
                m = ~np.isnan(v)
                z = np.full(len(v), np.nan)
                z[m] = _rank(v[m])
                Z.append(z)
            return np.nanmean(np.array(Z), 0)
        res[st]['thiet_lap'].append(_spear(comp([('pe_rel', -1), ('pb_rel', -1)]), y))
        res[st]['ket_qua'].append(_spear(comp([('np_yoy', 1), ('rv_yoy', 1), ('roe', 1)]), y))
        res[st]['70_30'].append(_spear(0.7 * comp([('pe_rel', -1), ('pb_rel', -1)]) + 0.3 * comp([('np_yoy', 1), ('rv_yoy', 1), ('roe', 1)]), y))
    out = {}
    for st, dct in res.items():
        out[st] = {k: dict(ic_tb=round(float(np.nanmean(v)), 3), n_thang=int(np.sum(~np.isnan(v)))) for k, v in dct.items()}
    return out


if __name__ == '__main__' and os.environ.get('R39_THEM', '1') == '1':
    d = P.load()
    ev = [e for e in R38.su_kien(d, 'port') if e['du_h']]
    o = json.load(open('evidence/r39_dinh_gia.json'))
    o['G'] = {f'H{H}': G_xac_suat_cham(d, ev, H) for H in (60, 120, 250)}
    o['H'] = H_ic_theo_trang_thai(bang(d))
    json.dump(o, open('evidence/r39_dinh_gia.json', 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({'G': o['G'], 'H': o['H']}, ensure_ascii=False, indent=1))
