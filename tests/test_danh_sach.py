# -*- coding: utf-8 -*-
"""Danh sách giải ngân của port (28/10/2026): khung luận điểm đủ sâu, 4 điều kiện, hai danh sách,
mã đang cầm trượt lọc thì giữ không mua thêm, trần 10 mã, sổ giả lập theo danh sách."""
import os
import sys
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'port'))
import danh_sach as DS  # noqa: E402
import sim as SM  # noqa: E402
from test_port_moi import _ngay  # noqa: E402

CHU = 'x' * 40


def _luan_day(ma, kl='ĐỦ ĐỂ XUỐNG TIỀN', tong=72, **k):
    t = dict(ma=ma, trang_thai='trong_port', quy_bctc='Q3/26',
             chuoi={c: CHU for c in DS.CHUOI}, bull=[CHU] * 3, bear=[CHU] * 3,
             pitch_diem=dict(khau={c: 10 for c in DS.KHAU}, so={c: 8 for c in DS.SO}, tong=tong, ket_luan=kl,
                             gia_sai={c: CHU for c in DS.GIA_SAI}),
             vo_hieu=CHU, kiem_chung=[dict(loai='funda')], dinh_gia=CHU, pitch=CHU)
    t.update(k)
    return t


def _B(gia: dict, n=260):
    lich = _ngay(n)
    return SimpleNamespace(lich=lich, c={s: np.asarray(v, float) for s, v in gia.items()})


def _gia_nen(dinh=20.0, day=14.0, n=260):
    # lên đỉnh ở phiên 100, rơi về 14 rồi đi ngang chặt 80 phiên cuối
    a = list(np.linspace(15, dinh, 100)) + list(np.linspace(dinh, day, 80)) + [day + 0.3 * ((k % 4) - 1.5) / 1.5 for k in range(n - 180)]
    return a


def _dong(ma, nen=0.06, tu_dinh=-0.30, nganh_td=-0.25, np4=20.0, cfo=500.0, dat=True, nganh='Thép', quy='Q3/26'):
    return dict(ma=ma, nganh=nganh, dat=dat, top110=True, f=dict(nen30=nen, tu_dinh=tu_dinh), nganh_tu_dinh=nganh_td,
                np4_yoy=np4, cfo_ty=cfo, tim=False, quy=quy, loai=[] if dat else ['nền rộng (biên độ 30 phiên 25%)'],
                diem=50, vi_sao=[])


# ---------------------------------------------------------------- khung luận điểm
def test_khung_day_du_va_thieu():
    assert DS.du_khung(_luan_day('A'), 'Q3/26') == []
    thieu = DS.du_khung({}, 'Q3/26')
    assert 'ít nhất 3 ý bull' in thieu and 'pitch cho khách' in thieu and 'chưa cập nhật BCTC Q3/26' in thieu
    assert 'chưa cập nhật BCTC Q3/26' in DS.du_khung(_luan_day('A', quy_bctc='Q2/26'), 'Q3/26')


def test_the_catalyst_bat_buoc_khi_chi_truoc():
    t = _luan_day('MWG', catalyst_can_chi_truoc=True)
    thieu = DS.du_khung(t, 'Q3/26')
    assert any(x.startswith('thẻ catalyst') for x in thieu) and len([x for x in thieu if 'thẻ catalyst' in x]) == 8
    t['the_catalyst'] = {k: CHU for k in DS.THE_CATALYST}
    t['the_catalyst']['moc_quy'] = [dict(quy='Q4/26', moc='mở 50 cửa hàng')]
    assert DS.du_khung(t, 'Q3/26') == []


