# -*- coding: utf-8 -*-
"""Kiểm thử 4 phần mới của Lọc port (22/10/2026): sổ giả lập, đọc BCTC sâu, nhận định hằng ngày, nhắc review."""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'port'))
import bctc as BC  # noqa: E402
import nhac as NH  # noqa: E402
import nhan_dinh as ND  # noqa: E402
import sim as SM  # noqa: E402


def _ngay(n, tu=date(2026, 10, 15)):
    out, d = [], tu
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _P(gia_x, vni=None):
    ds = _ngay(len(gia_x))
    return ds, {'X': dict(zip(ds, gia_x)), 'VNINDEX': dict(zip(ds, vni or [1000.0] * len(ds)))}


DM = {'ngay': '2026-10-15', 'vi_tri': [{'ma': 'X', 'ty_trong': 12}]}


def _luan(**k):
    t = {'ma': 'X', 'trang_thai': 'trong_port'}
    t.update(k)
    return {'X': t}


# ---------------------------------------------------------------- sổ giả lập
def test_mua_dot1_phien_sau_ngay_quyet_dinh_co_phi_lo_chan():
    ds, P = _P([10.0, 10.0, 10.1, 10.0])
    so = SM.chay(SM.so_moi(), P, ds, DM, _luan())
    mua = [l for l in so['lenh'] if l['loai'] == 'MUA']
    assert len(mua) == 1 and mua[0]['ngay'] == ds[1]          # 15/10 là ngày quyết định → khớp 16/10
    assert mua[0]['cp'] % 100 == 0 and mua[0]['cp'] * 10 * 1000 <= 1e9 * 0.12 / 3 + 1
    assert abs(mua[0]['phi'] - mua[0]['tien'] * SM.PHI_MUA) < 1
    assert so['nav'][0]['nav'] == 1_000_000_000                # trước khi mua


def test_cham_t1_ban_mot_phan_ba_va_khong_mua_them():
    ds, P = _P([10.0] * 3 + [10.5, 12.5] + [12.5] * 30)
    so = SM.chay(SM.so_moi(), P, ds, DM, _luan(muc_tieu=[{'id': 'T1', 'gia': 12.0}, {'id': 'T2', 'gia': 14.0}]))
    ban = [l for l in so['lenh'] if l['loai'] == 'BÁN']
    assert len(ban) == 1 and 'T1' in ban[0]['ly_do'] and ban[0]['ngay'] == ds[4]
    p = so['vi_the']['X']
    assert p['da_t1'] and p['so_dot'] == 1                      # sau T1 không có đợt 2 dù giá đi ngang 30 phiên
    assert abs(ban[0]['cp'] - (p['cp'] + ban[0]['cp']) / 3) <= 100


def test_cat_15_phan_tram_ban_het_va_co_10_phan_tram():
    ds, P = _P([10.0, 10.0, 8.9, 8.9, 8.4])
    so = SM.chay(SM.so_moi(), P, ds, DM, _luan())
    assert any(c['loai'] == 'lo_10' for c in so['co'])
    assert 'X' not in so['vi_the'] and so['lenh'][-1]['loai'] == 'BÁN' and '15%' in so['lenh'][-1]['ly_do']


def test_di_ngang_20_phien_mua_dot_2_va_chay_10_phan_tram():
    ds, P = _P([10.0, 10.0] + [10.05, 9.98] * 11)
    so = SM.chay(SM.so_moi(), P, ds, DM, _luan())
    assert [l['dot'] for l in so['lenh']] == ['Đợt 1', 'Đợt 2']
    ds, P = _P([10.0, 10.0, 10.5, 11.2] + [11.2] * 5)
    so = SM.chay(SM.so_moi(), P, ds, DM, _luan())
    assert so['lenh'][1]['ly_do'].startswith('giá chạy +10%')


def test_luan_diem_bi_loai_ban_het_va_so_chi_ghi_tiep():
    ds, P = _P([10.0, 10.0, 10.2, 10.3])
    so = SM.chay(SM.so_moi(), P, ds[:3], DM, _luan())
    n = len(so['lenh'])
    so = SM.chay(so, P, ds, DM, _luan(trang_thai='loai'))       # chỉ phiên mới được xử lý
    assert len(so['lenh']) == n + 1 and so['lenh'][-1]['loai'] == 'BÁN' and not so['vi_the']
    assert [r['ngay'] for r in so['nav']] == ds


