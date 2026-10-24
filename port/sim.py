# -*- coding: utf-8 -*-
"""Sổ giả lập của Lọc port — mua bán và NAV như sổ ghi tiến của nguyensonfinance (anh Sơn 22/10/2026).

Luật (anh Sơn chốt 15/10, 22/10, 24/10/2026):
  Vốn 1 tỷ. Phí mua 0,15%, phí bán 0,25% (đã gồm thuế). Tiền mặt không có lãi. So với VN-Index cùng kỳ.
  MUA  — mã nằm trong danh_muc.vi_tri có luận điểm `trong_port`, hoặc mã ở hàng chờ có kết luận CHỜ PHÉP THỬ.
         Tỷ trọng mục tiêu theo kết luận pitch (24/10/2026):
           · ĐỦ ĐỂ XUỐNG TIỀN, điểm 70/30 ≥ 70 → 12% NAV; 60–69 → 8% NAV
           · CHỜ PHÉP THỬ → chỉ đợt 1, tối đa 4% NAV (qua phép thử thì nâng lên mức ĐỦ, mua tiếp các đợt sau)
           · CẦN THÊM BẰNG CHỨNG / BÁC BỎ → 0 (nằm trong pool chờ)
         Chia đợt: bình thường 3 đợt 40/30/30; thị trường hoảng loạn (VN-Index ≤ −20% so với đỉnh 250 phiên) 2 đợt 60/40.
           · đợt sau: đi ngang 20 phiên kể từ đợt trước (biên đóng cửa ≤ 8%, đầu–cuối ≤ 4%, nửa sau không tạo đáy mới);
             quá 120 phiên không có nền → mua nốt.
           · giá chạy: đóng cửa ≥ giá đợt 1 + 10% trước đợt 2 → mua nửa phần còn lại ngay,
             nửa kia khi giá hồi về MA20 trong 60 phiên (quá hạn mua nốt).
         Trần: mỗi mã ≤ 15% NAV (tính cả phần giá tăng), mỗi ngành ≤ 30% NAV, tổng đã giải ngân ≤ 90% NAV
         (chừa 10% tiền mặt cho lúc hoảng loạn). Chạm trần thì đợt đó chỉ mua phần còn chỗ.
         Lệnh khớp ở giá đóng cửa của phiên ĐẦU TIÊN SAU ngày ra quyết định (không mua bằng giá đã biết lúc quyết).
  BÁN  — Đóng cửa < giá vốn bình quân −15%: bán hết.
         Luận điểm chuyển `loai`/`dong`, hoặc mã ra khỏi danh mục và hàng chờ: bán hết ở phiên kế tiếp.
         ĐÃ BỎ mục tiêu T1/T2 (24/10/2026) — port không số hoá điểm bán chốt lời.
  CỜ   — đóng cửa ≤ giá vốn −10%, hoặc thủng hỗ trợ của Daily: treo cờ "xem lại luận điểm", KHÔNG bán.

Sổ chỉ ghi tiếp, không sửa lịch sử: các phiên đã xử lý nằm trong port/state/so_gia_lap.json; lượt chạy sau
chỉ xử lý những phiên mới. Đổi luật thì phải xoá sổ và chạy lại từ đầu (ghi rõ trong `luat_hash`).
"""
from __future__ import annotations

import hashlib
import json
import re

VON = 1_000_000_000
PHI_MUA = 0.0015
PHI_BAN = 0.0025
LO = 100                       # lô chẵn
LUAT = dict(dot_thuong=[0.4, 0.3, 0.3], dot_hoang_loan=[0.6, 0.4], hoang_loan=-0.20, dinh_phien=250,
            nen_phien=20, nen_bien=0.08, nen_dau_cuoi=0.04, nen_qua_han=120, chay=0.10, chay_cho_ma20=60,
            cat=-0.15, co_lo=-0.10,
            ty_trong=dict(du_70=12.0, du_60=8.0, cho_phep_thu=4.0), tran_ma=0.15, tran_nganh=0.30, tran_tong=0.90)
DU = 'ĐỦ ĐỂ XUỐNG TIỀN'
CHO = 'CHỜ PHÉP THỬ'


