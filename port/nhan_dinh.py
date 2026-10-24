# -*- coding: utf-8 -*-
"""Nhận định hằng ngày bằng code + chấm đúng/sai + vòng học (anh Sơn 22/10/2026).

Mỗi chiều, code ghi một nhận định cho từng mã: TĂNG / ĐI NGANG / GIẢM so với VN-Index trong 5, 20 và 60 phiên tới,
kèm lý do (đặc trưng nào đẩy điểm lên/xuống). Sau đủ phiên, code tự chấm:
  tăng đúng khi mã vượt VN-Index; giảm đúng khi mã thua VN-Index; đi ngang đúng khi chênh lệch nằm trong biên
  (±2% cho 5 phiên, ±4% cho 20 phiên, ±7% cho 60 phiên).

Vòng học:
  1. Trọng số ĐANG DÙNG nằm ở port/trong_so.json (nhánh port-data). Chưa có file thì dùng bộ v1 viết tay dưới đây.
  2. Mỗi lượt chạy, code chạy lùi cùng cách tính trên lịch sử giá + BCTC (chỉ dùng BCTC đã công bố tính tới ngày đó)
     để có vài nghìn mẫu, rồi luyện một mô hình hồi quy logistic theo kiểu đi tiến (luyện trên các năm trước, thử trên
     năm sau). Kết quả: bảng so trọng số đang dùng với trọng số đề xuất, trên các năm mô hình CHƯA THẤY.
  3. (24/10/2026) Qua bài thi thì máy TỰ ĐỔI trọng số và báo chuông (tu_hoc.py, bộ mới ở state/trong_so_tu_hoc.json,
     bộ cũ giữ trong state/lich_su_trong_so_tu_hoc.json). Hai lần đổi cách nhau ít nhất 28 ngày.
Đặc trưng của 3 máy (bot/Tin/Daily) chưa có lịch sử nên chỉ ghi kèm từ nay; khi đủ mẫu mới đưa vào mô hình.

Nâng cấp R41 (anh Sơn duyệt 22/10/2026), sau khi kiểm trên 169 mã thanh khoản 2019→10/2026 (research/r41_vong_hoc.py):
  · Thước đo chính đổi từ "% đoán đúng chiều" (gần như tung đồng xu với mọi bộ trọng số) sang khả năng XẾP HẠNG:
    IC = tương quan hạng giữa điểm hôm nay và mức hơn/kém VN-Index sau n phiên, chênh lệch nhóm 20% điểm cao nhất
    với 20% thấp nhất, và % số lần nhóm điểm cao thật sự hơn VN-Index. Vẫn giữ % đúng để đối chiếu.
  · Nhận định theo HẠNG trong ngày: điểm thuộc 30% cao nhất của nhóm mã theo dõi → tăng, 30% thấp nhất → giảm,
    còn lại → đi ngang (ít hơn 10 mã thì dùng ngưỡng cũ). Bộ trọng số nào cũng so được với nhau, không phụ thuộc thang.
  · Mô hình đề xuất = hồi quy ridge trên đặc trưng chuẩn hóa, nhắm HẠNG mức hơn VN-Index (không phải lên/xuống),
    luyện riêng từng kỳ hạn, đi tiến theo năm. Chỉ đề xuất khi hơn bộ đang dùng ở ≥ 2/3 số năm chưa thấy VÀ IC
    tổng có t ≥ 2. (Từ 24/10/2026 qua bài thi thì tự đổi — xem mục 3.)
  · Thêm 2 đặc trưng: mạnh hơn VN-Index 120 phiên, tiền từ kinh doanh ÷ lãi 4 quý.
"""
from __future__ import annotations

import math
from datetime import date

import numpy as np

KY = (5, 20, 60)
BIEN = {5: 2.0, 20: 4.0, 60: 7.0}
NGUONG = 0.25          # điểm > +0,25 → tăng; < −0,25 → giảm; còn lại đi ngang
DAC_TRUNG = ('rs20', 'rs60', 'ma50', 'ma200', 'dinh250', 'bien_dong', 'ln_yoy', 'dt_yoy', 'dinh_gia', 'thi_truong',
             'rs120', 'cfo_ln')