# ---------------------------------------------------------------- 4 điều kiện
def test_bon_dieu_kien(monkeypatch):
    B = _B({'A': _gia_nen()})
    monkeypatch.setattr(DS, '_pe_tai', lambda rows, B_, s, d: ((20.0, 25.0) if d < B_.lich[-1] else (12.0, 30.0)))
    k = DS.bon_dieu_kien(_dong('A'), [], B)
    assert k['a']['dat'] and k['b']['dat'] and k['c']['dat'] and k['d']['dat'] and k['du']
    assert k['b']['peg_nay'] < k['b']['peg_dinh']
    # a: dòng tiền kinh doanh âm (không phải tài chính) → trượt; ngân hàng không xét dòng tiền
    assert DS.bon_dieu_kien(_dong('A', cfo=-50), [], B)['a']['dat'] is False
    assert DS.bon_dieu_kien(_dong('A', cfo=-50, nganh='Ngân hàng'), [], B)['a']['dat'] is True
    assert DS.bon_dieu_kien(_dong('A', cfo=None), [], B)['a']['dat'] is None
    # c: ngành không giảm, hoặc mã rơi riêng sâu hơn ngành > 15 điểm → vấn đề của chính công ty
    assert DS.bon_dieu_kien(_dong('A', nganh_td=-0.05), [], B)['c']['dat'] is False
    assert DS.bon_dieu_kien(_dong('A', tu_dinh=-0.45, nganh_td=-0.20), [], B)['c']['dat'] is False
    # b: PEG nay cao hơn lúc đỉnh → tăng trưởng chậm lại
    monkeypatch.setattr(DS, '_pe_tai', lambda rows, B_, s, d: ((10.0, 25.0) if d < B_.lich[-1] else (15.0, 10.0)))
    assert DS.bon_dieu_kien(_dong('A'), [], B)['b']['dat'] is False


def test_dieu_kien_d_day_moi():
    a = _gia_nen()
    a[-3] = 10.0                                   # thủng đáy 50 phiên trước
    k = DS.bon_dieu_kien(_dong('A'), None, _B({'A': a}))
    assert k['d']['dat'] is False and 'đáy mới' in k['d']['cau']


# ---------------------------------------------------------------- hai danh sách + trần 10 mã
def _lap(monkeypatch, bang, luan, dang_cam=()):
    syms = {r['ma'] for r in bang}
    B = _B({s: _gia_nen() for s in syms})
    monkeypatch.setattr(DS, '_pe_tai', lambda rows, B_, s, d: ((20.0, 25.0) if d < B_.lich[-1] else (12.0, 30.0)))
    return DS.lap(bang, luan, {s: [] for s in syms}, B, dang_cam=set(dang_cam))


def test_hai_danh_sach_va_giu_khong_mua(monkeypatch):
    bang = [_dong('A', nen=0.05), _dong('B', nen=0.04), _dong('C', nen=0.07, cfo=-10), _dong('F', dat=False, nen=0.25),
            _dong('U', nen=0.03)]
    luan = {'A': _luan_day('A'), 'B': _luan_day('B', vo_hieu=''), 'C': _luan_day('C'), 'F': _luan_day('F'),
            'T': _luan_day('T')}
    ds = _lap(monkeypatch, bang, luan, dang_cam={'F', 'C'})
    assert [x['ma'] for x in ds['giai_ngan']] == ['A']
    can = {x['ma']: x for x in ds['can_them']}
    assert set(can) == {'B', 'C'} and can['B']['duoc_mua'] and 'điều kiện vô hiệu' in can['B']['vi_sao']
    assert can['C']['duoc_mua'] is False and 'trượt a' in can['C']['vi_sao']      # trượt điều kiện đo được
    giu = {x['ma'] for x in ds['giu_khong_mua']}
    assert giu == {'F'}                                     # đang cầm mà trượt lọc → giữ, ngừng mua
    assert 'T' in {x['ma'] for x in ds['loai']}            # không có trong vũ trụ, không cầm
    assert [x['ma'] for x in ds['ung_vien']] == ['U']
    assert DS.ma_duoc_mua(ds) == {'A': 'du', 'B': 'cho'}
    # thứ tự theo độ chặt của nền
    assert ds['can_them'][0]['ma'] == 'B'


def test_tran_10_ma(monkeypatch):
    bang = [_dong(f'M{k:02d}', nen=0.02 + k / 1000) for k in range(13)]
    luan = {r['ma']: _luan_day(r['ma']) for r in bang}
    ds = _lap(monkeypatch, bang, luan, dang_cam={'M12'})
    duoc = [x['ma'] for x in ds['giai_ngan'] if x['duoc_mua']]
    assert len(duoc) == 10 and 'M12' in duoc                # mã đang cầm giữ chỗ trước
    assert duoc[:9] == [f'M{k:02d}' for k in range(9)]      # rồi tới nền chặt nhất
    assert all('đủ 10 mã' in x['vi_sao'] for x in ds['giai_ngan'] if not x['duoc_mua'])


