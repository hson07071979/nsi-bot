# -*- coding: utf-8 -*-
"""VÒNG HỌC CỦA POOL TUẦN (anh Sơn chốt 24/10/2026: "cho vào vòng học" + "tự đổi, báo chuông").

Mỗi đầu tuần:
  1. CHẠY LÙI bộ lọc pool trên lịch sử: từ 2020, cứ 5 phiên một lần, mọi mã trong port_gia.npz.
     Đặc trưng giá/khối lượng tính đúng như pool.py; BCTC chỉ dùng các quý đã công bố tới ngày đó (không nhìn trước).
     Chỉ giữ mẫu QUA luật loại cứng (nền thấp) — vì điểm chỉ dùng để xếp hạng trong nhóm đó.
     Nhãn = mức hơn/kém VN-Index sau 60 phiên (kỳ hạn chính; 20 và 120 phiên để tham khảo).
  2. HỌC: mỗi phần điểm (giá thấp, nền hẹp, siết vol, biên độ co, ngành đáy, rẻ so với chính nó, LN sắp hồi, ROE)
     được đổi về 0–1 theo bậc gốc; hồi quy ridge nhắm HẠNG mức hơn VN-Index trong từng ngày → phần nào giúp xếp
     hạng đúng thì đáng nhiều điểm hơn. Hệ số âm → 0 điểm (máy thấy phần đó không giúp). Tổng chuẩn về 100.
     Phần nào thiếu dữ liệu lịch sử (ví dụ khối lượng khi port_gia.npz chưa có) thì GIỮ NGUYÊN điểm, không học.
  3. THI: đi tiến theo năm — luyện trên các năm trước (bỏ đoạn nhãn chồng sang năm thi), chấm trên năm sau.
     So thang đang dùng với thang học được trên những năm máy CHƯA THẤY. Qua bài thi (≥ 2/3 số năm, IC cao hơn
     và dương, t ≥ 2) thì `dat_chuan=True` → pool.py gọi tu_hoc.ap_dung (tự đổi + báo chuông).
Trừ điểm (CFO, nợ xấu, khả năng trả lãi…) và luật loại cứng KHÔNG học — không có lịch sử các cờ đó.
"""
from __future__ import annotations

import bisect
from datetime import date

import numpy as np

import loc_quy as LQ
import nhan_dinh as ND
import pool as PO

TU = '2020-01-01'
BUOC = 5                 # 5 phiên một mẫu (≈ mỗi tuần)
N_CHINH = 60
KY = (20, 60, 120)
TOP = PO.N_RIENG
MIN_MA_NGAY = 8          # ngày có ít mã qua lọc hơn thì bỏ (không xếp hạng được)
PHU_TOI_THIEU = 0.5      # phần điểm có dữ liệu < 50% mẫu luyện → giữ nguyên, không học
NGUON_PHAN = dict(thap='tu_dinh', nen='nen30', vol='vol_ratio', bien='bien_ratio', nganh='nganh',
                  dinh_gia='dinh_gia', ln_hoi='ln', roe='roe')
TEN = dict(thap='giá ở vùng thấp', nen='nền hẹp', vol='siết vol', bien='biên độ co lại', nganh='ngành ở đáy',
           dinh_gia='rẻ so với chính nó', ln_hoi='LN sắp hồi', roe='ROE')
K = tuple(PO.THANG)


def _yoy(idx: dict, m: dict, k: str):
    p = (idx.get((m.get('y', 0) - 1, m.get('q'))) or {}).get(k)
    v = m.get(k)
    try:
        v, p = float(v), float(p)
    except (TypeError, ValueError):
        return None
    if not (np.isfinite(v) and np.isfinite(p)) or p == 0:
        return None
    return (v - p) / abs(p) * 100


