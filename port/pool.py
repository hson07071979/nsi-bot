# -*- coding: utf-8 -*-
"""POOL CỦA LỌC PORT — chấm lại hằng tuần (anh Sơn chốt 24/10/2026).

Pool là ĐẦU VÀO để Claude pitch theo khung 70/30, KHÔNG phải danh mục và không giải ngân hết.
Bộ máy port (luận điểm 5 khâu, khâu 5, debate với máy, giải ngân 15/10, cắt −15%, review quý) giữ nguyên;
chỉ đổi cách lọc và pool:

  Pool = mã trong watchlist NSI qua bộ lọc mới  +  20–30 mã riêng của port (TOP110) điểm cao nhất.
  Không quan tâm dòng tiền: mã ít người để ý, volume co lại còn được ưu tiên (trước khi chạy thường có
  giai đoạn siết vol, siết nền).

  LOẠI (cứng) — "nền giá cao": giá cách đỉnh 250 phiên chưa tới −15%, hoặc biên độ 30 phiên > 20%.
  ĐIỂM (0–100) — kịch bản rebound:
      giá ở vùng thấp (cách đỉnh 250 phiên)      25
      nền hẹp (biên độ đóng cửa 30 phiên)         15
      siết vol (KL TB20 ÷ KL TB120)               15
      biên độ dao động co lại (độ lệch 20 ÷ 120)    5
      ngành ở đáy chu kỳ (trung vị ngành cách đỉnh) 10
      rẻ so với chính nó (P/E, P/B ÷ trung vị 12 quý) 15   ← rơi sâu / P/E thấp ĐƯỢC dùng làm lý do mua
      lợi nhuận sắp hồi (LN quý giảm, doanh thu giữ)  10   ← giả thuyết, Claude kiểm bằng phần đọc BCTC
      ROE                                          5
  TRỪ ĐIỂM (không còn chặn cứng): CFO 12 tháng âm −10 (trừ ngân hàng/chứng khoán/bảo hiểm) · khả năng trả lãi vay < 1,5 lần −8 · nợ xấu > 3% −8 ·
      nợ vay/vốn chủ > 4 lần −5 · lãi bất thường (lãi trước thuế tăng nhưng lõi giảm) −3 · chưa có BCTC −5.

Mỗi tuần (tuần ISO đầu tiên có lượt chạy) chốt pool mới, ghi sổ pool bóng (mọi mã TOP110 có điểm, một dòng/tuần)
để vòng học chấm sau 20/60/120/250 phiên so VN-Index.

VÒNG HỌC (24/10/2026, anh Sơn chốt "cho vào vòng học" + "tự đổi, báo chuông"): đầu mỗi tuần pool_hoc.py chạy lùi
bộ lọc trên giá điều chỉnh + khối lượng từ 2020 (BCTC chỉ dùng phần đã công bố tới từng ngày), học lại trọng số
8 phần điểm, đi tiến theo năm. Qua bài thi (tu_hoc.py) thì thang mới ghi ở state/thang_pool.json và dùng ngay.
Bậc thang của từng phần và luật loại cứng (nền cao) KHÔNG học — chỉ học mỗi phần đáng bao nhiêu điểm.
"""
from __future__ import annotations

import bisect
import json
from datetime import date
from pathlib import Path

import numpy as np

import loc_quy as LQ
import nhac as NH

N_RIENG = 25                 # 20–30 mã riêng của port
TU_DINH_TOI_DA = -0.15       # giá phải cách đỉnh 250 phiên ít nhất 15%
NEN_TOI_DA = 0.20            # biên độ đóng cửa 30 phiên tối đa 20%
NGANH_TAI_CHINH = ('Ngân hàng', 'Dịch vụ tài chính', 'Bảo hiểm')
THANG = dict(thap=25, nen=15, vol=15, bien=5, nganh=10, dinh_gia=15, ln_hoi=10, roe=5)   # thang gốc (viết tay 24/10)
TRU = dict(cfo=-10, icr=-8, npl=-8, de=-5, lai_bat_thuong=-3, thieu_bctc=-5)