# ---------------------------------------------------------------- sổ giả lập theo danh sách
def _P(syms, n=4):
    ds = _ngay(n)
    P = {s: dict(zip(ds, [10.0] * n)) for s in syms}
    P['VNINDEX'] = dict(zip(ds, [1000.0] * n))
    return ds, P


def test_sim_theo_danh_sach_cho_4_phan_tram_va_giu_ma_rot():
    ds, P = _P(['A', 'B', 'X'])
    luan = {s: _luan_day(s) for s in 'ABX'}
    dm = {'ngay': '2026-10-15', 'vi_tri': []}
    so = SM.chay(SM.so_moi(), P, ds[:2], dm, luan, duoc={'A': 'du', 'B': 'cho', 'X': 'du'})
    tien = {l['ma']: l['tien'] for l in so['lenh']}
    assert tien['A'] > 1e9 * 0.04 and tien['B'] <= 1e9 * 0.04
    # X rơi khỏi danh sách (trượt lọc) → giữ, không bán, không mua thêm
    so = SM.chay(so, P, ds, dm, luan, duoc={'A': 'du', 'B': 'cho'})
    assert 'X' in so['vi_the'] and not [l for l in so['lenh'] if l['loai'] == 'BÁN']
    assert len([l for l in so['lenh'] if l['ma'] == 'X']) == 1


def test_sim_ma_ha_xuong_cho_khong_mua_them():
    ds = _ngay(30)
    P = {'A': dict(zip(ds, [10.0, 10.0] + [10.05, 9.98] * 14)), 'VNINDEX': dict(zip(ds, [1000.0] * 30))}
    luan = {'A': _luan_day('A')}
    so = SM.chay(SM.so_moi(), P, ds, {'ngay': '2026-10-15', 'vi_tri': []}, luan, duoc={'A': 'cho'})
    assert len([l for l in so['lenh'] if l['ma'] == 'A']) == 1
    so2 = SM.chay(SM.so_moi(), P, ds[:2], {'ngay': '2026-10-15', 'vi_tri': []}, luan, duoc={'A': 'du'})
    so2 = SM.chay(so2, P, ds, {'ngay': '2026-10-15', 'vi_tri': []}, luan, duoc={'A': 'cho'})
    assert len([l for l in so2['lenh'] if l['ma'] == 'A']) == 1     # đang theo kế hoạch đủ, nay chỉ còn chờ → không thêm


def test_sim_tran_10_ma():
    syms = [f'M{k:02d}' for k in range(12)]
    ds, P = _P(syms)
    luan = {s: _luan_day(s, tong=65) for s in syms}       # 8% mỗi mã → 12 mã = 96% nếu không có trần
    nganh = {s: f'N{k}' for k, s in enumerate(syms)}
    so = SM.chay(SM.so_moi(), P, ds, {'ngay': '2026-10-15', 'vi_tri': []}, luan, nganh=nganh,
                 duoc={s: 'du' for s in syms})
    assert len(so['vi_the']) == SM.TOI_DA_MA


def test_luat_hash_khong_doi():
    # danh sách mới không được đổi luat_hash (đổi = sổ chạy lại quá khứ bằng danh sách hôm nay = nhìn trước)
    assert 'toi_da_ma' not in SM.LUAT and SM.TOI_DA_MA == 10


def test_dieu_kien_a_xet_loi_nhuan_cot_loi():
    # LN sau thuế 4 quý tăng nhờ khoản một lần, nhưng kinh doanh cốt lõi 4 quý giảm → không phải tăng trưởng thật
    B = _B({'A': _gia_nen()})
    giam = dict(quy=[dict(loi=100.0)] * 4 + [dict(loi=80.0)] * 4)
    tang = dict(quy=[dict(loi=80.0)] * 4 + [dict(loi=100.0)] * 4)
    assert DS.loi_4q(giam)['pct'] == -20.0 and DS.loi_4q(dict(quy=[dict(loi=1.0)] * 7)) is None
    assert DS.bon_dieu_kien(_dong('A'), None, B, giam)['a']['dat'] is False
    k = DS.bon_dieu_kien(_dong('A'), None, B, tang)['a']
    assert k['dat'] is True and 'cốt lõi 4 quý +25.0%' in k['cau']
    lo_sang_lai = dict(quy=[dict(loi=-10.0)] * 4 + [dict(loi=5.0)] * 4)
    assert DS.bon_dieu_kien(_dong('A'), None, B, lo_sang_lai)['a']['dat'] is True
