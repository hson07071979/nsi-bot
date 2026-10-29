# -*- coding: utf-8 -*-
"""LỌC QUÝ TỰ ĐỘNG cho Lọc port (anh Sơn 22/10/2026).

Nối thẳng vào BCTC mà trang nguyensonfinance cào mỗi tối (fetch_funda.py → data/funda_raw2.json, cache `bctc-`;
không có thì dùng 12 quý trên trang). Không cào thêm gì.

Mỗi lượt "Lọc port":
  1. Mã nào trong TOP110 (vũ trụ của bot) vừa có BCTC quý mới → chấm lại PHẦN SỐ của khung 70/30:
       định giá so với chính nó 20 (P/E, hoặc P/B với ngân hàng/CK/bảo hiểm/BĐS, so trung vị 12 quý)
     + lợi nhuận 4 quý so cùng kỳ 10 + ROE 10  = tối đa 40 điểm. Cùng thang với giai_ngan.diem_70_30.
     Mã bị cổng rủi ro của bot chặn (CFO âm, khó trả lãi vay, nợ xấu…) bị loại khỏi danh sách lọt lọc.
  2. Top 10 điểm cao nhất = "lọt lọc quý". Lọt lọc KHÔNG tự vào port: phần 70% định tính (lập luận, vì sao thị
     trường định giá sai) do Claude viết lúc anh Sơn review quý (anh Sơn chọn 22/10/2026).
  3. Sổ pitch bóng: mỗi mã TOP110 mỗi quý một dòng (ngày, giá, điểm) → chấm sau 20/60/120/250 phiên so VN-Index.
     Đây là mẫu cho vòng học (~440 dòng/năm thay vì ~44 dòng của riêng port).
  4. Chạy lùi từ 2019 cùng công thức trên giá điều chỉnh (port_gia.npz) và BCTC có ngày công bố (không nhìn trước):
     tương quan hạng (IC) giữa điểm và lợi suất hơn VN-Index theo từng đợt quý, top 10 so với cả rổ.
Vòng học chỉ đo; đổi thang điểm phải được anh Sơn duyệt.
"""
from __future__ import annotations

import bisect
import json
from datetime import date
from pathlib import Path

import numpy as np

import nhac as NH
import nhan_dinh as ND

TOP_K = 10
MOC = (20, 60, 120, 250)
MOC_LUI = (60, 120, 250)
NGANH_PB = ND.NGANH_PB
TU_LUI = '2019-07-01'
CO_TOI_THIEU = 15          # đợt quý có ít hơn số mã này thì không tính IC


# ---------------------------------------------------------------- tiện ích
def _num(x):
    return x if isinstance(x, (int, float)) and np.isfinite(x) else None


def nhan_quy(y: int, q: int) -> str:
    return f'Q{q}/{y % 100:02d}'


def _key(lbl: str | None):
    try:
        q, y = str(lbl)[1:].split('/')
        return int(y), int(q)
    except (ValueError, AttributeError):
        return (0, 0)


def _avail(r: dict) -> date:
    a = r.get('avail')
    if isinstance(a, date):
        return a
    try:
        return date.fromisoformat(str(a)[:10])
    except ValueError:
        return date.min


def _het_quy(r: dict) -> date:
    y, q = int(r.get('y') or 1), int(r.get('q') or 1)
    return date(y, 3 * q, 30 if q in (2, 3) else 31)


def rows_den(rows: list[dict] | None, d: date, live: bool = False) -> list[dict]:
    """Các quý ĐÃ CÔNG BỐ tới ngày d, xếp theo kỳ báo cáo.
    live=True — CHỈ cho ngày hôm nay, không dùng khi chạy lùi (anh Sơn 29/10/2026: công ty nào đã có số quý mới thì
    dùng luôn): lấy cả quý đã kết thúc mà đã có dòng trong dữ liệu Vietcap dù chưa tới mốc `avail` (sàn 45 ngày của bot
    chỉ để chống nhìn trước khi chạy lùi). Vietcap chỉ có dòng quý khi doanh nghiệp đã công bố."""
    return sorted((r for r in rows or [] if _avail(r) <= d or (live and _het_quy(r) < d)),
                  key=lambda r: (r.get('y', 0), r.get('q', 0)))


def _hang(v: np.ndarray) -> np.ndarray:
    """Hạng trung bình khi bằng nhau (cho tương quan Spearman, không cần scipy)."""
    o = np.argsort(v, kind='mergesort')
    r = np.empty(len(v))
    r[o] = np.arange(len(v), dtype=float)
    sv = v[o]
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and sv[j + 1] == sv[i]:
            j += 1
        if j > i:
            r[o[i:j + 1]] = (i + j) / 2
        i = j + 1
    return r