# ---------------------------------------------------------------- tiện ích
def _num(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if np.isfinite(x) else None


def tuan_iso(d: str) -> str:
    y, w, _ = date.fromisoformat(d).isocalendar()
    return f'{y}-W{w:02d}'


def _bac(x, moc: list[tuple[float, float]], nguoc: bool = False) -> float:
    """Điểm theo bậc. moc = [(ngưỡng, điểm)] xếp từ tốt nhất. nguoc=False: x ≤ ngưỡng thì được điểm."""
    if x is None:
        return 0.0
    for nguong, d in moc:
        if (x >= nguong) if nguoc else (x <= nguong):
            return float(d)
    return 0.0


# ---------------------------------------------------------------- đặc trưng giá / volume
def dac_trung_gia(closes, vols=None) -> dict:
    """closes: giá điều chỉnh (cũ → mới, có thể có NaN). vols: khối lượng (cũ → mới) hoặc None."""
    c = np.asarray([x for x in (closes if closes is not None else []) if x is not None], dtype=float)
    c = c[np.isfinite(c) & (c > 0)]
    out = dict(tu_dinh=None, vi_tri_52w=None, nen30=None, vol_ratio=None, bien_ratio=None, so_phien=int(len(c)))
    if len(c) >= 120:
        w = c[-250:]
        out['tu_dinh'] = round(float(c[-1] / w.max() - 1), 4)
        rng = w.max() - w.min()
        out['vi_tri_52w'] = round(float((c[-1] - w.min()) / rng), 3) if rng > 0 else None
    if len(c) >= 30:
        n = c[-30:]
        out['nen30'] = round(float(n.max() / n.min() - 1), 4)
    if len(c) >= 121:
        r = np.diff(np.log(c[-121:]))
        s120, s20 = r.std(), r[-20:].std()
        out['bien_ratio'] = round(float(s20 / s120), 3) if s120 > 0 else None
    if vols is not None:
        v = np.asarray([x if x is not None else np.nan for x in vols], dtype=float)
        v = v[np.isfinite(v)]
        if len(v) >= 120 and np.mean(v[-120:]) > 0:
            out['vol_ratio'] = round(float(np.mean(v[-20:]) / np.mean(v[-120:])), 3)
    return out


def _gia_tu_nguon(sym: str, B, candles: dict, V: dict | None = None) -> tuple[list | None, list | None, str]:
    """Giá điều chỉnh từ port_gia.npz (B) nếu có; khối lượng từ port_gia.npz (V, cùng lịch với B) nếu có,
    không thì từ nến 240 phiên của trang web."""
    bars = ((candles or {}).get(sym) or {}).get('bars') or []
    vols = [b[5] for b in bars if len(b) >= 6] or None
    a = (B.c.get(sym) if B is not None else None)
    if a is not None and np.isfinite(a).sum() >= 120:
        v = (V or {}).get(sym)
        if v is not None:
            ok = np.isfinite(a)
            vols = list(np.asarray(v, dtype=float)[ok][-260:])
        return list(a[np.isfinite(a)][-260:]), vols, 'giá điều chỉnh'
    if bars:
        return [b[4] for b in bars if len(b) >= 5], vols, 'nến 240 phiên (giá thô)'
    return None, vols, 'thiếu giá'


# ---------------------------------------------------------------- điểm
def phan_goc(f: dict, nganh_tu_dinh: float | None, so: dict | None, sc: dict | None) -> dict:
    """Điểm từng phần theo thang gốc THANG (bậc viết tay). Vòng học chỉ đổi mỗi phần đáng bao nhiêu điểm."""
    sc, so = sc or {}, so or {}
    p = dict(
        thap=_bac(f.get('tu_dinh'), [(-0.50, 25), (-0.40, 20), (-0.30, 15), (-0.20, 10), (-0.15, 5)]),
        nen=_bac(f.get('nen30'), [(0.08, 15), (0.12, 11), (0.16, 7), (0.20, 3)]),
        vol=_bac(f.get('vol_ratio'), [(0.5, 15), (0.7, 10), (0.9, 5)]),
        bien=_bac(f.get('bien_ratio'), [(0.7, 5), (0.9, 2)]),
        nganh=_bac(nganh_tu_dinh, [(-0.30, 10), (-0.20, 6), (-0.10, 3)]),
        dinh_gia=_bac(so.get('dinh_gia_rel'), [(0.6, 15), (0.8, 10), (1.0, 5)]),
    )
    ny, ry = _num(sc.get('npat_yoy')), _num(sc.get('rev_yoy'))
    if ny is not None and ny < 0:
        p['ln_hoi'] = 10.0 if (ry is not None and ry >= 0) else 4.0
    elif ny is not None and so.get('np4_yoy') is not None and so['np4_yoy'] >= 0:
        p['ln_hoi'] = 5.0
    else:
        p['ln_hoi'] = 0.0
    p['roe'] = _bac(so.get('roe') if so.get('roe') is not None else _num(sc.get('roe')), [(15, 5), (10, 3)], nguoc=True)
    return p


def theo_thang(pg: dict, thang: dict | None) -> dict:
    """Đổi điểm từng phần từ thang gốc sang thang đang dùng (thang do vòng học đặt)."""
    if not thang:
        return dict(pg)
    return {k: round(v * (thang.get(k, THANG[k]) / THANG[k]), 2) for k, v in pg.items()}


def cham(f: dict, nganh_tu_dinh: float | None, so: dict | None, sc: dict | None, lk: dict | None,
         sector: str = '', thang: dict | None = None) -> dict:
    """f = dac_trung_gia; so = LQ.diem_so (định giá, LN 4 quý, ROE); sc = dòng screener; lk = dòng lookup.
    thang = số điểm tối đa mỗi phần (None = thang gốc)."""
    sc, lk, so = sc or {}, lk or {}, so or {}
    td = f.get('tu_dinh')
    p = theo_thang(phan_goc(f, nganh_tu_dinh, so, sc), thang)
    tru, ly_do_tru = {}, []
    tc = any(k.lower() in (sector or '').lower() for k in NGANH_TAI_CHINH)
    block = str(lk.get('block') or sc.get('block') or '')
    cfo = _num(lk.get('cfo_ty'))
    if not tc and ((cfo is not None and cfo < 0) or 'CFO' in block):   # ngân hàng/CK/bảo hiểm: CFO không mang nghĩa
        tru['cfo'] = TRU['cfo']
        ly_do_tru.append('dòng tiền kinh doanh 12 tháng âm' + (f' ({cfo:,.0f} tỷ)'.replace(',', '.') if cfo is not None else ''))
    icr = _num(sc.get('icr'))
    if not tc and (('ICR' in block) or (icr is not None and icr < 1.5)):
        tru['icr'] = TRU['icr']
        ly_do_tru.append(f'khả năng trả lãi vay thấp ({icr:.2f} lần)' if icr is not None else 'khả năng trả lãi vay thấp')
    if 'NPL' in block:
        tru['npl'] = TRU['npl']
        ly_do_tru.append('nợ xấu ' + block.replace('NPL', '').strip())
    de = _num(sc.get('de'))
    if not tc and (('D/E' in block) or (de is not None and de > 4)):
        tru['de'] = TRU['de']
        ly_do_tru.append(f'nợ vay/vốn chủ cao ({de:.1f} lần)' if de is not None else 'nợ vay/vốn chủ cao')
    if lk.get('tim') or sc.get('tim'):
        tru['lai_bat_thuong'] = TRU['lai_bat_thuong']
        ly_do_tru.append('lãi bất thường: ' + str(lk.get('tim_vi') or sc.get('tim_vi') or ''))
    if not so and 'Chưa có báo cáo' in block:
        tru['thieu_bctc'] = TRU['thieu_bctc']
        ly_do_tru.append('chưa có báo cáo tài chính')
    diem = round(sum(p.values()) + sum(tru.values()), 1)
    loai = []
    if td is None or td > TU_DINH_TOI_DA:
        loai.append('giá còn gần đỉnh' + (f' (cách đỉnh {td * 100:.0f}%)' if td is not None else ' (thiếu giá)'))
    if f.get('nen30') is None or f['nen30'] > NEN_TOI_DA:
        loai.append('nền rộng' + (f' (biên độ 30 phiên {f["nen30"] * 100:.0f}%)' if f.get('nen30') is not None else ''))
    return dict(diem=diem, phan=p, tru=tru, ly_do_tru=ly_do_tru, loai=loai, dat=not loai)


def _ly_do(r: dict) -> list[str]:
    """Câu ngắn, lời dễ hiểu, cho bảng pool."""
    out = []
    f = r.get('f') or {}
    if f.get('tu_dinh') is not None:
        out.append(f"cách đỉnh 1 năm {f['tu_dinh'] * 100:.0f}%")
    if f.get('nen30') is not None:
        out.append(f"30 phiên chỉ dao động {f['nen30'] * 100:.0f}%")
    if f.get('vol_ratio') is not None and f['vol_ratio'] <= 0.9:
        out.append(f"khối lượng co còn {f['vol_ratio'] * 100:.0f}% mức thường")
    if r.get('nganh_tu_dinh') is not None and r['nganh_tu_dinh'] <= -0.2:
        out.append(f"cả ngành cách đỉnh {r['nganh_tu_dinh'] * 100:.0f}%")
    if r.get('dinh_gia_rel') is not None and r['dinh_gia_rel'] <= 0.8:
        out.append(f"{r.get('theo') or 'P/E'} bằng {r['dinh_gia_rel']:.2f}× mức thường thấy")
    if (r.get('phan') or {}).get('ln_hoi', 0) >= 10:
        out.append('lợi nhuận quý giảm nhưng doanh thu giữ — có thể là khoản tạm, cần đọc BCTC')
    return out


# ---------------------------------------------------------------- bảng + pool
def dung_bang(D: dict, rows_f: dict, B, asof: str, them: set[str] | None = None, thang: dict | None = None,
              V: dict | None = None) -> list[dict]:
    lk_all = D.get('lookup') or {}
    sc_all = {r['sym']: r for r in (D.get('screener') or {}).get('rows') or [] if r.get('sym')}
    wl = {m['sym'] for m in (D.get('watchlist') or {}).get('members') or [] if m.get('sym')}
    candles = D.get('candles') or {}
    top110 = {s for s, x in lk_all.items() if (x or {}).get('inuni')}
    vu_tru = sorted(top110 | wl | set(them or ()))
    hom_nay = date.fromisoformat(asof) if asof else date.today()
    rows = []
    for s in vu_tru:
        lk = lk_all.get(s) or {}
        sector = lk.get('sector') or (sc_all.get(s) or {}).get('sector') or ''
        c, v, nguon = _gia_tu_nguon(s, B, candles, V)
        f = dac_trung_gia(c, v)
        so = LQ.diem_so(LQ.rows_den((rows_f or {}).get(s), hom_nay, live=True), sector) if rows_f else None
        rows.append(dict(ma=s, ten=lk.get('name'), nganh=sector, gia=_num(lk.get('price')), f=f, nguon_gia=nguon,
                         trong_wl=s in wl, top110=s in top110, so=so, sc=sc_all.get(s), lk=lk))
    # ngành ở đáy chu kỳ: trung vị "cách đỉnh" của các mã cùng ngành trong vũ trụ (≥ 3 mã)
    theo_nganh: dict[str, list[float]] = {}
    for r in rows:
        if r['f']['tu_dinh'] is not None and r['nganh']:
            theo_nganh.setdefault(r['nganh'], []).append(r['f']['tu_dinh'])
    tv = {k: float(np.median(v)) for k, v in theo_nganh.items() if len(v) >= 3}
    out = []
    for r in rows:
        nt = tv.get(r['nganh'])
        k = cham(r['f'], nt, r['so'], r['sc'], r['lk'], r['nganh'], thang=thang)
        so = r['so'] or {}
        row = dict(ma=r['ma'], ten=r['ten'], nganh=r['nganh'], gia=r['gia'], trong_wl=r['trong_wl'], top110=r['top110'],
                   f=r['f'], nguon_gia=r['nguon_gia'], nganh_tu_dinh=round(nt, 4) if nt is not None else None,
                   dinh_gia_rel=so.get('dinh_gia_rel'), theo=so.get('theo'), np4_yoy=so.get('np4_yoy'),
                   roe=so.get('roe'), quy=so.get('quy'),
                   npat_yoy=_num((r['sc'] or {}).get('npat_yoy')), rev_yoy=_num((r['sc'] or {}).get('rev_yoy')),
                   # 28/10/2026: cho 4 điều kiện của danh sách giải ngân (danh_sach.py)
                   cfo_ty=_num((r['lk'] or {}).get('cfo_ty')), tim=bool((r['lk'] or {}).get('tim')),
                   tim_vi=(r['lk'] or {}).get('tim_vi'), **k)
        row['vi_sao'] = _ly_do(row)
        out.append(row)
    return out


def chon_pool(bang: list[dict], n_rieng: int = N_RIENG) -> tuple[list[str], list[str]]:
    """(mã từ watchlist NSI qua lọc, mã riêng của port). Watchlist qua lọc vào hết; mã riêng lấy top n_rieng."""
    dat = [r for r in bang if r['dat']]
    tu_wl = sorted((r for r in dat if r['trong_wl']), key=lambda r: (-r['diem'], r['ma']))
    rieng = sorted((r for r in dat if not r['trong_wl'] and r['top110']), key=lambda r: (-r['diem'], r['ma']))
    return [r['ma'] for r in tu_wl], [r['ma'] for r in rieng[:n_rieng]]


def _i_tai(B, d: str):
    if B is None or not B.lich:
        return None
    i = bisect.bisect_right(B.lich, d) - 1
    return i if i >= 0 else None


# ---------------------------------------------------------------- lượt chạy
def chay(D: dict, rows_f: dict, B, asof: str, state: Path, luan: dict | None = None,
         gui_chuong: bool = True, V: dict | None = None) -> dict:
    """V = khối lượng {mã: mảng cùng lịch với B} từ port_gia.npz (None = dùng nến 240 phiên của trang)."""
    import pool_hoc as PH
    import tu_hoc as TH
    luan = luan or {}
    st = _rj(state / 'pool.json', {}) or {}
    so = _rj(state / 'so_pool.json', []) or []
    tuan = tuan_iso(asof) if asof else None
    tuan_moi = bool(tuan) and st.get('tuan') != tuan
    # ---- vòng học: đầu tuần (hoặc chưa có kết quả) chạy lùi + học lại thang, qua bài thi thì tự đổi
    tu = TH.doc(state, 'thang_pool')
    thang = dict((tu or {}).get('thang') or THANG)
    hoc = _rj(state / 'pool_hoc.json', None)
    if B is not None and rows_f and (tuan_moi or not hoc):
        try:
            hoc = PH.chay(B, V, rows_f, {s: (x or {}).get('sector', '') for s, x in (D.get('lookup') or {}).items()},
                          thang, asof)
        except Exception as e:  # noqa: BLE001 — vòng học hỏng không được làm hỏng pool
            print('pool_hoc lỗi:', type(e).__name__, e)
            hoc = dict(loi=f'{type(e).__name__}: {e}', ngay=asof)
        if hoc.get('dat_chuan') and hoc.get('de_xuat'):
            d = TH.ap_dung(state, 'thang_pool', dict(ten=hoc['de_xuat']['ten'], thang=hoc['de_xuat']['thang']),
                           dict(ten=(tu or {}).get('ten') or 'thang gốc 24/10/2026', thang=thang), asof,
                           'Pool port: máy tự đổi thang điểm', hoc['ket_luan'] + '\n' + PH.mo_ta_doi(thang, hoc['de_xuat']['thang']),
                           bang_chung=dict(ic_moi=hoc.get('ic_moi'), ic_cu=hoc.get('ic_cu'), t=hoc.get('t'),
                                           nam_hon=hoc.get('nam_hon'), so_nam=hoc.get('so_nam')),
                           gui_chuong=gui_chuong)
            if d:
                thang = dict(hoc['de_xuat']['thang'])
                hoc['da_doi'] = asof
            else:
                hoc['cho_doi_ngay'] = TH.con_cho(state, 'thang_pool', asof)
        _wj(state / 'pool_hoc.json', hoc)
    bang = dung_bang(D, rows_f, B, asof, them=set(luan), thang=thang, V=V)
    by = {r['ma']: r for r in bang}
    da_gui = None
    if tuan_moi:
        tu_wl, rieng = chon_pool(bang)
        cu = set(st.get('tu_wl') or []) | set(st.get('rieng') or [])
        moi = tu_wl + rieng
        vao = [s for s in moi if s not in cu]
        roi = sorted(cu - set(moi))
        i0 = _i_tai(B, asof)
        da_co = {(r['ma'], r['quy']) for r in so}
        for r in bang:                 # sổ pool bóng: mọi mã TOP110 có điểm, mỗi tuần một dòng
            if not r['top110'] or (r['ma'], tuan) in da_co:
                continue
            a = B.c.get(r['ma']) if B is not None else None
            g0 = float(a[i0]) if a is not None and i0 is not None and a[i0] > 0 else None
            so.append(dict(ma=r['ma'], quy=tuan, ngay=asof, gia0=g0, diem=r['diem'], dat=r['dat'],
                           top=r['ma'] in moi, trong_wl=r['trong_wl']))
        if st.get('tuan') and (vao or roi):
            dong = [f"+ {s} — {by[s]['diem']:.0f} điểm · " + '; '.join(by[s]['vi_sao'][:3]) for s in vao]
            if roi:
                dong.append('Rời pool: ' + ', '.join(roi))
            dong.append(f'Pool tuần {tuan}: {len(tu_wl)} mã từ watchlist NSI + {len(rieng)} mã riêng. '
                        'Mở /port → Pool tuần. Mã trong pool chưa phải danh mục — cần pitch 70/30 + debate.')
            tieu_de = f'Pool port tuần {tuan}: {len(vao)} mã vào, {len(roi)} mã ra'
            if gui_chuong:
                NH.gui(tieu_de, '\n'.join(dong))
            da_gui = dict(tieu_de=tieu_de, noi_dung='\n'.join(dong))
        st = dict(tuan=tuan, ngay=asof, tu_wl=tu_wl, rieng=rieng, lan_cuoi=da_gui or st.get('lan_cuoi'),
                  khoi_tao=st.get('khoi_tao') or asof)
    if B is not None:
        LQ.cham_so(so, B)
    _wj(state / 'pool.json', st)
    _wj(state / 'so_pool.json', so)
    pool = set(st.get('tu_wl') or []) | set(st.get('rieng') or [])
    for r in bang:
        r['trong_pool'] = r['ma'] in pool
    # mã đã có luận điểm (đang cầm / hàng chờ) chạy lại qua bộ lọc mới
    soat = []
    for s, t in sorted(luan.items()):
        r = by.get(s)
        if not r:
            soat.append(dict(ma=s, trang_thai=t.get('trang_thai'), ket_luan=((t.get('pitch_diem') or {}).get('ket_luan')),
                             co_du_lieu=False))
            continue
        soat.append(dict(ma=s, trang_thai=t.get('trang_thai'), ket_luan=(t.get('pitch_diem') or {}).get('ket_luan'),
                         co_du_lieu=True, trong_pool=r['ma'] in pool, dat=r['dat'], diem=r['diem'], loai=r['loai'],
                         vi_sao=r['vi_sao'], ly_do_tru=r['ly_do_tru'], f=r['f'], trong_wl=r['trong_wl']))
    bang.sort(key=lambda r: (not r.get('trong_pool'), not r['dat'], -r['diem'], r['ma']))
    return dict(tuan=st.get('tuan'), ngay_chot=st.get('ngay'), tu_wl=st.get('tu_wl') or [], rieng=st.get('rieng') or [],
                bang=bang, soat_luan_diem=soat, so_gan=so[-300:], so_tong=len(so), do_chinh_xac=LQ.tong_ket_so(so),
                lan_cuoi=st.get('lan_cuoi'), khoi_tao=st.get('khoi_tao'), n_rieng=N_RIENG,
                luat=dict(tu_dinh_toi_da=TU_DINH_TOI_DA, nen_toi_da=NEN_TOI_DA, thang=thang, thang_goc=THANG, tru=TRU),
                hoc=hoc, lich_su_thang=TH.lich_su(state, 'thang_pool'))


def _rj(p: Path, default):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def _wj(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