def ket_luan(t: dict) -> tuple[str, float | None]:
    """(kết luận sau debate, điểm 70/30) của luận điểm."""
    pd = (t or {}).get('pitch_diem') or {}
    return str(pd.get('ket_luan') or '').strip().upper(), _num(pd.get('tong'))


def ty_trong_muc_tieu(t: dict) -> float:
    """% NAV mục tiêu theo kết luận pitch (anh Sơn duyệt 24/10/2026)."""
    kl, d = ket_luan(t)
    tt = LUAT['ty_trong']
    if kl.startswith(DU):
        return tt['du_70'] if (d or 0) >= 70 else tt['du_60'] if (d or 0) >= 60 else 0.0
    if kl.startswith(CHO):
        return tt['cho_phep_thu']
    return 0.0
LUAT_HASH = hashlib.sha1(json.dumps(LUAT, sort_keys=True).encode()).hexdigest()[:10]


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


# ---------------------------------------------------------------- giá
def chuoi_gia(D: dict, gia: dict) -> dict[str, dict[str, float]]:
    """Giá đóng cửa từng phiên: nến 240 phiên của trang web + ảnh chụp của port (ảnh chụp thắng khi trùng ngày)."""
    out: dict[str, dict[str, float]] = {}
    for sym, c in (D.get('candles') or {}).items():
        for b in (c or {}).get('bars') or []:
            if len(b) >= 5 and _num(b[4]):
                out.setdefault(sym, {})[b[0]] = float(b[4])
    for r in D.get('regime') or []:
        if r.get('date') and _num(r.get('vni')):
            out.setdefault('VNINDEX', {})[r['date']] = float(r['vni'])
    for sym, s in (gia or {}).items():
        for d, p in s.items():
            if _num(p):
                out.setdefault(sym, {})[d] = float(p)
    return out


def ma(series: list[float], n: int):
    return sum(series[-n:]) / n if len(series) >= n else None


# ---------------------------------------------------------------- mục tiêu do code đề xuất
_RE_VUNG = re.compile(r'([\d.]+)\s*[–-]\s*([\d.]+)')


def _vung(s: str):
    m = _RE_VUNG.search(s or '')
    return (float(m.group(1)), float(m.group(2))) if m else None


def daily_row(daily: dict | None, sym: str) -> dict | None:
    for arr in (((daily or {}).get('fc') or {}).get('ma_theo_nhom') or {}).values():
        for x in arr:
            if x.get('ma') == sym:
                return x
    return None


NGANH_PB = ('Ngân hàng', 'Dịch vụ tài chính', 'Bảo hiểm', 'Bất động sản')
T1_TOI_THIEU = 0.12            # port đi dài: T1 cách giá ít nhất +12% (bán 1/3 ở +2% là phá luận điểm)
T2_CACH_T1 = 0.12


def _so_dau(s: str):
    m = re.match(r'\s*([\d.]+)', s or '')
    return float(m.group(1)) if m else None