class _Funda:
    """BCTC theo ngày công bố, có nhớ tạm theo số quý đã công bố (diem_so tốn thời gian)."""

    def __init__(self, rows_f: dict, nganh: dict):
        self.r = {}
        for s, rows in (rows_f or {}).items():
            rr = sorted((r for r in rows or [] if LQ._avail(r) > date.min), key=LQ._avail)
            self.r[s] = (rr, [str(LQ._avail(r)) for r in rr])
        self.nganh = nganh
        self.nho = {}

    def tai(self, s: str, d: str):
        if s not in self.r:
            return None, None
        rr, av = self.r[s]
        k = bisect.bisect_right(av, d)
        if (s, k) not in self.nho:
            rows = sorted(rr[:k], key=lambda r: (r.get('y', 0), r.get('q', 0)))
            so = LQ.diem_so(rows, self.nganh.get(s, '')) if rows else None
            sc = None
            if rows:
                idx = {(r.get('y'), r.get('q')): r for r in rows}
                sc = dict(npat_yoy=_yoy(idx, rows[-1], 'npat'), rev_yoy=_yoy(idx, rows[-1], 'rev'))
            self.nho[(s, k)] = (so, sc)
        return self.nho[(s, k)]


def mau_lui(B, V: dict | None, rows_f: dict, nganh: dict, syms=None, tu: str = TU, buoc: int = BUOC) -> list[dict]:
    """Mẫu chạy lùi: dict(ngay, ma, x={phần: 0–1}, co={phần: có dữ liệu}, y={kỳ hạn: % hơn VNI})."""
    syms = [s for s in (syms or sorted(B.c)) if s in B.c]
    F = _Funda(rows_f, nganh)
    i0 = bisect.bisect_left(B.lich, tu)
    i0 = max(i0, 130)
    out = []
    for i in range(i0, len(B.lich), buoc):
        d = B.lich[i]
        hom = []
        for s in syms:
            a = B.c[s][:i + 1]
            ok = np.isfinite(a)
            if ok[-130:].sum() < 120 or not (a[-1] > 0):
                continue
            c = a[ok][-260:]
            v = None
            if V is not None and V.get(s) is not None:
                v = np.asarray(V[s][:i + 1], dtype=float)[ok][-260:]
            f = PO.dac_trung_gia(c, v)
            if f['tu_dinh'] is None or f['tu_dinh'] > PO.TU_DINH_TOI_DA or f['nen30'] is None \
                    or f['nen30'] > PO.NEN_TOI_DA:
                continue              # chỉ học trong nhóm qua luật loại cứng
            hom.append((s, f))
        if len(hom) < MIN_MA_NGAY:
            continue
        theo_nganh: dict[str, list] = {}
        for s, f in hom:
            if nganh.get(s):
                theo_nganh.setdefault(nganh[s], []).append(f['tu_dinh'])
        tv = {g: float(np.median(v)) for g, v in theo_nganh.items() if len(v) >= 3}
        for s, f in hom:
            so, sc = F.tai(s, d)
            nt = tv.get(nganh.get(s, ''))
            p = PO.phan_goc(f, nt, so, sc)
            co = dict(tu_dinh=True, nen30=True, vol_ratio=f.get('vol_ratio') is not None,
                      bien_ratio=f.get('bien_ratio') is not None, nganh=nt is not None,
                      dinh_gia=(so or {}).get('dinh_gia_rel') is not None,
                      ln=(sc or {}).get('npat_yoy') is not None, roe=(so or {}).get('roe') is not None)
            y = {n: ND.nhan(B, s, i, n) for n in KY}
            out.append(dict(ngay=d, ma=s, x={k: p[k] / PO.THANG[k] for k in K},
                            co={k: co[NGUON_PHAN[k]] for k in K}, y=y))
    return out


def _diem(m: dict, thang: dict) -> float:
    return sum(thang.get(k, 0) * m['x'][k] for k in K)


def _theo_ngay(mau, n):
    by = {}
    for m in mau:
        if m['y'].get(n) is not None:
            by.setdefault(m['ngay'], []).append(m)
    return {d: v for d, v in by.items() if len(v) >= MIN_MA_NGAY}