def test_de_xuat_muc_tieu_cach_gia_toi_thieu():
    D = {'lookup': {'X': {'price': 10, 'sector': 'Công nghệ'}},
         'funda': {'X': {'pe': [20, 21, 19, 22, 20, 18, 10], 'pb': [2] * 7}}}
    daily = {'fc': {'ma_theo_nhom': {'a': [{'ma': 'X', 'khang_cu': ['10.2–10.5 ★', '11.6–12 ★'],
                                            'duong_ma': 'MA200=13.1(-20%)', 'dinh_60_250p': ['12.4·01/09·-5%', '19·01/02·-40%']}]}}}
    r = SM.de_xuat_muc_tieu('X', D, daily, {'X': {'2026-10-21': 10.0}})
    assert r['t1']['gia'] >= 11.2 and r['t1']['gia'] == 11.6          # 10,2 quá gần (+2%) nên bỏ
    assert r['t2']['gia'] >= r['t1']['gia'] * 1.12


# ---------------------------------------------------------------- đọc BCTC sâu
def _q(y, q, **v):
    base = {'yearReport': y, 'lengthReport': q, 'publicDate': f'{y}-0{min(q * 3, 9)}-20T00:00:00'}
    return {**base, **{k: x * 1e9 for k, x in v.items()}}


def test_bctc_doanh_nghiep_thuong_tach_mot_lan_va_du_phong():
    is_, cf = [], []
    for y in (2025, 2026):
        for q in (1, 2, 3, 4):
            if (y, q) > (2026, 2):
                continue
            mot = 300 if (y, q) == (2026, 2) else 0
            is_.append(_q(y, q, isa3=1000, isa5=300, isa9=-50, isa10=-50, isa6=10, isa7=-30, isa8=-20, isa102=0,
                          isa14=mot, isa16=180 + mot, isa20=150 + mot, isa22=150 + mot, isa21=0, isa18=0))
            cf.append(_q(y, q, cfa3=120 if (y, q) == (2026, 2) else 0, cfa4=0, cfa18=160))
    x = BC.phan_tich('X', {'is': is_, 'cf': cf})
    assert x['loai'] == 'thuong' and x['moi_nhat'] == 'Q2/26' and x['so_voi'] == 'Q2/25'
    assert x['lntt'] == 480 and x['lntt_bo_mot_lan'] == 180 and x['loi'] == 200
    cau = ' '.join(x['cau_chuyen'])
    assert 'Khoản một lần' in cau and 'trích lập dự phòng 120 tỷ' in cau
    k = x['quy'][-1]['khoan']
    assert abs(sum(i['gia_tri'] for i in k) - 480) < 0.5          # các khoản cộng lại đúng lãi trước thuế


def test_bctc_ngan_hang_du_phong():
    is_ = [_q(y, q, isb27=1000, isb30=100, isb31=0, isb32=0, isb33=0, isb36=0, isb37=0, isb39=-400,
              isb40=700, isb41=-(300 if (y, q) == (2026, 2) else 100), isa16=700 - (300 if (y, q) == (2026, 2) else 100),
              isa20=0, isa22=0)
           for y in (2025, 2026) for q in (1, 2, 3, 4) if (y, q) <= (2026, 2)]
    x = BC.phan_tich('B', {'is': is_, 'cf': []})
    assert x['loai'] == 'ngan_hang' and x['ty_le_du_phong'] == round(300 / 700 * 100, 1)
    assert any('trích lập dự phòng rủi ro tín dụng tăng 200 tỷ' in c for c in x['cau_chuyen'])


# ---------------------------------------------------------------- nhận định hằng ngày
def _bang(n=320, trend=0.002):
    ds = _ngay(n, date(2025, 1, 1))
    vni = [1000.0] * n
    a = [10 * (1 + trend) ** i for i in range(n)]
    return ND.Bang(ds, vni, {'UP': dict(zip(ds, a)), 'DN': dict(zip(ds, [10 * (1 - trend) ** i for i in range(n)]))})


def test_dac_trung_khong_nhin_truoc_bctc():
    B = _bang()
    rows = [dict(y=2025, q=4, avail=date(2026, 2, 1), npat=200, rev=1000, pe=10),
            dict(y=2024, q=4, avail=date(2025, 2, 1), npat=100, rev=900, pe=12)]
    i = B.pos[next(d for d in B.lich if d >= '2026-01-15')]
    f = ND.dac_trung(B, 'UP', i, rows)
    assert f['ln_yoy'] is None                                   # quý 4/2025 chưa công bố ở 15/01/2026
    i2 = B.pos[next(d for d in B.lich if d >= '2026-02-02')]
    assert ND.dac_trung(B, 'UP', i2, rows)['ln_yoy'] == 1.0