def spearman(a, b) -> float | None:
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    if len(a) < 5:
        return None
    ra, rb = _hang(a), _hang(b)
    if ra.std() == 0 or rb.std() == 0:
        return None
    return float(np.corrcoef(ra, rb)[0, 1])


# ---------------------------------------------------------------- điểm phần số
def diem_so(rows: list[dict], sector: str = '') -> dict | None:
    """rows = các quý đã công bố (rows_den). Trả về điểm phần số của 70/30 (tối đa 40) + từng thành phần."""
    if not rows:
        return None
    m = rows[-1]
    dung_pb = any(k.lower() in (sector or '').lower() for k in NGANH_PB)
    k = 'pb' if dung_pb else 'pe'
    lo, hi = (0, 50) if dung_pb else (0, 200)
    hist = sorted(r[k] for r in rows[-12:] if _num(r.get(k)) is not None and lo < r[k] < hi)
    hien = _num(m.get(k))
    rel = round(hien / hist[len(hist) // 2], 3) if len(hist) >= 6 and hien is not None and lo < hien < hi else None
    idx = {(r.get('y'), r.get('q')): r for r in rows}
    y, q = m.get('y'), m.get('q')
    ky = []
    for _ in range(8):
        ky.append((y, q))
        y, q = (y, q - 1) if q > 1 else (y - 1, 4)
    v = [_num((idx.get(t) or {}).get('npat')) for t in ky]
    np4 = None
    if all(x is not None for x in v):
        a1, a0 = sum(v[:4]), sum(v[4:])
        if a0 > 0:
            np4 = round((a1 / a0 - 1) * 100, 1)
    roe = _num(m.get('roe'))
    if roe is not None and abs(roe) <= 1.5:      # Vietcap ghi dạng tỷ lệ (0,26) — trang ghi % (26)
        roe = roe * 100
    roe = round(roe, 1) if roe is not None else None
    d_dg = 0 if rel is None else (20 if rel <= 0.6 else 14 if rel <= 0.8 else 7 if rel <= 1.0 else 0)
    d_ln = 0 if np4 is None else (10 if np4 >= 15 else 6 if np4 >= 0 else 0)
    d_roe = 0 if roe is None else (10 if roe >= 20 else 7 if roe >= 15 else 4 if roe >= 10 else 0)
    return dict(diem=d_dg + d_ln + d_roe, d_dinh_gia=d_dg, d_loi_nhuan=d_ln, d_roe=d_roe, dinh_gia_rel=rel,
                theo='P/B' if dung_pb else 'P/E', np4_yoy=np4, roe=roe, quy=nhan_quy(m['y'], m['q']),
                cong_bo=str(_avail(m)) if _avail(m) > date.min else None)


def xep_top(bang: list[dict], k: int = TOP_K) -> list[str]:
    ok = [r for r in bang if not r.get('chan') and r.get('dinh_gia_rel') is not None]
    ok.sort(key=lambda r: (-r['diem'], r['dinh_gia_rel'], r['ma']))
    return [r['ma'] for r in ok[:k]]


# ---------------------------------------------------------------- giá
def _i_tai(B, d: str) -> int | None:
    if not B.lich:
        return None
    i = bisect.bisect_right(B.lich, d) - 1
    return i if i >= 0 else None


def cham_so(so: list[dict], B) -> None:
    for r in so:
        i0 = _i_tai(B, r['ngay'])
        if i0 is None:
            continue
        for n in MOC:
            if r.get(f'kq{n}') is None:
                v = ND.nhan(B, r['ma'], i0, n)
                if v is not None:
                    r[f'kq{n}'] = v


def tong_ket_so(so: list[dict]) -> dict:
    out = {}
    for n in MOC:
        k = f'kq{n}'
        da = [r for r in so if r.get(k) is not None]
        top = [r[k] for r in da if r.get('top')]
        con = [r[k] for r in da if not r.get('top')]
        ics = []
        for q in sorted({r['quy'] for r in da}, key=_key):
            g = [r for r in da if r['quy'] == q]
            if len(g) >= CO_TOI_THIEU:
                ic = spearman([r['diem'] for r in g], [r[k] for r in g])
                if ic is not None:
                    ics.append(ic)
        out[f'{n}p'] = dict(da_cham=len(da), cho=sum(1 for r in so if r.get(k) is None),
                            top_tb=round(float(np.mean(top)), 2) if top else None,
                            con_lai_tb=round(float(np.mean(con)), 2) if con else None,
                            ic_tb=round(float(np.mean(ics)), 3) if ics else None, so_dot=len(ics))
    return out


# ---------------------------------------------------------------- chạy lùi
def chay_lui(B, rows_f: dict, nganh: dict, syms, tu: str = TU_LUI) -> dict:
    """Mỗi mã, mỗi quý: chấm điểm ở phiên đầu tiên sau ngày công bố, đo hơn VN-Index sau 60/120/250 phiên."""
    mau = []
    for s in syms:
        rows = rows_f.get(s)
        if not rows or s not in B.c:
            continue
        for r in sorted(rows, key=lambda r: (r.get('y', 0), r.get('q', 0))):
            a = _avail(r)
            if a == date.min or str(a) < tu:
                continue
            i = bisect.bisect_left(B.lich, str(a))
            if i >= len(B.lich):
                continue
            rd = rows_den(rows, date.fromisoformat(B.lich[i]))
            if not rd or (rd[-1].get('y'), rd[-1].get('q')) != (r.get('y'), r.get('q')):
                continue          # tới phiên đó đã có quý mới hơn
            d = diem_so(rd, nganh.get(s, ''))
            if not d or d['dinh_gia_rel'] is None:
                continue
            x = dict(ma=s, quy=d['quy'], diem=d['diem'], rel=d['dinh_gia_rel'], np4=d['np4_yoy'], roe=d['roe'])
            for n in MOC_LUI:
                x[f'kq{n}'] = ND.nhan(B, s, i, n)
            mau.append(x)
    ket = {}
    for n in MOC_LUI:
        k = f'kq{n}'
        dot = {}
        for x in mau:
            if x[k] is not None:
                dot.setdefault(x['quy'], []).append(x)
        ics = {c: [] for c in ('diem', 'dinh_gia', 'loi_nhuan', 'roe')}
        chenh, nam = [], {}
        for q, g in sorted(dot.items(), key=lambda kv: _key(kv[0])):
            if len(g) < CO_TOI_THIEU:
                continue
            y = [x[k] for x in g]
            for c, v in (('diem', [x['diem'] for x in g]), ('dinh_gia', [-x['rel'] for x in g]),
                         ('loi_nhuan', [x['np4'] if x['np4'] is not None else np.nan for x in g]),
                         ('roe', [x['roe'] if x['roe'] is not None else np.nan for x in g])):
                ic = spearman(v, y)
                if ic is not None:
                    ics[c].append(ic)
            g2 = sorted(g, key=lambda x: (-x['diem'], x['rel'], x['ma']))
            top = [x[k] for x in g2[:TOP_K]]
            c = float(np.mean(top)) - float(np.mean(y))
            chenh.append(c)
            nam.setdefault('20' + q[-2:], []).append(c)

        def tk(v):
            if not v:
                return None
            a = np.array(v)
            return dict(tb=round(float(a.mean()), 3), duong=round(float((a > 0).mean()), 2), so_dot=len(a),
                        t=round(float(a.mean() / a.std() * np.sqrt(len(a))), 2) if len(a) > 2 and a.std() > 0 else None)
        ket[f'{n}p'] = dict(ic={c: tk(v) for c, v in ics.items()}, top_hon_ca_ro=tk(chenh),
                            top_hon_ca_ro_theo_nam={y: round(float(np.mean(v)), 2) for y, v in sorted(nam.items())})
    return dict(so_mau=len(mau), so_ma=len({x['ma'] for x in mau}), tu=tu, ket=ket,
                ghi_chu='Vũ trụ = các mã đang thanh khoản trong port_gia.npz (~170 mã) → có thiên lệch sống sót. '
                        'Điểm chấm ở phiên đầu tiên sau ngày công bố BCTC; lợi suất là % hơn VN-Index.')


# ---------------------------------------------------------------- lượt chạy
def chay(D: dict, rows_f: dict, B, asof: str, state: Path, pg_co: bool, raw_co: bool,
         gui_chuong: bool = True, luan: dict | None = None) -> dict:
    lk = D.get('lookup') or {}
    nganh = {s: (x or {}).get('sector', '') for s, x in lk.items()}
    top110 = sorted(s for s, x in lk.items() if (x or {}).get('inuni'))
    hom_nay = date.fromisoformat(asof) if asof else date.today()
    st = _rj(state / 'loc_quy.json', {}) or {}
    so = _rj(state / 'so_loc_quy.json', []) or []
    khoi_tao = not st.get('quy')
    quy_cu = dict(st.get('quy') or {})
    i_nay = _i_tai(B, asof) if asof else None

    bang, su_kien = [], []
    for s in top110:
        x = lk.get(s) or {}
        d = diem_so(rows_den(rows_f.get(s), hom_nay, live=True), nganh.get(s, ''))
        if not d:
            bang.append(dict(ma=s, ten=x.get('name'), nganh=nganh.get(s), diem=None, quy=None, chan=x.get('block') or None,
                             ghi_chu='chưa có BCTC trên trang'))
            continue
        row = dict(ma=s, ten=x.get('name'), nganh=nganh.get(s), gia=_num(x.get('price')), chan=x.get('block') or None,
                   lai_bat_thuong=bool(x.get('tim')), lai_bat_thuong_vi=x.get('tim_vi'), **d)
        bang.append(row)
        if khoi_tao or _key(d['quy']) > _key(quy_cu.get(s)):
            su_kien.append(s)
        quy_cu[s] = d['quy'] if _key(d['quy']) >= _key(quy_cu.get(s)) else quy_cu[s]

    top = xep_top([r for r in bang if r.get('diem') is not None])
    mua = max((r['quy'] for r in bang if r.get('quy')), key=_key, default=None)
    co_so_moi = [r['ma'] for r in bang if r.get('quy') == mua]
    for r in bang:
        r['top'] = r['ma'] in top
        r['hang'] = top.index(r['ma']) + 1 if r['ma'] in top else None
    da_co = {(r['ma'], r['quy']) for r in so}
    by = {r['ma']: r for r in bang}
    for s in su_kien:
        r = by[s]
        if (s, r['quy']) in da_co:
            continue
        a = B.c.get(s)
        g0 = float(a[i_nay]) if a is not None and i_nay is not None and a[i_nay] > 0 else None
        so.append(dict(ma=s, quy=r['quy'], ngay=asof, gia0=g0, diem=r['diem'], rel=r['dinh_gia_rel'],
                       np4=r['np4_yoy'], roe=r['roe'], top=r['top'], chan=r['chan'],
                       su_kien='khởi tạo' if khoi_tao else 'BCTC mới'))
    cham_so(so, B)

    top_cu = list(st.get('top') or [])
    moi_lot = [s for s in top if s not in top_cu]
    roi = [s for s in top_cu if s not in top]
    da_gui = None
    if not khoi_tao and (moi_lot or roi):
        co_ld = set(luan or {})
        dong = [f"#{by[s]['hang']} {s} — {by[s]['diem']}/40 · {by[s]['theo']} bằng {by[s]['dinh_gia_rel']}× mức thường thấy"
                f" · LN 4 quý {by[s]['np4_yoy'] if by[s]['np4_yoy'] is not None else '—'}% · ROE {by[s]['roe'] if by[s]['roe'] is not None else '—'}%"
                + (' · đã có luận điểm' if s in co_ld else '') + (' · ⚠ lãi bất thường' if by[s].get('lai_bat_thuong') else '')
                for s in moi_lot]
        if roi:
            dong.append('Rời top: ' + ', '.join(roi))
        dong.append(f'{len(co_so_moi)}/{len(top110)} mã TOP110 đã có số {mua}. Mở /port → Lọc quý. '
                    'Mã lọt lọc chưa vào port — cần pitch + debate lúc review.')
        tieu_de = f"Lọc quý {mua}: {len(moi_lot)} mã mới lọt top {TOP_K}"
        if gui_chuong:
            NH.gui(tieu_de, '\n'.join(dong))
        da_gui = dict(tieu_de=tieu_de, noi_dung='\n'.join(dong))

    lui = chay_lui(B, rows_f, nganh, sorted(B.c)) if (pg_co and raw_co) else _rj(state / 'loc_quy_lui.json', None)
    if pg_co and raw_co and lui:
        _wj(state / 'loc_quy_lui.json', lui)
    st = dict(quy=quy_cu, top=top, mua=mua, khoi_tao=st.get('khoi_tao') or asof, lan_cuoi=da_gui)
    _wj(state / 'loc_quy.json', st)
    _wj(state / 'so_loc_quy.json', so)
    bang.sort(key=lambda r: (r.get('diem') is None, -(r.get('diem') or 0), r.get('dinh_gia_rel') or 9, r['ma']))
    return dict(mua=mua, co_so_moi=len(co_so_moi), tong=len(top110), top=top, bang=bang, su_kien_moi=su_kien,
                so_gan=so[-300:], so_tong=len(so), do_chinh_xac=tong_ket_so(so), lui=lui, lan_cuoi=da_gui,
                khoi_tao=st['khoi_tao'], top_k=TOP_K)


def _rj(p: Path, default):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def _wj(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