TY_LE_CHIEU = 0.30     # 30% điểm cao nhất trong ngày → tăng; 30% thấp nhất → giảm
MIN_XEP_HANG = 10      # ít mã hơn thì dùng ngưỡng điểm tuyệt đối NGUONG
TEN = dict(rs20='mạnh hơn VN-Index 20 phiên', rs60='mạnh hơn VN-Index 60 phiên', ma50='giá so với MA50',
           ma200='giá so với MA200', dinh250='cách đỉnh 250 phiên', bien_dong='biến động 20 phiên',
           ln_yoy='lợi nhuận quý gần nhất so cùng kỳ', dt_yoy='doanh thu quý gần nhất so cùng kỳ',
           dinh_gia='định giá so với trung vị 12 quý (âm = rẻ hơn)', thi_truong='VN-Index so với MA50',
           rs120='mạnh hơn VN-Index 120 phiên', cfo_ln='tiền từ kinh doanh ÷ lãi 4 quý')
# Bộ v1 viết tay (trên đặc trưng đã chuẩn hóa): đà giá + tăng trưởng thì cộng, đắt so với chính nó thì trừ.
TRONG_SO_V1 = dict(ten='v1 viết tay 22/10/2026', w=dict(rs20=0.15, rs60=0.35, ma50=0.25, ma200=0.15, dinh250=0.0,
                                                       bien_dong=-0.10, ln_yoy=0.25, dt_yoy=0.10, dinh_gia=-0.25,
                                                       thi_truong=0.10, rs120=0.0, cfo_ln=0.0), b=0.0)
# Bộ v2 (R41, CHỜ anh Sơn duyệt — chưa dùng): kiểm trên 169 mã 2021→10/2026, kỳ hạn 20 phiên IC +0,059 (dương 5/6 năm),
# nhóm 20% điểm cao hơn nhóm 20% thấp +2,0%/20 phiên; v1 chỉ IC −0,017. Lý do chính: trong 20–60 phiên, mã ĐẮT hơn trung vị
# định giá của chính nó (đang được thị trường định giá lại) chạy hơn mã rẻ — v1 để dấu ngược. Ở 12 tháng thì ngược lại
# (rẻ thắng), nên cổng 'giá thấp' của luận điểm port vẫn đúng; đây chỉ là nhận định ngắn hạn.
TRONG_SO_V2 = dict(ten='v2 R41 22/10/2026', w={**{k: 0.0 for k in DAC_TRUNG},
                                               'dinh_gia': 0.5, 'cfo_ln': 0.2, 'rs120': 0.15, 'ma200': 0.15}, b=0.0)
NGANH_PB = ('Ngân hàng', 'Dịch vụ tài chính', 'Bảo hiểm', 'Bất động sản')


# ---------------------------------------------------------------- đặc trưng
def _clip(x, lo, hi):
    return None if x is None or not math.isfinite(x) else max(lo, min(hi, x))


class Bang:
    """Giá đã căn theo lịch VN-Index: c[sym] = mảng giá đóng cửa (NaN ngày không có)."""

    def __init__(self, lich: list[str], vni: list[float], gia: dict[str, dict[str, float]]):
        self.lich = list(lich)
        self.pos = {d: i for i, d in enumerate(self.lich)}
        self.vni = np.array(vni, dtype=float)
        self.c = {}
        for s, m in gia.items():
            a = np.full(len(self.lich), np.nan)
            for d, p in m.items():
                i = self.pos.get(d)
                if i is not None and p:
                    a[i] = p
            self.c[s] = a


def _ret(a, i, n):
    if i - n < 0 or not (a[i] > 0 and a[i - n] > 0):
        return None
    return a[i] / a[i - n] - 1


def _ma(a, i, n):
    if i + 1 < n:
        return None
    w = a[i + 1 - n:i + 1]
    w = w[np.isfinite(w)]
    return float(w.mean()) if len(w) >= int(n * 0.8) else None


