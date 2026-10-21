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
  3. Code KHÔNG tự đổi trọng số. Anh Sơn xem bảng, đồng ý thì Claude ghi trọng số đề xuất vào port/trong_so.json.
Đặc trưng của 3 máy (bot/Tin/Daily) chưa có lịch sử nên chỉ ghi kèm từ nay; khi đủ mẫu mới đưa vào mô hình.
"""
from __future__ import annotations

import math
from datetime import date

import numpy as np

KY = (5, 20, 60)
BIEN = {5: 2.0, 20: 4.0, 60: 7.0}
NGUONG = 0.25          # điểm > +0,25 → tăng; < −0,25 → giảm; còn lại đi ngang
DAC_TRUNG = ('rs20', 'rs60', 'ma50', 'ma200', 'dinh250', 'bien_dong', 'ln_yoy', 'dt_yoy', 'dinh_gia', 'thi_truong')
TEN = dict(rs20='mạnh hơn VN-Index 20 phiên', rs60='mạnh hơn VN-Index 60 phiên', ma50='giá so với MA50',
           ma200='giá so với MA200', dinh250='cách đỉnh 250 phiên', bien_dong='biến động 20 phiên',
           ln_yoy='lợi nhuận quý gần nhất so cùng kỳ', dt_yoy='doanh thu quý gần nhất so cùng kỳ',
           dinh_gia='định giá so với trung vị 12 quý (âm = rẻ hơn)', thi_truong='VN-Index so với MA50')
# Bộ v1 viết tay (trên đặc trưng đã chuẩn hóa): đà giá + tăng trưởng thì cộng, đắt so với chính nó thì trừ.
TRONG_SO_V1 = dict(ten='v1 viết tay 22/10/2026', w=dict(rs20=0.15, rs60=0.35, ma50=0.25, ma200=0.15, dinh250=0.0,
                                                       bien_dong=-0.10, ln_yoy=0.25, dt_yoy=0.10, dinh_gia=-0.25,
                                                       thi_truong=0.10), b=0.0)
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
        ln_yoy=None, dt_yoy=None, dinh_gia=None)
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
                   thi_truong=(0.0, 0.04))


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


def _logit(X: np.ndarray, y: np.ndarray, l2: float = 1.0, vong: int = 400, buoc: float = 0.5) -> np.ndarray:
    n, m = X.shape
    w = np.zeros(m + 1)
    Xb = np.hstack([X, np.ones((n, 1))])
    for _ in range(vong):
        p = 1 / (1 + np.exp(-Xb @ w))
        g = Xb.T @ (p - y) / n
        g[:-1] += l2 * w[:-1] / n
        w -= buoc * g
    return w


def _mat(rows, tk):
    return np.array([[chuan_hoa(r['f'], tk)[k] for k in DAC_TRUNG] for r in rows], dtype=float)


def _cham_bo(rows, n, ts, tk):
    """Tỷ lệ đúng của một bộ trọng số trên các mẫu đã có nhãn ở kỳ hạn n, tính riêng phần nói tăng/giảm."""
    xs = [r for r in rows if r['y'].get(n) is not None]
    if not xs:
        return None
    ket = [(chieu(diem(chuan_hoa(r['f'], tk), ts)), r['y'][n]) for r in xs]
    co = [(c, e) for c, e in ket if c != 'ngang']
    dung = sum(1 for c, e in ket if dung_sai(c, e, n))
    d_co = sum(1 for c, e in co if dung_sai(c, e, n))
    alpha = [e if c == 'tang' else -e for c, e in co]
    return dict(mau=len(xs), dung_pct=round(dung / len(xs) * 100, 1), mau_co_chieu=len(co),
                dung_co_chieu_pct=round(d_co / len(co) * 100, 1) if co else None,
                alpha_tb=round(float(np.mean(alpha)), 2) if alpha else None)


def hoc(rows: list[dict], ts_dang_dung: dict, n_chinh: int = 20) -> dict:
    """Đi tiến theo năm: luyện trên các năm trước, chấm trên năm sau. So trọng số đang dùng với mô hình."""
    nam = sorted({r['ngay'][:4] for r in rows})
    tk_all = thong_ke(rows)
    bang = []
    for y in nam[2:]:
        tr = [r for r in rows if r['ngay'][:4] < y and r['y'].get(n_chinh) is not None]
        te = [r for r in rows if r['ngay'][:4] == y]
        if len(tr) < 500 or not te:
            continue
        tk = thong_ke(tr)
        X = _mat(tr, tk)
        yb = np.array([1.0 if r['y'][n_chinh] > 0 else 0.0 for r in tr])
        w = _logit(X, yb)
        ts_m = dict(w={k: float(w[j]) for j, k in enumerate(DAC_TRUNG)}, b=float(w[-1]))
        bang.append(dict(nam=y, mau_luyen=len(tr),
                         dang_dung={n: _cham_bo(te, n, ts_dang_dung, tk) for n in KY},
                         mo_hinh={n: _cham_bo(te, n, ts_m, tk) for n in KY}))
    # đề xuất = luyện trên toàn bộ mẫu đã có nhãn
    tr = [r for r in rows if r['y'].get(n_chinh) is not None]
    de_xuat = None
    if len(tr) >= 500:
        X = _mat(tr, tk_all)
        w = _logit(X, np.array([1.0 if r['y'][n_chinh] > 0 else 0.0 for r in tr]))
        de_xuat = dict(ten=f'mô hình luyện {date.today().isoformat()} trên {len(tr)} mẫu (kỳ hạn {n_chinh} phiên)',
                       w={k: round(float(w[j]), 4) for j, k in enumerate(DAC_TRUNG)}, b=round(float(w[-1]), 4))

    def tong(key):
        out = {}
        for n in KY:
            xs = [b[key][n] for b in bang if b[key].get(n)]
            m = sum(x['mau'] for x in xs)
            out[n] = dict(mau=m, dung_pct=round(sum(x['dung_pct'] * x['mau'] for x in xs) / m, 1) if m else None,
                          alpha_tb=round(float(np.mean([x['alpha_tb'] for x in xs if x['alpha_tb'] is not None])), 2)
                          if any(x['alpha_tb'] is not None for x in xs) else None)
        return out
    tk_ = tong('dang_dung'), tong('mo_hinh')
    tot_hon = bool(de_xuat) and all((tk_[1][n]['dung_pct'] or 0) > (tk_[0][n]['dung_pct'] or 0) for n in KY)
    return dict(so_mau=len(rows), theo_nam=bang, tong_dang_dung=tk_[0], tong_mo_hinh=tk_[1], de_xuat=de_xuat,
                thong_ke=tk_all, ket_luan=('Mô hình đúng hơn trọng số đang dùng ở cả 3 kỳ hạn trên các năm chưa thấy — '
                                           'đề xuất anh Sơn duyệt.' if tot_hon else
                                           'Mô hình chưa hơn trọng số đang dùng ở cả 3 kỳ hạn — giữ nguyên.'))


# ---------------------------------------------------------------- sổ nhận định hằng ngày
def ghi_hom_nay(so: list[dict], B: Bang, syms, funda: dict, nganh: dict, ts: dict, tk: dict,
                may: dict | None = None) -> int:
    """Mỗi mã một dòng cho phiên mới nhất (không ghi trùng phiên). `may` = hướng 3 máy {ma: {bot,tin,daily}}."""
    i = len(B.lich) - 1
    d = B.lich[i]
    da = {(r['ma'], r['ngay']) for r in so}
    moi = 0
    for s in syms:
        if (s, d) in da:
            continue
        f = dac_trung(B, s, i, funda.get(s), nganh.get(s, ''))
        if not f:
            continue
        z = chuan_hoa(f, tk)
        sc = diem(z, ts)
        so.append(dict(ma=s, ngay=d, diem=round(sc, 3), chieu=chieu(sc), ly_do=ly_do(z, ts, f),
                       f={k: (None if v is None else round(v, 4)) for k, v in f.items()},
                       trong_so=ts.get('ten'), may=(may or {}).get(s), gia0=round(float(B.c[s][i]), 3)))
        moi += 1
    return moi


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