def test_ghi_va_cham_nhan_dinh():
    B = _bang()
    so = []
    full_lich = B.lich
    B.lich = full_lich[:-30]                                     # ghi ở phiên cách cuối 30 phiên
    ND.ghi_hom_nay(so, B, ['UP', 'DN'], {}, {}, ND.TRONG_SO_V1, {})
    B.lich = full_lich
    ND.cham_so(so, B)
    up = next(r for r in so if r['ma'] == 'UP')
    dn = next(r for r in so if r['ma'] == 'DN')
    assert up['chieu'] == 'tang' and dn['chieu'] == 'giam'
    assert up['kq_5'] == 'ĐÚNG' and up['kq_20'] == 'ĐÚNG' and 'kq_60' not in up
    assert dn['kq_20'] == 'ĐÚNG'
    t = ND.tong_ket_so(so)
    assert t[20]['da_cham'] == 2 and t[20]['dung_pct'] is None    # dưới 10 mẫu chưa ra tỷ lệ


def test_hoc_khong_tu_doi_trong_so():
    B = _bang(900)
    rows = ND.chay_lui(B, ['UP', 'DN'], {}, {}, buoc=2, tu='2025-01-01')
    h = ND.hoc(rows, ND.TRONG_SO_V1)
    assert h['so_mau'] == len(rows) and 'ket_luan' in h
    assert h['de_xuat'] is None or set(h['de_xuat']['w']) == set(ND.DAC_TRUNG)


# ---------------------------------------------------------------- nhắc review
def test_nhac_khi_co_quy_moi_va_ky_review():
    luan = {'A': {'trang_thai': 'trong_port'}, 'B': {'trang_thai': 'nghien_cuu'}, 'C': {'trang_thai': 'loai'}}
    D = {'funda': {'A': {'q': ['Q2/26']}, 'B': {'q': ['Q2/26']}, 'C': {'q': ['Q2/26']}}}
    st = NH.kiem(D, luan, {}, gui_that=False)
    assert st['lan_cuoi'] == [] and st['ky_review'] == 'Q2/26'   # lần đầu chỉ ghi mốc
    D['funda']['A']['q'].append('Q3/26')
    st = NH.kiem(D, luan, st, gui_that=False)
    assert [t['tieu_de'] for t in st['lan_cuoi']] == ['A có BCTC Q3/26']
    D['funda']['B']['q'].append('Q3/26')
    st = NH.kiem(D, luan, st, [{'ma': 'A', 'loai': 'lo_10', 'ngay': '2026-11-02', 'noi_dung': 'x'}], gui_that=False)
    tt = [t['tieu_de'] for t in st['lan_cuoi']]
    assert 'B có BCTC Q3/26' in tt and 'Đến kỳ review port Q3/26' in tt and 'Cờ review A' in tt
    st = NH.kiem(D, luan, st, [{'ma': 'A', 'loai': 'lo_10', 'ngay': '2026-11-02', 'noi_dung': 'x'}], gui_that=False)
    assert st['lan_cuoi'] == []                                  # không báo lặp


def test_r41_chieu_theo_hang_va_ic():
    d = list(range(20))
    ch = ND.chieu_theo_hang(d)
    assert ch.count('tang') == 6 and ch.count('giam') == 6 and ch[-1] == 'tang' and ch[0] == 'giam'
    assert ND.chieu_theo_hang([1.0, -1.0]) == ['tang', 'giam']          # ít mã → ngưỡng cũ
    # điểm = đúng đặc trưng quyết định nhãn → IC = 1, nhóm cao hơn nhóm thấp
    rows = []
    for k in range(12):
        for j in range(15):
            f = {x: 0.0 for x in ND.DAC_TRUNG}
            f['dinh_gia'] = j / 10
            rows.append(dict(ma=f'M{j}', ngay=f'2025-01-{k + 1:02d}', f=f, y={5: j - 7.0, 20: j - 7.0, 60: j - 7.0}))
    ts = dict(w={**{x: 0.0 for x in ND.DAC_TRUNG}, 'dinh_gia': 1.0}, b=0.0)
    r = ND._cham_bo(rows, 20, ts, ND.thong_ke(rows))
    assert r['ic'] > 0.99 and r['chenh'] > 0 and r['top_thang_pct'] == 100.0
    assert set(ND.TRONG_SO_V2['w']) == set(ND.DAC_TRUNG)