def funda_luc(rows: list[dict], d: date) -> dict | None:
    """Quý mới nhất ĐÃ CÔNG BỐ tính tới ngày d (không nhìn trước)."""
    ok = [r for r in rows or [] if r.get('avail') and r['avail'] <= d]
    return ok[-1] if ok else None


def dac_trung(B: Bang, sym: str, i: int, funda_rows: list[dict] | None, sector: str = '') -> dict | None:
    a = B.c.get(sym)
    if a is None or not (a[i] > 0):
        return None
    r20, r60 = _ret(a, i, 20), _ret(a, i, 60)
    v20, v60 = _ret(B.vni, i, 20), _ret(B.vni, i, 60)
    m50, m200 = _ma(a, i, 50), _ma(a, i, 200)
    vm50 = _ma(B.vni, i, 50)
    w = a[max(0, i - 249):i + 1]
    w = w[np.isfinite(w)]
    dr = np.diff(np.log(a[max(0, i - 20):i + 1]))
    dr = dr[np.isfinite(dr)]
    f = dict(
        rs20=_clip((r20 - v20) if r20 is not None and v20 is not None else None, -0.5, 0.5),
        rs60=_clip((r60 - v60) if r60 is not None and v60 is not None else None, -0.8, 0.8),
        ma50=_clip(a[i] / m50 - 1 if m50 else None, -0.5, 0.5),
        ma200=_clip(a[i] / m200 - 1 if m200 else None, -0.8, 0.8),
        dinh250=_clip(a[i] / w.max() - 1 if len(w) >= 120 else None, -0.9, 0.0),
        bien_dong=_clip(float(dr.std()) if len(dr) >= 15 else None, 0, 0.15),
        thi_truong=_clip(B.vni[i] / vm50 - 1 if vm50 else None, -0.3, 0.3),
        ln_yoy=None, dt_yoy=None, dinh_gia=None, rs120=None, cfo_ln=None)
    r120, v120 = _ret(a, i, 120), _ret(B.vni, i, 120)
    if r120 is not None and v120 is not None:
        f['rs120'] = _clip(r120 - v120, -1.0, 1.5)
    d = date.fromisoformat(B.lich[i])
    rows = sorted((r for r in funda_rows or [] if r.get('avail') and r['avail'] <= d),
                  key=lambda r: (r.get('y', 0), r.get('q', 0)))
    if rows:
        m = rows[-1]
        cu = next((r for r in rows if r.get('y') == m.get('y', 0) - 1 and r.get('q') == m.get('q')), None)
        if cu:
            for k, ten in (('npat', 'ln_yoy'), ('rev', 'dt_yoy')):
                x, y = m.get(k), cu.get(k)
                if isinstance(x, (int, float)) and isinstance(y, (int, float)) and y > 0:
                    f[ten] = _clip(x / y - 1, -1.0, 2.0)
        c4, n4 = [r.get('cfo') for r in rows[-4:]], [r.get('npat') for r in rows[-4:]]
        if len(rows) >= 4 and all(isinstance(x, (int, float)) for x in c4 + n4) and sum(n4) > 0:
            f['cfo_ln'] = _clip(sum(c4) / sum(n4), -3.0, 3.0)
        dung_pb = any(k.lower() in (sector or '').lower() for k in NGANH_PB)
        k = 'pb' if dung_pb else 'pe'
        lo, hi = (0, 50) if dung_pb else (0, 200)
        hist = sorted(r[k] for r in rows[-12:] if isinstance(r.get(k), (int, float)) and lo < r[k] < hi)
        hien = m.get(k)
        if len(hist) >= 6 and isinstance(hien, (int, float)) and lo < hien < hi:
            f['dinh_gia'] = _clip(hien / hist[len(hist) // 2] - 1, -0.8, 1.5)
    if f['rs60'] is None or f['ma50'] is None:
        return None
    return f


def nhan(B: Bang, sym: str, i: int, n: int):
    """Chênh lệch % so với VN-Index sau n phiên tính từ phiên i (None nếu chưa đủ phiên)."""
    a = B.c.get(sym)
    if a is None or i + n >= len(B.lich) or not (a[i] > 0 and a[i + n] > 0):
        return None
    return round(((a[i + n] / a[i]) / (B.vni[i + n] / B.vni[i]) - 1) * 100, 2)


# ---------------------------------------------------------------- điểm + nhận định
# Thang mặc định (trung bình, độ lệch) khi chưa có thống kê từ mẫu chạy lùi — ước lượng thô cho cổ phiếu VN.
TK_MAC_DINH = dict(rs20=(0.0, 0.08), rs60=(0.0, 0.15), ma50=(0.0, 0.08), ma200=(0.0, 0.15), dinh250=(-0.2, 0.15),
                   bien_dong=(0.02, 0.01), ln_yoy=(0.1, 0.5), dt_yoy=(0.1, 0.3), dinh_gia=(0.0, 0.3),
                   thi_truong=(0.0, 0.04), rs120=(0.0, 0.25), cfo_ln=(0.8, 1.2))


def chuan_hoa(f: dict, tk: dict) -> dict:
    """Đổi đặc trưng sang thang chuẩn (trừ trung bình, chia độ lệch) theo thống kê của mẫu chạy lùi; thiếu thì 0."""
    out = {}
    for k in DAC_TRUNG:
        x = f.get(k)
        m, s = (tk.get(k) or TK_MAC_DINH[k])
        out[k] = 0.0 if x is None else max(-3.0, min(3.0, (x - m) / (s or 1.0)))
    return out


def diem(z: dict, ts: dict) -> float:
    w = ts.get('w') or {}
    return float(ts.get('b', 0.0) + sum(w.get(k, 0.0) * z.get(k, 0.0) for k in DAC_TRUNG))


def chieu(s: float) -> str:
    return 'tang' if s > NGUONG else ('giam' if s < -NGUONG else 'ngang')


def chieu_theo_hang(diems: list[float]) -> list[str]:
    """Nhận định theo hạng trong cùng một ngày (R41): top 30% → tăng, đáy 30% → giảm. Ít mã thì dùng ngưỡng."""
    n = len(diems)
    if n < MIN_XEP_HANG:
        return [chieu(x) for x in diems]
    o = np.argsort(np.argsort(np.array(diems, dtype=float), kind='stable'), kind='stable')
    k = max(1, int(round(n * TY_LE_CHIEU)))
    return ['tang' if r >= n - k else ('giam' if r < k else 'ngang') for r in o]


def ly_do(z: dict, ts: dict, f: dict, k: int = 3) -> list[str]:
    w = ts.get('w') or {}
    dong = sorted(((w.get(x, 0) * z.get(x, 0), x) for x in DAC_TRUNG), key=lambda t: -abs(t[0]))
    out = []
    for v, x in dong[:k]:
        if abs(v) < 0.03:
            continue
        raw = f.get(x)
        so = '' if raw is None else (f' {raw * 100:+.1f}%' if x != 'bien_dong' else f' {raw * 100:.1f}%/phiên')
        so = so.replace('.', ',').replace('-', '−')
        out.append(f"{TEN[x]}{so} → {'cộng' if v > 0 else 'trừ'} điểm")
    return out


def dung_sai(c: str, ex: float, n: int) -> bool:
    if c == 'tang':
        return ex > 0
    if c == 'giam':
        return ex < 0
    return abs(ex) <= BIEN[n]


# ---------------------------------------------------------------- chạy lùi + mô hình
def thong_ke(rows: list[dict]) -> dict:
    tk = {}
    for k in DAC_TRUNG:
        xs = np.array([r['f'][k] for r in rows if r['f'].get(k) is not None], dtype=float)
        tk[k] = (float(xs.mean()), float(xs.std() or 1.0)) if len(xs) >= 30 else (0.0, 1.0)
    return tk


def chay_lui(B: Bang, syms, funda: dict, nganh: dict, buoc: int = 5, tu: str = '2019-06-01') -> list[dict]:
    """Mẫu lịch sử: mỗi `buoc` phiên một mẫu cho mỗi mã (giảm trùng lặp giữa các mẫu liền nhau)."""
    rows = []
    i0 = next((i for i, d in enumerate(B.lich) if d >= tu), len(B.lich))
    for i in range(max(i0, 200), len(B.lich), buoc):
        for s in syms:
            f = dac_trung(B, s, i, funda.get(s), nganh.get(s, ''))
            if not f:
                continue
            y = {n: nhan(B, s, i, n) for n in KY}
            rows.append(dict(ma=s, ngay=B.lich[i], f=f, y=y))
    return rows


def _ridge(X: np.ndarray, y: np.ndarray, lam: float = 50.0) -> np.ndarray:
    """Hồi quy ridge có hệ số chặn (không phạt hệ số chặn)."""
    n, m = X.shape
    Xb = np.hstack([X, np.ones((n, 1))])
    P = lam * np.eye(m + 1)
    P[-1, -1] = 0.0
    return np.linalg.solve(Xb.T @ Xb + P, Xb.T @ y)


def _mat(rows, tk):
    return np.array([[chuan_hoa(r['f'], tk)[k] for k in DAC_TRUNG] for r in rows], dtype=float)


def _hang(a) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    return np.argsort(np.argsort(a, kind='stable'), kind='stable').astype(float)


def _theo_ngay(rows, n):
    by = {}
    for r in rows:
        if r['y'].get(n) is not None:
            by.setdefault(r['ngay'], []).append(r)
    return by


def _cham_bo(rows, n, ts, tk):
    """Chấm một bộ trọng số trên các mẫu đã có nhãn ở kỳ hạn n.
    Thước đo chính (R41): IC theo ngày, chênh lệch nhóm 20% điểm cao − 20% điểm thấp, % nhóm cao hơn VN-Index.
    Phụ: % đúng chiều (nhận định theo hạng trong ngày) để đối chiếu với sổ hằng ngày."""
    by = _theo_ngay(rows, n)
    if not by:
        return None
    ics, chenh, top_thang, dung, tong, alpha = [], [], [], 0, 0, []
    for xs in by.values():
        sc = [diem(chuan_hoa(r['f'], tk), ts) for r in xs]
        ex = np.array([r['y'][n] for r in xs], dtype=float)
        ch = chieu_theo_hang(sc)
        dung += sum(1 for c, e in zip(ch, ex) if dung_sai(c, e, n))
        tong += len(xs)
        alpha += [e if c == 'tang' else -e for c, e in zip(ch, ex) if c != 'ngang']
        if len(xs) >= MIN_XEP_HANG:
            hs, he = _hang(sc), _hang(ex)
            if hs.std() > 0 and he.std() > 0:
                ics.append(float(np.corrcoef(hs, he)[0, 1]))
            q = max(1, len(xs) // 5)
            o = np.argsort(np.array(sc), kind='stable')
            chenh.append(float(ex[o[-q:]].mean() - ex[o[:q]].mean()))
            top_thang.append(float((ex[o[-q:]] > 0).mean()))
    ic = float(np.mean(ics)) if ics else None
    # t gần đúng: các mẫu cách nhau 5 phiên nên chồng nhãn n/5 lần
    t = (ic / (np.std(ics) or 1.0) * np.sqrt(len(ics) / max(1.0, n / 5))) if len(ics) >= 5 else None
    return dict(mau=tong, ngay=len(by), dung_pct=round(dung / tong * 100, 1) if tong else None,
                alpha_tb=round(float(np.mean(alpha)), 2) if alpha else None,
                ic=None if ic is None else round(ic, 3), ic_t=None if t is None else round(float(t), 1),
                chenh=round(float(np.mean(chenh)), 2) if chenh else None,
                top_thang_pct=round(float(np.mean(top_thang)) * 100, 1) if top_thang else None)


def _luyen(tr, n, tk):
    """Ridge nhắm hạng (trong ngày) của mức hơn VN-Index sau n phiên."""
    X, Y = [], []
    for xs in _theo_ngay(tr, n).values():
        if len(xs) < MIN_XEP_HANG:
            continue
        X.append(_mat(xs, tk))
        Y.append(_hang([r['y'][n] for r in xs]) / (len(xs) - 1) - 0.5)
    if not X:
        return None
    w = _ridge(np.vstack(X), np.concatenate(Y))
    return dict(w={k: float(w[j]) for j, k in enumerate(DAC_TRUNG)}, b=float(w[-1]))


def hoc(rows: list[dict], ts_dang_dung: dict, n_chinh: int = 20) -> dict:
    """Đi tiến theo năm: luyện trên các năm trước (bỏ phần nhãn chồng sang năm thử), chấm trên năm sau.
    So bộ trọng số đang dùng với mô hình ridge trên những năm mô hình CHƯA THẤY.
    Qua bài thi thì `dat_chuan=True`; việc tự đổi + báo chuông do tu_hoc.py làm (anh Sơn chốt 24/10/2026)."""
    nam = sorted({r['ngay'][:4] for r in rows})
    tk_all = thong_ke(rows)
    bang = []
    for y in nam[2:]:
        te = [r for r in rows if r['ngay'][:4] == y]
        moc = date(int(y), 1, 1)
        mo_hinh, mau_luyen = {}, 0
        for n in KY:
            tr = [r for r in rows if r['ngay'][:4] < y and r['y'].get(n) is not None
                  and (moc - date.fromisoformat(r['ngay'])).days > n * 1.5]
            mau_luyen = max(mau_luyen, len(tr))
            if len(tr) < 500 or not te:
                continue
            tk = thong_ke(tr)
            m = _luyen(tr, n, tk)
            if m:
                mo_hinh[n] = _cham_bo(te, n, m, tk)
        if not mo_hinh:
            continue
        tk = thong_ke([r for r in rows if r['ngay'][:4] < y])
        bang.append(dict(nam=y, mau_luyen=mau_luyen,
                         dang_dung={n: _cham_bo(te, n, ts_dang_dung, tk) for n in KY}, mo_hinh=mo_hinh))
    de_xuat = None
    tr = [r for r in rows if r['y'].get(n_chinh) is not None]
    if len(tr) >= 500:
        m = _luyen(tr, n_chinh, tk_all)
        if m:
            de_xuat = dict(ten=f'mô hình ridge {date.today().isoformat()} trên {len(tr)} mẫu (kỳ hạn {n_chinh} phiên)',
                           w={k: round(v, 4) for k, v in m['w'].items()}, b=round(m['b'], 4))

    def tong(key):
        out = {}
        for n in KY:
            xs = [b[key][n] for b in bang if (b[key].get(n) or {}).get('mau')]
            m = sum(x['mau'] for x in xs)
            tb = lambda k: [x[k] for x in xs if x.get(k) is not None]  # noqa: E731
            out[n] = dict(mau=m, dung_pct=round(sum((x['dung_pct'] or 0) * x['mau'] for x in xs) / m, 1) if m else None,
                          alpha_tb=round(float(np.mean(tb('alpha_tb'))), 2) if tb('alpha_tb') else None,
                          ic=round(float(np.mean(tb('ic'))), 3) if tb('ic') else None,
                          chenh=round(float(np.mean(tb('chenh'))), 2) if tb('chenh') else None,
                          top_thang_pct=round(float(np.mean(tb('top_thang_pct'))), 1) if tb('top_thang_pct') else None,
                          nam_hon=sum(1 for b in bang if ((b['mo_hinh'].get(n) or {}).get('ic') or -9)
                                      > ((b['dang_dung'].get(n) or {}).get('ic') or -9)) if key == 'mo_hinh' else None,
                          so_nam=len(xs))
        return out
    t0, t1 = tong('dang_dung'), tong('mo_hinh')
    # IC tổng của mô hình trên toàn bộ ngày thử (để tính t)
    ics = []
    for b in bang:
        x = b['mo_hinh'].get(n_chinh) or {}
        if x.get('ic') is not None:
            ics.append(x['ic'])
    a, c = t1.get(n_chinh) or {}, t0.get(n_chinh) or {}
    hon = bool(de_xuat) and a.get('so_nam') and a.get('nam_hon', 0) * 3 >= a['so_nam'] * 2 \
        and (a.get('ic') or 0) > (c.get('ic') or 0) and (a.get('ic') or 0) > 0
    t_ok = len(ics) >= 3 and np.mean(ics) / (np.std(ics) or 1.0) * np.sqrt(len(ics)) >= 2.0
    if hon and t_ok:
        kl = (f'Mô hình xếp hạng tốt hơn bộ đang dùng ở {a["nam_hon"]}/{a["so_nam"]} năm chưa thấy (kỳ hạn '
              f'{n_chinh} phiên: IC {a["ic"]:+.3f} so với {c.get("ic") or 0:+.3f}) — qua bài thi, máy tự đổi sang bộ mới.')
    elif hon:
        kl = (f'Mô hình nhỉnh hơn ở {a["nam_hon"]}/{a["so_nam"]} năm nhưng chưa đủ chắc (IC không ổn định qua các năm) '
              f'— giữ nguyên, lượt sau chấm lại.')
    else:
        kl = 'Mô hình chưa hơn bộ đang dùng trên những năm chưa thấy — giữ nguyên.'
    return dict(so_mau=len(rows), theo_nam=bang, tong_dang_dung=t0, tong_mo_hinh=t1, de_xuat=de_xuat,
                dat_chuan=bool(hon and t_ok), t=round(float(np.mean(ics) / (np.std(ics) or 1.0) * np.sqrt(len(ics))), 2) if ics else None,
                thong_ke=tk_all, ket_luan=kl, thuoc_do='IC xếp hạng + chênh nhóm 20% cao/thấp (R41)')


# ---------------------------------------------------------------- sổ nhận định hằng ngày
def ghi_hom_nay(so: list[dict], B: Bang, syms, funda: dict, nganh: dict, ts: dict, tk: dict,
                may: dict | None = None) -> int:
    """Mỗi mã một dòng cho phiên mới nhất (không ghi trùng phiên). `may` = hướng 3 máy {ma: {bot,tin,daily}}.
    Chiều nhận định theo HẠNG điểm trong cả nhóm mã theo dõi hôm đó (R41); hang_pct = vị trí (100 = cao nhất)."""
    i = len(B.lich) - 1
    d = B.lich[i]
    da = {(r['ma'], r['ngay']) for r in so}
    moi = []
    for s in syms:
        if (s, d) in da:
            continue
        f = dac_trung(B, s, i, funda.get(s), nganh.get(s, ''))
        if not f:
            continue
        z = chuan_hoa(f, tk)
        sc = diem(z, ts)
        moi.append(dict(ma=s, ngay=d, diem=round(sc, 3), ly_do=ly_do(z, ts, f),
                        f={k: (None if v is None else round(v, 4)) for k, v in f.items()},
                        trong_so=ts.get('ten'), may=(may or {}).get(s), gia0=round(float(B.c[s][i]), 3)))
    ch = chieu_theo_hang([r['diem'] for r in moi])
    hg = _hang([r['diem'] for r in moi])
    for r, c, h in zip(moi, ch, hg):
        r['chieu'] = c
        r['hang_pct'] = round(float(h) / max(1, len(moi) - 1) * 100) if len(moi) > 1 else None
        r['so_ma_xep'] = len(moi)
    so.extend(moi)
    return len(moi)


def cham_so(so: list[dict], B: Bang) -> None:
    for r in so:
        i = B.pos.get(r['ngay'])
        if i is None:
            continue
        for n in KY:
            if f'kq_{n}' in r:
                continue
            ex = nhan(B, r['ma'], i, n)
            if ex is not None:
                r[f'vuot_{n}'] = ex
                r[f'kq_{n}'] = 'ĐÚNG' if dung_sai(r['chieu'], ex, n) else 'SAI'


def tong_ket_so(so: list[dict], chi_ma=None) -> dict:
    xs = [r for r in so if not chi_ma or r['ma'] in chi_ma]
    out = {}
    for n in KY:
        ch = [r for r in xs if f'kq_{n}' in r]
        d = sum(1 for r in ch if r[f'kq_{n}'] == 'ĐÚNG')
        out[n] = dict(da_cham=len(ch), dung=d, dung_pct=round(d / len(ch) * 100, 1) if len(ch) >= 10 else None,
                      cho=sum(1 for r in xs if f'kq_{n}' not in r))
    return out