def de_xuat_muc_tieu(sym: str, D: dict, daily: dict | None, P: dict) -> dict:
    """Gom các mốc có nguồn: vùng kháng cự Daily, MA200, đỉnh 60/250 phiên, định giá về điểm giữa và về trung vị
    12 quý (P/E; P/B với ngân hàng, chứng khoán, bảo hiểm, BĐS).
    T1 = mốc gần nhất cách giá ≥ +12%; T2 = mốc gần nhất cách T1 ≥ +12%.
    Chỉ là ĐỀ XUẤT — Claude duyệt rồi mới ghi vào luận điểm (muc_tieu); sổ giả lập chỉ dùng số đã duyệt."""
    lk = (D.get('lookup') or {}).get(sym) or {}
    f = (D.get('funda') or {}).get(sym) or {}
    s = P.get(sym) or {}
    ngay = sorted(s)
    gia = s[ngay[-1]] if ngay else _num(lk.get('price'))
    out = dict(ma=sym, gia=gia, t1=None, t2=None, moc=[])
    if not gia:
        return out
    moc = []
    row = daily_row(daily, sym) or {}
    for x in row.get('khang_cu') or []:
        v = _vung(x)
        if v:
            moc.append((v[0], f'vùng kháng cự Daily {v[0]}–{v[1]}'))
    m200 = re.search(r'MA200=([\d.]+)', row.get('duong_ma') or '')
    if m200:
        moc.append((float(m200.group(1)), 'MA200'))
    for x, ten in zip(row.get('dinh_60_250p') or [], ('đỉnh 60 phiên', 'đỉnh 250 phiên')):
        v = _so_dau(x)
        if v:
            moc.append((v, ten))
    if not row and len(ngay) >= 60:
        moc.append((max(s[d] for d in ngay[-60:]), 'đỉnh 60 phiên'))
        moc.append((max(s[d] for d in ngay[-250:]), 'đỉnh 250 phiên (trong dữ liệu có)'))
    sector = lk.get('sector') or ''
    dung_pb = any(k.lower() in sector.lower() for k in NGANH_PB)

    def med(k, lo, hi):
        a = sorted(x for x in (f.get(k) or []) if _num(x) is not None and lo < x < hi)
        return a[len(a) // 2] if len(a) >= 6 else None

    def last(k):
        a = [x for x in (f.get(k) or []) if _num(x) is not None]
        return a[-1] if a else None
    pe, pe_tv, pb, pb_tv = last('pe'), med('pe', 0, 200), last('pb'), med('pb', 0, 50)
    if not dung_pb and pe and pe > 0 and pe_tv and pe_tv > pe:
        ten, hien, tv = 'P/E', pe, pe_tv
    elif pb and pb_tv and pb_tv > pb:
        ten, hien, tv = 'P/B', pb, pb_tv
    else:
        ten = None
    if ten:
        giua = round((hien + tv) / 2, 2)
        moc.append((gia * giua / hien, f'{ten} về {giua} (giữa hiện tại {hien} và trung vị 12 quý {tv})'))
        moc.append((gia * tv / hien, f'{ten} về trung vị 12 quý {tv} (hiện {hien})'))
    moc = sorted((round(g, 2), n) for g, n in moc if g and g > gia)
    out['moc'] = [dict(gia=g, nguon=n, cach_pct=round((g / gia - 1) * 100, 1)) for g, n in moc]
    t1 = next((m for m in out['moc'] if m['gia'] >= gia * (1 + T1_TOI_THIEU)), None)
    t2 = next((m for m in out['moc'] if t1 and m['gia'] >= t1['gia'] * (1 + T2_CACH_T1)), None)
    out['t1'], out['t2'] = t1, t2
    return out


def muc_tieu_duyet(t: dict) -> tuple[float | None, float | None]:
    m = {str(x.get('id', '')).upper(): _num(x.get('gia')) for x in t.get('muc_tieu') or []}
    return m.get('T1') or None, m.get('T2') or None


# ---------------------------------------------------------------- sổ
def so_moi() -> dict:
    return dict(luat=LUAT, luat_hash=LUAT_HASH, von=VON, tien=float(VON), da_xu_ly=None, vi_the={}, lenh=[],
                nav=[], co=[], ghi_chu='Sổ giả lập: không phải lệnh thật. Giá khớp = giá đóng cửa.')


def _nav(so: dict, P: dict, d: str) -> float:
    v = so['tien']
    for sym, p in so['vi_the'].items():
        px = _gia_luc(P, sym, d)
        v += p['cp'] * (px or 0) * 1000
    return v


def _gia_luc(P: dict, sym: str, d: str):
    s = P.get(sym) or {}
    if d in s:
        return s[d]
    truoc = [k for k in s if k <= d]
    return s[max(truoc)] if truoc else None


def _mua(so: dict, sym: str, d: str, px: float, tien_muon: float, ly_do: str, dot: str) -> bool:
    cp = int(min(tien_muon, so['tien']) / (px * 1000 * (1 + PHI_MUA)) // LO * LO)
    if cp <= 0:
        return False
    tien = cp * px * 1000
    phi = tien * PHI_MUA
    so['tien'] -= tien + phi
    p = so['vi_the'][sym]
    p['cp'] += cp
    p['von'] += tien + phi
    p['so_dot'] += 1
    p['dot_cuoi'] = dict(ngay=d, gia=px)
    p.setdefault('gia_dot1', px)
    so['lenh'].append(dict(ngay=d, ma=sym, loai='MUA', cp=cp, gia=px, tien=round(tien), phi=round(phi),
                           dot=dot, ly_do=ly_do))
    return True


def _ban(so: dict, sym: str, d: str, px: float, ti_le: float, ly_do: str) -> None:
    p = so['vi_the'][sym]
    cp = p['cp'] if ti_le >= 0.999 else int(p['cp'] * ti_le // LO * LO)
    if cp <= 0:
        return
    tien = cp * px * 1000
    phi = tien * PHI_BAN
    von = p['von'] * cp / p['cp']
    so['tien'] += tien - phi
    p['von'] -= von
    p['cp'] -= cp
    lai = tien - phi - von
    so['lenh'].append(dict(ngay=d, ma=sym, loai='BÁN', cp=cp, gia=px, tien=round(tien), phi=round(phi),
                           lai=round(lai), lai_pct=round(lai / von * 100, 2) if von else None, ly_do=ly_do))
    if p['cp'] <= 0:
        so.setdefault('da_dong', []).append(dict(ma=sym, mo=p['ngay_mo'], dong=d, ly_do=ly_do))
        del so['vi_the'][sym]


def _co(so: dict, sym: str, d: str, loai: str, noi_dung: str) -> None:
    if any(c['ma'] == sym and c['loai'] == loai and not c.get('xong') for c in so['co']):
        return
    so['co'].append(dict(ngay=d, ma=sym, loai=loai, noi_dung=noi_dung))


def _hoang_loan(P: dict, d: str) -> bool:
    v = P.get('VNINDEX') or {}
    ds = [k for k in sorted(v) if k <= d][-LUAT['dinh_phien']:]
    if not ds:
        return False
    return v[ds[-1]] / max(v[k] for k in ds) - 1 <= LUAT['hoang_loan']


def _nen(closes: list[float]) -> bool:
    """Đi ngang 20 phiên: biên đóng cửa ≤ 8%, đầu–cuối ≤ 4%, nửa sau không tạo đáy mới."""
    n = LUAT['nen_phien']
    if len(closes) < n:
        return False
    c = closes[-n:]
    lo, hi = min(c), max(c)
    h = n // 2
    return (hi / lo - 1 <= LUAT['nen_bien'] and abs(c[-1] / c[0] - 1) <= LUAT['nen_dau_cuoi']
            and min(c[h:]) >= min(c[:h]))


def _con_cho(so: dict, P: dict, d: str, sym: str, nav: float, nganh: dict[str, str]) -> float:
    """Số tiền còn được mua cho `sym` trước khi chạm trần mã 15% / ngành 30% / tổng 90% NAV."""
    gt = {s_: p['cp'] * (_gia_luc(P, s_, d) or 0) * 1000 for s_, p in so['vi_the'].items()}
    ng = nganh.get(sym) or ''
    cung_nganh = sum(v for s_, v in gt.items() if ng and nganh.get(s_) == ng)
    return max(0.0, min(nav * LUAT['tran_ma'] - gt.get(sym, 0.0),
                        nav * LUAT['tran_nganh'] - cung_nganh if ng else float('inf'),
                        nav * LUAT['tran_tong'] - sum(gt.values())))


def chay(so: dict, P: dict, ngay_phien: list[str], danh_muc: dict, luan: dict[str, dict],
         ho_tro: dict[str, float] | None = None, nganh: dict[str, str] | None = None) -> dict:
    """Xử lý các phiên mới (sau so['da_xu_ly']). `ngay_phien` = các phiên có giá VN-Index."""
    if so.get('luat_hash') != LUAT_HASH:
        so = so_moi()
    ho_tro = ho_tro or {}
    vi_tri = {str(v.get('ma', '')).upper(): v for v in (danh_muc or {}).get('vi_tri') or []}
    nganh = nganh or {}
    # mã được giải ngân: trong danh mục (luận điểm trong_port) + hàng chờ có kết luận CHỜ PHÉP THỬ
    duoc_mua = {s_: v for s_, v in vi_tri.items() if (luan.get(s_) or {}).get('trang_thai') == 'trong_port'}
    for h in (danh_muc or {}).get('hang_cho') or []:
        s_ = str(h.get('ma', '')).upper()
        t_ = luan.get(s_) or {}
        if s_ not in duoc_mua and t_.get('trang_thai') not in ('loai', 'dong') and ket_luan(t_)[0].startswith(CHO):
            duoc_mua[s_] = h
    ngay_qd = (danh_muc or {}).get('ngay') or ''
    moi = [d for d in ngay_phien if not so['da_xu_ly'] or d > so['da_xu_ly']]
    for d in moi:
        nav_dau = _nav(so, P, d)
        # 1) bán / cờ cho vị thế đang cầm
        for sym in list(so['vi_the']):
            p = so['vi_the'][sym]
            px = _gia_luc(P, sym, d)
            if not px:
                continue
            t = luan.get(sym) or {}
            if t.get('trang_thai') in ('loai', 'dong') or sym not in duoc_mua:
                _ban(so, sym, d, px, 1.0, 'luận điểm bị loại/đóng hoặc mã ra khỏi danh mục')
                continue
            gv = p['von'] / (p['cp'] * 1000) if p['cp'] else None
            if gv and px <= gv * (1 + LUAT['cat']):
                _ban(so, sym, d, px, 1.0, f'đóng cửa {px} thấp hơn giá vốn {gv:.2f} quá 15%')
                continue
            if gv and px <= gv * (1 + LUAT['co_lo']):
                _co(so, sym, d, 'lo_10', f'đóng cửa {px} thấp hơn giá vốn {gv:.2f} từ 10% — xem lại luận điểm')
            if ho_tro.get(sym) and px < ho_tro[sym]:
                _co(so, sym, d, 'thung_ho_tro', f'đóng cửa {px} thủng hỗ trợ Daily {ho_tro[sym]} — xem lại luận điểm')
        # 2) mua đợt 1 cho mã mới vào danh mục, đợt sau cho mã đang cầm
        for sym, v in duoc_mua.items():
            t = luan.get(sym) or {}
            px = _gia_luc(P, sym, d)
            if not px or (P.get(sym) or {}).get(d) is None:
                continue
            ngay_vao = max(str(t.get('ngay_vao') or ''), ngay_qd)
            if ngay_vao and d <= ngay_vao:          # khớp ở phiên SAU ngày quyết định (ngày vào / ngày chốt danh mục)
                continue
            tt = ty_trong_muc_tieu(t)
            cho = ket_luan(t)[0].startswith(CHO)
            if sym not in so['vi_the']:
                if tt <= 0 or any(x['ma'] == sym for x in so.get('da_dong') or []):
                    continue                        # đã đóng thì không tự mở lại; mở lại phải ghi luận điểm mới
                hl = _hoang_loan(P, d)
                dot = [1.0] if cho else (LUAT['dot_hoang_loan'] if hl else LUAT['dot_thuong'])
                so['vi_the'][sym] = dict(cp=0, von=0.0, so_dot=0, ngay_mo=d, muc_tieu_tien=nav_dau * tt / 100,
                                         ty_trong_muc_tieu=tt, ke_hoach=dot, hoang_loan=hl, da_mua_tien=0.0,
                                         cho_phep_thu=cho)
                p = so['vi_the'][sym]
                tien = min(p['muc_tieu_tien'] * dot[0], _con_cho(so, P, d, sym, nav_dau, nganh))
                ly = ('chờ phép thử: chỉ đợt 1, tối đa 4% NAV' if cho else
                      'đợt 1 trong 2 (thị trường hoảng loạn: 60/40)' if hl else 'đợt 1 trong 3 (40%)')
                if tien > 0 and _mua(so, sym, d, px, tien, ly, 'Đợt 1'):
                    p['da_mua_tien'] += tien
                else:
                    del so['vi_the'][sym]
                continue
            p = so['vi_the'][sym]
            if p.get('cho_phep_thu') and not cho and tt > p.get('ty_trong_muc_tieu', 0):
                # qua phép thử → nâng lên mức ĐỦ ĐỂ XUỐNG TIỀN, mua tiếp các đợt sau theo 40/30/30
                p.update(cho_phep_thu=False, ty_trong_muc_tieu=tt, muc_tieu_tien=nav_dau * tt / 100,
                         ke_hoach=LUAT['dot_thuong'])
            if p['so_dot'] >= len(p['ke_hoach']):
                continue
            con = p['muc_tieu_tien'] - p['da_mua_tien']
            if con <= 0:
                continue
            closes = [P[sym][k] for k in sorted(P[sym]) if k > p['dot_cuoi']['ngay'] and k <= d]
            all_c = [P[sym][k] for k in sorted(P[sym]) if k <= d]
            so_phien = len(closes)
            mot = p['muc_tieu_tien'] * p['ke_hoach'][min(p['so_dot'], len(p['ke_hoach']) - 1)]
            ly, tien = None, 0.0
            if p.get('cho_ma20'):
                m20 = ma(all_c, 20)
                if m20 and px <= m20:
                    ly, tien = 'giá hồi về MA20 sau nhịp chạy', con
                elif so_phien >= LUAT['chay_cho_ma20']:
                    ly, tien = 'quá 60 phiên chưa hồi về MA20 → mua nốt', con
            elif p['so_dot'] == 1 and px >= p['gia_dot1'] * (1 + LUAT['chay']):
                ly, tien = 'giá chạy +10% so với đợt 1 → mua nửa phần còn lại', con / 2
                p['cho_ma20'] = True
            elif _nen(closes):
                cuoi = p['so_dot'] >= len(p['ke_hoach']) - 1     # đợt cuối mua nốt phần còn lại
                ly, tien = 'đi ngang 20 phiên sau đợt trước', con if cuoi else min(mot, con)
            elif so_phien >= LUAT['nen_qua_han']:
                ly, tien = 'quá 120 phiên chưa có nền → mua nốt', con
            if ly:
                tran = _con_cho(so, P, d, sym, nav_dau, nganh)
                if tran < tien:
                    ly += ' (chạm trần mã/ngành/tổng — chỉ mua phần còn chỗ)'
                    tien = tran
            if ly and tien > 0 and _mua(so, sym, d, px, tien, ly, f"Đợt {p['so_dot'] + 1}"):
                p['da_mua_tien'] += tien
                if p.get('cho_ma20') and ly.startswith(('giá hồi', 'quá 60')):
                    p['cho_ma20'] = False
                    p['so_dot'] = len(p['ke_hoach'])
        nav = _nav(so, P, d)
        so['nav'].append(dict(ngay=d, nav=round(nav), tien=round(so['tien']),
                              vni=_gia_luc(P, 'VNINDEX', d)))
        so['da_xu_ly'] = d
    return so


def tong_ket(so: dict, P: dict) -> dict:
    nav = so.get('nav') or []
    if not nav:
        return dict(co_du_lieu=False)
    n0, n1 = nav[0], nav[-1]
    lai = n1['nav'] / VON - 1
    vni = (n1['vni'] / n0['vni'] - 1) if n0.get('vni') and n1.get('vni') else None
    dinh, dd = 0, 0.0
    for r in nav:
        dinh = max(dinh, r['nav'])
        dd = min(dd, r['nav'] / dinh - 1)
    ban = [l for l in so['lenh'] if l['loai'] == 'BÁN']
    vt = []
    for sym, p in so['vi_the'].items():
        px = _gia_luc(P, sym, n1['ngay'])
        gt = p['cp'] * px * 1000 if px else 0
        vt.append(dict(ma=sym, cp=p['cp'], gia_von=round(p['von'] / (p['cp'] * 1000), 2) if p['cp'] else None,
                       gia=px, gia_tri=round(gt), ty_trong=round(gt / n1['nav'] * 100, 1) if n1['nav'] else None,
                       lai_pct=round((gt / p['von'] - 1) * 100, 2) if p['von'] else None, so_dot=p['so_dot'],
                       ke_hoach=len(p['ke_hoach']), ngay_mo=p['ngay_mo'],
                       ty_trong_muc_tieu=p.get('ty_trong_muc_tieu'), cho_phep_thu=bool(p.get('cho_phep_thu'))))
    return dict(co_du_lieu=True, tu=n0['ngay'], den=n1['ngay'], nav=n1['nav'], lai_pct=round(lai * 100, 2),
                vni_pct=round(vni * 100, 2) if vni is not None else None,
                vuot_vni=round((lai - vni) * 100, 2) if vni is not None else None,
                sut_giam_lon_nhat=round(dd * 100, 2), tien_mat_pct=round(so['tien'] / n1['nav'] * 100, 1),
                so_lenh=len(so['lenh']), so_lenh_ban=len(ban),
                ban_lai=sum(1 for l in ban if (l.get('lai') or 0) > 0), vi_the=sorted(vt, key=lambda x: -x['gia_tri']),
                co_mo=[c for c in so['co'] if not c.get('xong')])
