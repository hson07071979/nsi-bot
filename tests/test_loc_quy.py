# -*- coding: utf-8 -*-
"""Lọc quý TOP110 (port/loc_quy.py, 22/10/2026). Run: PORT_KHONG_CHUONG=1 python -m pytest -q tests/test_loc_quy.py"""
import os
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'port'))
import loc_quy as LQ          # noqa: E402
import nhan_dinh as ND        # noqa: E402


def quy(y, q, npat, pe, roe=0.22, pb=2.0, avail=None):
    return dict(y=y, q=q, npat=npat, pe=pe, pb=pb, roe=roe, avail=avail or date(y, 3 * q, 1) + timedelta(days=75))


def lich_su(pe_cuoi, np_cuoi=130.0, n=12):
    out, y, q = [], 2023, 3
    for k in range(n):
        out.append(quy(y, q, 100.0, 15.0))
        y, q = (y, q + 1) if q < 4 else (y + 1, 1)
    out[-1] = quy(out[-1]['y'], out[-1]['q'], np_cuoi, pe_cuoi)
    for r in out[-4:-1]:
        r['npat'] = 130.0
    return out


def test_diem_so_thang_70_30():
    d = LQ.diem_so(lich_su(pe_cuoi=8.0), 'Công nghệ')       # P/E 8 so trung vị 15 = 0,53 → 20 điểm
    assert d['theo'] == 'P/E' and d['dinh_gia_rel'] == round(8 / 15, 3)
    assert (d['d_dinh_gia'], d['d_loi_nhuan'], d['d_roe']) == (20, 10, 10) and d['diem'] == 40
    assert d['np4_yoy'] == 30.0 and d['roe'] == 22.0          # ROE Vietcap 0,22 → 22%
    d2 = LQ.diem_so(lich_su(pe_cuoi=16.5), 'Công nghệ')      # 1,1× → 0 điểm định giá
    assert d2['d_dinh_gia'] == 0
    d3 = LQ.diem_so(lich_su(pe_cuoi=8.0), 'Ngân hàng')        # ngân hàng dùng P/B
    assert d3['theo'] == 'P/B'


def test_khong_nhin_truoc():
    rows = lich_su(pe_cuoi=8.0)
    last = rows[-1]['avail']
    assert LQ.rows_den(rows, last - timedelta(days=1))[-1] is rows[-2]
    assert LQ.rows_den(rows, last)[-1] is rows[-1]


def test_spearman():
    assert abs(LQ.spearman([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]) - 1) < 1e-9
    assert abs(LQ.spearman([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) + 1) < 1e-9
    assert LQ.spearman([1, 1, 1, 1, 1], [1, 2, 3, 4, 5]) is None


def _bang(syms, n=400):
    lich = [(date(2026, 1, 1) + timedelta(days=k)).isoformat() for k in range(n)]
    gia = {s: {d: 10.0 * (1 + 0.001 * k * (j + 1)) for k, d in enumerate(lich)} for j, s in enumerate(syms)}
    return ND.Bang(lich, [100.0] * n, gia)


def test_luot_chay_khoi_tao_roi_bao_ma_moi_lot(tmp_path):
    syms = [f'M{k:02d}' for k in range(12)]
    lk = {s: dict(inuni=True, sector='Công nghệ', name=s, price=10.0) for s in syms}
    lk['M00']['block'] = 'CFO < 0'
    rows = {s: lich_su(pe_cuoi=6 + k) for k, s in enumerate(syms)}
    for s in syms:
        for r in rows[s]:
            r['avail'] = date(2025, 1, 1)                     # đều đã công bố trước asof
    B = _bang(syms)
    D = dict(lookup=lk)
    o1 = LQ.chay(D, rows, B, '2026-03-01', tmp_path, pg_co=False, raw_co=False, gui_chuong=False)
    assert o1['so_tong'] == 12 and o1['lan_cuoi'] is None                 # khởi tạo: ghi sổ, không chuông
    assert 'M00' not in o1['top'] and len(o1['top']) == LQ.TOP_K           # mã bị chặn không vào top
    # quý mới của M11 (đang ngoài top vì đắt) → rẻ hẳn → lọt top, có tin
    r = rows['M11']
    r.append(quy(2026, 3, 140.0, 4.0, avail=date(2026, 2, 1)))
    o2 = LQ.chay(D, rows, B, '2026-03-02', tmp_path, pg_co=False, raw_co=False, gui_chuong=False)
    assert o2['su_kien_moi'] == ['M11'] and o2['so_tong'] == 13
    assert 'M11' in o2['top'] and o2['lan_cuoi'] and 'M11' in o2['lan_cuoi']['noi_dung']
    # chạy lại cùng ngày: không ghi trùng, không báo lại
    o3 = LQ.chay(D, rows, B, '2026-03-02', tmp_path, pg_co=False, raw_co=False, gui_chuong=False)
    assert o3['so_tong'] == 13 and o3['lan_cuoi'] is None


def test_cham_so_pitch_bong():
    B = _bang(['A'])
    so = [dict(ma='A', quy='Q1/26', ngay=B.lich[10], diem=30, top=True)]
    LQ.cham_so(so, B)
    assert so[0]['kq20'] is not None and so[0]['kq20'] > 0                 # A tăng, VN-Index đứng yên
    assert so[0].get('kq250') is not None
    tk = LQ.tong_ket_so(so)
    assert tk['20p']['da_cham'] == 1 and tk['20p']['top_tb'] == so[0]['kq20']