def cham(mau: list[dict], n: int, thang: dict) -> dict | None:
    """IC theo ngày (điểm vs mức hơn VN-Index sau n phiên) + nhóm top hơn cả nhóm qua lọc bao nhiêu."""
    by = _theo_ngay(mau, n)
    if not by:
        return None
    ics, chenh = [], []
    for xs in by.values():
        sc = [_diem(m, thang) for m in xs]
        y = [m['y'][n] for m in xs]
        ic = LQ.spearman(sc, y)
        if ic is not None:
            ics.append(ic)
        o = sorted(range(len(xs)), key=lambda j: -sc[j])[:min(TOP, max(3, len(xs) // 3))]
        chenh.append(float(np.mean([y[j] for j in o]) - np.mean(y)))
    return dict(ic=round(float(np.mean(ics)), 4) if ics else None, top_hon=round(float(np.mean(chenh)), 2),
                so_ngay=len(by), mau=sum(len(v) for v in by.values()))


def luyen(mau: list[dict], n: int, thang_dang_dung: dict, lam: float = 20.0) -> dict | None:
    """Ridge trên phần điểm 0–1 (trừ trung bình trong ngày) nhắm hạng mức hơn VN-Index trong ngày."""
    by = _theo_ngay(mau, n)
    if not by:
        return None
    tat = [m for v in by.values() for m in v]
    phu = {k: float(np.mean([m['co'][k] for m in tat])) for k in K}
    hoc_k = [k for k in K if phu[k] >= PHU_TOI_THIEU]
    giu = {k: thang_dang_dung.get(k, PO.THANG[k]) for k in K if k not in hoc_k}
    if not hoc_k:
        return None
    X, Y = [], []
    for xs in by.values():
        a = np.array([[m['x'][k] for k in hoc_k] for m in xs], dtype=float)
        X.append(a - a.mean(axis=0))
        h = ND._hang([m['y'][n] for m in xs])
        Y.append(h / (len(xs) - 1) - 0.5)
    X, Y = np.vstack(X), np.concatenate(Y)
    w = np.linalg.solve(X.T @ X + lam * np.eye(len(hoc_k)), X.T @ Y)
    w = np.clip(w, 0, None)
    if w.sum() <= 0:
        return None
    con = 100 - sum(giu.values())
    thang = {k: int(round(float(w[j] / w.sum() * con))) for j, k in enumerate(hoc_k)}
    thang.update({k: int(round(v)) for k, v in giu.items()})
    return dict(thang={k: thang[k] for k in K}, giu_nguyen=sorted(giu), phu={k: round(v, 2) for k, v in phu.items()},
                he_so={k: round(float(w[j]), 4) for j, k in enumerate(hoc_k)})


def ic_tung_phan(mau: list[dict], n: int = N_CHINH) -> dict:
    """IC của riêng từng phần (để anh Sơn đọc: phần nào thật sự giúp)."""
    by = _theo_ngay(mau, n)
    out = {}
    for k in K:
        ics = [LQ.spearman([m['x'][k] for m in xs], [m['y'][n] for m in xs]) for xs in by.values()
               if sum(m['co'][k] for m in xs) >= MIN_MA_NGAY]
        ics = [x for x in ics if x is not None]
        out[k] = dict(ic=round(float(np.mean(ics)), 4) if ics else None, so_ngay=len(ics))
    return out


def hoc(mau: list[dict], thang_dang_dung: dict, n_chinh: int = N_CHINH) -> dict:
    nam = sorted({m['ngay'][:4] for m in mau})
    bang = []
    for y in nam[2:]:
        moc = date(int(y), 1, 1)
        tr = [m for m in mau if m['ngay'][:4] < y and (moc - date.fromisoformat(m['ngay'])).days > n_chinh * 1.5]
        te = [m for m in mau if m['ngay'][:4] == y]
        md = luyen(tr, n_chinh, thang_dang_dung)
        a = cham(te, n_chinh, thang_dang_dung)
        b = cham(te, n_chinh, md['thang']) if md else None
        if a and b and a['ic'] is not None and b['ic'] is not None:
            bang.append(dict(nam=y, mau_luyen=len(tr), dang_dung=a, mo_hinh=b, thang_nam=md['thang']))
    de = luyen(mau, n_chinh, thang_dang_dung)
    so_nam = len(bang)
    nam_hon = sum(1 for b in bang if b['mo_hinh']['ic'] > b['dang_dung']['ic'])
    ic_moi = round(float(np.mean([b['mo_hinh']['ic'] for b in bang])), 4) if bang else None
    ic_cu = round(float(np.mean([b['dang_dung']['ic'] for b in bang])), 4) if bang else None
    ics = [b['mo_hinh']['ic'] for b in bang]
    t = round(float(np.mean(ics) / (np.std(ics) or 1.0) * np.sqrt(len(ics))), 2) if len(ics) >= 3 else None
    khac = bool(de) and any(de['thang'][k] != int(round(thang_dang_dung.get(k, 0))) for k in K)
    hon = bool(de) and khac and so_nam >= 3 and nam_hon * 3 >= so_nam * 2 and (ic_moi or 0) > (ic_cu or 0) \
        and (ic_moi or 0) > 0
    dat = hon and (t or 0) >= 2.0
    if not bang:
        kl = 'Chưa đủ lịch sử để thi (cần ít nhất 3 năm có nhãn 60 phiên) — giữ thang đang dùng.'
    elif dat:
        kl = (f'Thang học được tốt hơn thang đang dùng ở {nam_hon}/{so_nam} năm máy chưa thấy (IC 60 phiên '
              f'{ic_moi:+.3f} so với {ic_cu:+.3f}, t {t:.1f}) — qua bài thi, máy tự đổi thang.')
    elif hon:
        kl = (f'Thang học được nhỉnh hơn ở {nam_hon}/{so_nam} năm (IC {ic_moi:+.3f} so với {ic_cu:+.3f}) nhưng chưa '
              f'đủ chắc (t {t if t is not None else 0:.1f} < 2) — giữ thang đang dùng, tuần sau chấm lại.')
    else:
        kl = (f'Thang học được chưa hơn thang đang dùng trên những năm chưa thấy (IC {ic_moi if ic_moi is not None else 0:+.3f}'
              f' so với {ic_cu if ic_cu is not None else 0:+.3f}, hơn {nam_hon}/{so_nam} năm) — giữ thang đang dùng.')
    de_xuat = dict(ten=f'thang học {date.today().isoformat()} ({len(mau)} mẫu, 60 phiên)', **de) if de else None
    return dict(so_mau=len(mau), so_nam=so_nam, nam_hon=nam_hon, ic_moi=ic_moi, ic_cu=ic_cu, t=t, dat_chuan=dat,
                ket_luan=kl, theo_nam=bang, de_xuat=de_xuat, thang_dang_dung=thang_dang_dung,
                ky=({f'{n}p': dict(dang_dung=cham(mau, n, thang_dang_dung),
                                   de_xuat=cham(mau, n, de['thang']) if de else None) for n in KY}),
                ic_tung_phan=ic_tung_phan(mau, n_chinh), ten=TEN)


def chay(B, V: dict | None, rows_f: dict, nganh: dict, thang_dang_dung: dict, asof: str) -> dict:
    mau = mau_lui(B, V, rows_f, nganh)
    r = hoc(mau, thang_dang_dung)
    r.update(ngay=asof, co_khoi_luong=V is not None, tu=TU)
    print('vòng học pool:', r['ket_luan'], f"· {r['so_mau']} mẫu" + ('' if V is not None else ' · chưa có khối lượng lịch sử'))
    return r


def mo_ta_doi(cu: dict, moi: dict) -> str:
    return 'Thang mới: ' + ' · '.join(f"{TEN[k]} {int(round(cu.get(k, 0)))}→{moi[k]}" for k in K)
