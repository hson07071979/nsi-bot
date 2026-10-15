# -*- coding: utf-8 -*-
"""Kiểm thử vòng học Lọc port: chấm mốc giá/cơ bản, sổ bất đồng, quan điểm từng máy, cờ chưa trả lời máy."""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'port'))
import build as B  # noqa: E402


def _gia(sym_prices, vni):
    g = {'VNINDEX': dict(vni)}
    g.update({s: dict(p) for s, p in sym_prices.items()})
    return g


DAYS = ['2026-10-%02d' % d for d in range(1, 11)]


def test_moc_gia_giu_va_thung():
    g = _gia({'X': zip(DAYS, [10, 10.2, 9.8, 10.5, 10.6, 10.7, 10.8, 10.9, 11, 11.1])}, zip(DAYS, [1000] * 10))
    # giữ 10: phiên 3 (9.8) thủng → SAI
    r = B.cham_moc_gia({'loai': 'giu', 'moc': 10, 'han_phien': 5}, '2026-10-01', g, 'X')
    assert r['ket_qua'] == 'SAI' and r['ngay_dong'] == '2026-10-03' and r['phien'] == 2
    # vượt 10.65 trong 5 phiên: phiên 6 (10.7) là phiên thứ 5 sau ngày ghi → ĐÚNG
    r = B.cham_moc_gia({'loai': 'vuot', 'moc': 10.65, 'han_phien': 5}, '2026-10-01', g, 'X')
    assert r['ket_qua'] == 'ĐÚNG' and r['ngay_dong'] == '2026-10-06'
    # không vượt 12 trong 3 phiên → hết hạn ĐÚNG
    r = B.cham_moc_gia({'loai': 'duoi', 'moc': 12, 'han_phien': 3}, '2026-10-01', g, 'X')
    assert r['ket_qua'] == 'ĐÚNG' and r['phien'] == 3
    # chưa đủ phiên → còn mở
    r = B.cham_moc_gia({'loai': 'thung', 'moc': 5, 'han_phien': 60}, '2026-10-01', g, 'X')
    assert r['trang_thai'] == 'mo' and r['phien'] == 9


def test_moc_co_ban():
    fu = {'q': ['Q1/26', 'Q2/26'], 'ny': [5.0, 13.7]}
    assert B.cham_moc_cb({'quy': 'Q2/26', 'chi_tieu': 'ny', 'so_sanh': '>=', 'nguong': 15}, fu)['ket_qua'] == 'SAI'
    assert B.cham_moc_cb({'quy': 'Q2/26', 'chi_tieu': 'ny', 'so_sanh': '<=', 'nguong': 15}, fu)['ket_qua'] == 'ĐÚNG'
    assert B.cham_moc_cb({'quy': 'Q3/26', 'chi_tieu': 'ny', 'nguong': 15}, fu)['trang_thai'] == 'mo'


def test_so_bat_dong_cham_ai_dung():
    days = ['2026-%02d-%02d' % (m, d) for m in (10, 11, 12) for d in range(1, 29)][:70]
    g = _gia({'X': [(d, 10 + i * 0.1) for i, d in enumerate(days)]}, [(d, 1000) for d in days])
    so = [dict(ma='X', may='bot', ngay=days[0], chieu_port=1, chieu_may=-1),
          dict(ma='X', may='tin', ngay=days[0], chieu_port=-1, chieu_may=1)]
    B.cham_bat_dong(so, g)
    assert so[0]['vuot_20p'] == 20.0 and so[0]['port_dung_20p'] is True and so[0]['port_dung_60p'] is True
    assert so[1]['port_dung_20p'] is False
    tk = B.tong_ket_bat_dong(so)
    assert tk['bot']['20p']['port_dung'] == 1 and tk['tin']['20p']['may_dung'] == 1
    assert tk['bot']['20p']['ty_le_port_dung'] is None      # mẫu < 10 thì không ra tỷ lệ


def test_may_bot_cong_rui_ro_va_tin_hieu():
    D = {'asof': '2026-10-13', 'lookup': {
        'A': {'state': 'chan', 'block': 'CFO < 0', 'label': 'CỔNG RỦI RO CHẶN'},
        'B': {'state': 'chan', 'block': 'Chưa có báo cáo tài chính', 'label': 'CỔNG RỦI RO CHẶN'},
        'C': {'state': 'khongdat', 'label': 'CHƯA ĐỦ ĐIỀU KIỆN'}},
        'signals': [{'sym': 'C', 'date': '2026-10-08', 'light': 'DO'}]}
    assert B.may_bot('A', D)['chieu'] == -1
    assert B.may_bot('B', D)['chieu'] == 0       # thiếu BCTC là thiếu dữ liệu, không phải quan điểm xấu
    assert B.may_bot('C', D)['chieu'] == 1
    assert B.may_bot('Z', D)['chieu'] == 0


def test_may_tin_zalo_danh_dau_noi_bo():
    reps = [{'ngay': '2026-10-13', 'web': {'topics': [
        {'tieu_de': 't1', 'quan_trong': 5, 'nganh_ma': [{'ten': 'X', 'chieu': '-'}], 'phe': {'lac_quan': {'nhan_dinh': 'tot'}}}]},
        'zalo': {'topics': [{'tieu_de': 'z', 'quan_trong': 5, 'nganh_ma': [{'ten': 'X', 'chieu': '-'}]}]}}]
    r = B.may_tin('X', None, reps)
    assert r['chieu'] == -1
    assert [x['noi_bo'] for x in r['bang_chung']] == [False, True]


def test_may_daily_so_du_bao_uu_tien_cau_truc():
    so = [{'doi_tuong': 'X', 'trang_thai': 'mo', 'loai': 'giu', 'moc': 10, 'han_phien': 5}]
    daily = {'fc': {'ma_theo_nhom': {'n': [{'ma': 'X', 'duong_ma': 'MA50=11(-5.0%) MA200=12(-9.0%)'}]}}}
    assert B.may_daily('X', daily, so)['chieu'] == 1
    assert B.may_daily('X', daily, [])['chieu'] == -1


def test_build_offline(tmp_path, monkeypatch):
    """Dựng gói từ DATA giả: cờ máy ngược chiều + chưa trả lời, mở sổ bất đồng, bảng lọc có đủ mã."""
    data = {'asof': '2026-10-13', 'regime': [{'date': '2026-10-13', 'vni': 1700, 'light': 'DO'}],
            'lookup': {'X': {'price': 10, 'state': 'chan', 'block': 'ICR 1.1 < 1.5', 'sector': 'Thép', 'name': 'X corp'}},
            'funda': {'X': {'q': ['Q1/26', 'Q2/26'], 'ny': [10, 20], 'np': [1, 2], 'pe': [8, 9], 'pb': [1, 1]}},
            'signals': [], 'marks': {}}
    html = tmp_path / 'index.html'
    html.write_text('<script id="DATA" type="application/json">' + json.dumps(data) + '</script>', encoding='utf-8')
    tin = tmp_path / 'tin'
    (tin / 'out' / 'daily').mkdir(parents=True)
    root = tmp_path / 'port'
    (root / 'luan_diem').mkdir(parents=True)
    (root / 'luan_diem' / 'X.json').write_text(json.dumps({'ma': 'X', 'trang_thai': 'nghien_cuu', 'chieu': 'tang'}),
                                               encoding='utf-8')
    monkeypatch.setenv('SITE_HTML', str(html))
    monkeypatch.setenv('TIN_DIR', str(tin))
    monkeypatch.setattr(B, 'ROOT', root)
    monkeypatch.setattr(B, 'LUAN', root / 'luan_diem')
    monkeypatch.setattr(B, 'STATE', root / 'state')
    monkeypatch.setattr(B, 'OUT', root / 'out')
    b = B.build(datetime(2026, 10, 14, 18, 0, tzinfo=B.VN))
    x = b['luan_diem'][0]
    assert x['ho_so']['nguoc'] == ['bot'] and x['ho_so']['chua_tra_loi'] == ['bot']
    assert 'thiếu luận điểm bull' in x['thieu']
    assert b['so_bat_dong'][0]['gia0'] == 10 and b['so_bat_dong'][0]['vni0'] == 1700
    assert [r['sym'] for r in b['loc']] == ['X'] and b['loc'][0]['ny_lien'] == 2
    # chạy lại cùng ngày: không mở thêm dòng sổ bất đồng
    b2 = B.build(datetime(2026, 10, 14, 19, 0, tzinfo=B.VN))
    assert len(b2['so_bat_dong']) == 1
    # trả lời máy → hết cờ
    (root / 'luan_diem' / 'X.json').write_text(json.dumps(
        {'ma': 'X', 'trang_thai': 'nghien_cuu', 'chieu': 'tang', 'phan_bien_may': {'bot': {'noi_dung': 'ICR thấp do...'}}}),
        encoding='utf-8')
    b3 = B.build(datetime(2026, 10, 14, 20, 0, tzinfo=B.VN))
    assert b3['luan_diem'][0]['ho_so']['chua_tra_loi'] == []
    assert json.loads((root / 'state' / 'gia.json').read_text())['X'] == {'2026-10-13': 10}


# ---------------------------------------------------------------- vòng học 2: mục tiêu, timing, sổ dự đoán, hiệu quả
import hoc as H  # noqa: E402


def test_muc_tieu_dat_vo_hieu_het_han_va_timing():
    g = _gia({'X': zip(DAYS, [10, 10.4, 10.8, 11.2, 11.0, 10.9, 10.8, 10.7, 10.6, 10.5])}, zip(DAYS, [1000] * 10))
    t = {'ma': 'X', 'vo_hieu_gia': 9.5, 'muc_tieu': [
        {'id': 'T1', 'gia': 11.2, 'du_kien_phien': 5, 'han_phien': 8},
        {'id': 'T2', 'gia': 12.0, 'du_kien_phien': 6, 'han_phien': 6}]}
    a, b = H.cham_muc_tieu(t, g, '2026-10-01')
    assert a['ket_qua'] == 'ĐẠT' and a['phien'] == 3 and a['lech_timing'] == -2      # đến sớm 2 phiên
    assert b['ket_qua'] == 'HẾT HẠN' and b['phien'] == 6 and b['con_cach_pct'] > 0
    t2 = {'ma': 'X', 'vo_hieu_gia': 10.45, 'muc_tieu': [{'id': 'T1', 'gia': 20, 'du_kien_phien': 5, 'han_phien': 50}]}
    g2 = _gia({'X': zip(DAYS, [10.5, 10.6, 10.4, 11, 11, 11, 11, 11, 11, 11])}, zip(DAYS, [1000] * 10))
    assert H.cham_muc_tieu(t2, g2, '2026-10-01')[0]['ket_qua'] == 'VÔ HIỆU'
    t2['vo_hieu_gia'] = 9.0
    assert H.cham_muc_tieu(t2, g, '2026-10-01')[0]['trang_thai'] == 'mo'


def test_rr_va_san_sang():
    t = {'ma': 'X', 'vo_hieu_gia': 9.4, 'muc_tieu': [{'id': 'T1', 'gia': 11, 'nguon': 'MA200', 'du_kien_phien': 40, 'han_phien': 80},
                                                     {'id': 'T2', 'gia': 13, 'nguon': 'đỉnh cũ', 'du_kien_phien': 90, 'han_phien': 160}],
         'luan_diem': [{'id': 'L1', 'nhan': 'INTERPRETATION', 'bang_chung': ['FACT: P/E 7']}],
         'bull': ['a', 'b', 'c'], 'bear': ['x', 'y', 'z'],
         'debate': [{'ben': b} for b in ('bull', 'bear', 'trong_tai', 'claude', 'trong_tai')],
         'kiem_chung': [{'loai': 'giu'}, {'loai': 'funda'}]}
    assert [x['rr'] for x in H.rr(t, 10)] == [1.67, 5.0]
    s = H.san_sang(t, {'chua_tra_loi': [], 'nguoc': []}, [], 10)
    assert s['ket_luan'] == 'ĐỦ ĐỂ XUỐNG TIỀN', s
    t['dieu_kien_vao'] = [{'loai': 'den', 'khong': ['DO']}, {'loai': 'kiem_chung', 'id': 'K2'}]
    s = H.san_sang(t, {'chua_tra_loi': [], 'nguoc': []}, [], 10, [{'id': 'K2', 'ket_qua': 'ĐÚNG'}], 'DO')
    assert s['ket_luan'] == 'LUẬN ĐIỂM ĐỦ CHẶT — CHỜ ĐIỀU KIỆN VÀO' and [x['dat'] for x in s['dieu_kien_vao']] == [False, True]
    assert H.san_sang(t, {'chua_tra_loi': [], 'nguoc': []}, [], 10, [{'id': 'K2', 'ket_qua': 'ĐÚNG'}], 'VANG')['ket_luan'] == 'ĐỦ ĐỂ XUỐNG TIỀN'
    t['dieu_kien_vao'] = []
    t['vo_hieu_gia'] = 9.0                       # −10%: vượt chuẩn −7%
    s = H.san_sang(t, {'chua_tra_loi': ['tin'], 'nguoc': ['tin']}, [], 10)
    hong = {m['ten'] for m in s['muc'] if not m['dat']}
    assert s['ket_luan'] == 'CHƯA ĐỦ' and any('−7%' in x for x in hong) and any('trả lời' in x for x in hong)
    t['luan_diem'] = [{'id': 'L1', 'nhan': 'INTERPRETATION', 'bang_chung': []}]
    assert not H.san_sang(t, {}, [], 10)['muc'][1]['dat']   # luận điểm không có luận cứ


def test_so_du_doan_ghi_khi_doi_chieu_va_cham():
    from datetime import date, timedelta
    days = [(date(2026, 10, 1) + timedelta(days=i)).isoformat() for i in range(130)]
    g = _gia({'X': [(d, 10 + i * 0.05) for i, d in enumerate(days)]}, [(d, 1000) for d in days])
    D = {'lookup': {'X': {'price': 10, 'rs': 50}}, 'funda': {'X': {'pe': [8, 9, 10, 11, 7]}}, 'regime': [{'light': 'DO'}]}
    may = lambda b, t, d: {'bot': {'chieu': b}, 'tin': {'chieu': t}, 'daily': {'chieu': d}}
    the = [{'luan': {'ma': 'X', 'chieu': 'tang', 'trang_thai': 'trong_port'}, 'ho_so': {'may': may(1, -1, 0)}}]
    so = []
    assert H.ghi_du_doan(so, the, D, g, days[0]) == 4
    assert so[0]['dong_thuan'] == 1 and so[0]['nguoc'] == 1 and so[0]['dac_trung']['pe_rel'] == round(7 / 9, 2)
    assert H.ghi_du_doan(so, the, D, g, days[1]) == 0          # không đổi chiều → không ghi
    the[0]['ho_so']['may']['tin']['chieu'] = 1
    assert H.ghi_du_doan(so, the, D, g, days[2]) == 1           # Tin đổi chiều → một dòng mới
    H.cham_du_doan(so, g)
    port = so[0]
    assert port['dung_20p'] is True and port['dung_120p'] is True and 'vuot_120p' in port
    assert so[3]['dung_20p'] is None                            # Daily trung lập: không chấm đúng/sai
    dc = H.do_chinh_xac(so)
    assert dc['port']['20p']['da_cham'] == 1 and dc['port']['20p']['ty_le'] is None   # mẫu < 10
    assert dc['tin']['20p']['da_cham'] == 2 and dc['tin']['20p']['dung'] == 1


def test_wilson():
    assert H.wilson_thap(0, 0) is None
    assert H.wilson_thap(8, 10) < 80 and H.wilson_thap(80, 100) > H.wilson_thap(8, 10)


def test_hieu_qua_tu_so_lenh():
    g = _gia({'X': zip(DAYS, [10] * 5 + [12] * 5), 'Y': zip(DAYS, [20] * 10)}, zip(DAYS, [1000] * 9 + [1100]))
    sl = {'lenh': [{'ngay': DAYS[0], 'ma': 'X', 'ty_le': 10}, {'ngay': DAYS[1], 'ma': 'Y', 'ty_le': 10, 'gia': 25},
                   {'ngay': DAYS[6], 'ma': 'X', 'ty_le': 5, 'loai': 'ban'}]}
    r = H.hieu_qua(sl, g, DAYS[-1])
    # X: 1 cp-đơn vị giá 10, bán nửa ở 12 → chốt +1; còn nửa: giá trị 6 trên vốn 5. Y: 0,4 đơn vị giá vốn 25, nay 20 → 8.
    assert r['lai_da_chot'] == 1.0 and r['tien_mat'] == 86.0 and r['nav'] == 100.0
    assert r['vni_pct'] == 10.0 and r['vuot_vni'] == -10.0
    assert {v['ma']: v['lai_pct'] for v in r['vi_the']} == {'X': 20.0, 'Y': -20.0}
    assert H.hieu_qua({}, g, DAYS[-1]) is None


# ---------------------------------------------------------------- R38/R39: giải ngân, rủi ro, xác suất chạm, 70/30
import giai_ngan as G  # noqa: E402


def _reg(vals):
    return {'regime': [{'date': '2026-01-%02d' % (i % 28 + 1), 'vni': v} for i, v in enumerate(vals)]}


def test_trang_thai_thi_truong():
    assert G.trang_thai_tt(_reg([1000] * 10 + [790]))['ten'] == 'hoảng loạn'
    assert G.trang_thai_tt(_reg([1000] * 10 + [790]))['ty_le'] == [0.6, 0.4]
    assert G.trang_thai_tt(_reg([1000] * 10 + [880]))['ten'] == 'căng thẳng'
    assert G.trang_thai_tt(_reg([1000] * 10 + [950]))['so_dot'] == 3


def test_xac_suat_cham():
    import math
    c = [100 * math.exp(0.02 * ((-1) ** i)) for i in range(80)]   # σ ngày ≈ 4%
    p = G.xac_suat_cham(c, c[-1] * 1.10, 60)
    assert 0.5 < p < 0.95
    assert G.xac_suat_cham(c, c[-1] * 0.9, 60) == 1.0
    assert G.xac_suat_cham(c[:20], c[-1] * 1.1, 60) is None


def test_nen_di_ngang():
    c = [100.0] * 30 + [100 + (i % 3) for i in range(20)]
    assert G.nen(c, 25)['co'] is True
    assert G.nen(c, 10)['co'] is False                       # cửa sổ chưa nằm trọn sau đợt trước
    roi = [100 - i * 0.3 for i in range(40)]                  # trôi xuống đều: biên nhỏ nhưng tạo đáy mới
    assert G.nen(roi, 30)['co'] is False


def _t(ma='X'):
    return {'ma': ma, 'trang_thai': 'trong_port'}


TT = {'ten': 'căng thẳng', 'vni': 1700, 'ty_le': [1 / 3] * 3}
DATES = ['2026-09-%02d' % d for d in range(1, 29)] + ['2026-10-%02d' % d for d in range(1, 29)]


def test_ke_hoach_dot1_va_hoan():
    c = [10.0] * len(DATES)
    k = G.ke_hoach(_t(), 18, TT, DATES, c, {}, {'ket_luan': 'ĐỦ ĐỂ XUỐNG TIỀN'}, [], 1668.5)
    assert k['muc'] == 'mua' and k['ty_le_mua'] == 6.0
    k = G.ke_hoach(_t(), 18, dict(TT, vni=1600), DATES, c, {}, {'ket_luan': 'ĐỦ ĐỂ XUỐNG TIỀN'}, [], 1668.5)
    assert k['muc'] == 'hoan'
    k = G.ke_hoach(_t(), 18, TT, DATES, c, {}, {'ket_luan': 'CHƯA ĐỦ'}, [], None)
    assert k['muc'] == 'cho'


def test_ke_hoach_ban_ngung_chay_nen():
    sl = lambda g: {'lenh': [{'ngay': DATES[0], 'ma': 'X', 'ty_le': 6, 'gia': g}]}
    flat = [10.0] * len(DATES)
    assert G.ke_hoach(_t(), 18, TT, DATES, flat, sl(12.0), {}, [], None)['muc'] == 'ban'         # −16,7%
    assert G.ke_hoach(_t(), 18, TT, DATES, flat, sl(10.9), {}, [], None)['muc'] == 'ngung'       # −8,3%
    k = G.ke_hoach(_t(), 18, TT, DATES, flat, sl(9.0), {}, [], None)                              # +11%: chạy
    assert k['muc'] == 'mua' and k['ty_le_mua'] == 6.0                                             # nửa của 12
    k = G.ke_hoach(_t(), 18, TT, DATES, flat, sl(10.0), {}, [], None)                             # đi ngang đủ 20 phiên
    assert k['muc'] == 'mua' and k['ty_le_mua'] == 6.0
    assert G.ke_hoach(_t(), 18, TT, DATES, flat, sl(10.0), {}, [{'id': 'K2', 'loai': 'funda', 'ket_qua': 'SAI'}], None)['muc'] == 'ra_soat'


def test_diem_70_30_va_nhiet():
    loc = {'pe': 6, 'pe_tv': 12, 'pb': 1, 'pb_tv': 2, 'np4_yoy': 20, 'roe': 22}
    d = G.diem_70_30({'pitch_diem': {'dinh_gia_sai': 12}}, loc, {'ten': 'hoảng loạn'}, {'dat': 9, 'tong': 9},
                     [{'id': 'K2', 'trang_thai': 'dong', 'ket_qua': 'ĐÚNG'}])
    assert d['pitch'] == 20 + 20 + 15 + 12 and d['ket_qua'] == 30 and d['tong'] == 97
    d = G.diem_70_30({}, {'pe': 20, 'pe_tv': 10}, {'ten': 'bình thường'}, {'dat': 0, 'tong': 9}, [])
    assert d['pitch'] == 4 and d['ket_qua'] == 5
    n = G.nhiet_danh_muc([{'ma': 'A', 'da_giai_ngan': 10, 'lai_lo_pct': 0, 'ty_trong_muc_tieu': 12.5},
                          {'ma': 'B', 'da_giai_ngan': 5, 'lai_lo_pct': -20, 'ty_trong_muc_tieu': 25}])
    assert n['hien_tai'] == 1.5 and n['vi_pham_tran_ma'] == ['B']


def test_lop_danh_muc_cong_vni_va_nhip():
    c = [10.0] * len(DATES)
    ok = {'ket_luan': 'ĐỦ ĐỂ XUỐNG TIỀN'}
    # thị trường bình thường (−5%): không mở mã mới
    k = G.ke_hoach(_t(), 12.5, dict(TT, dd=-5.0), DATES, c, {}, ok, [], None)
    assert k['muc'] == 'cho' and 'Không mở mã mới' in k['hanh_dong']
    # căng thẳng (−11,6%): được mở
    assert G.ke_hoach(_t(), 12.5, dict(TT, dd=-11.6), DATES, c, {}, ok, [], None)['muc'] == 'mua'
    # nhịp: 1 mã mới mở 5 phiên trước → còn 1 lượt; ứng viên xếp theo điểm 70/30
    sl = {'lenh': [{'ngay': DATES[-6], 'ma': 'Z', 'ty_le': 4, 'gia': 10}]}
    mg = G.mo_gan_day(sl, DATES)
    assert mg['dang_nam'] == 1 and mg['mo_gan'] == 1 and mg['phien_toi_luot'] == 15
    the = [dict(luan={'ma': m}, giai_ngan=dict(muc='mua', hanh_dong='Đợt 1', ty_le_mua=4.2, so_lan_mua=0), diem_70_30={'tong': d})
           for m, d in (('A', 60), ('B', 70), ('C', 65))]
    lu = G.xep_luot(the, mg)
    assert lu['slot'] == 1 and lu['uu_tien'] == ['B', 'C', 'A']
    assert [x['giai_ngan']['muc'] for x in the] == ['cho_luot', 'mua', 'cho_luot']
    # đủ 8 mã → không mở thêm
    sl8 = {'lenh': [{'ngay': DATES[0], 'ma': f'M{i}', 'ty_le': 4, 'gia': 10} for i in range(8)]}
    assert G.xep_luot([dict(luan={'ma': 'X'}, giai_ngan=dict(muc='mua', hanh_dong='Đợt 1', so_lan_mua=0), diem_70_30={'tong': 90})],
                      G.mo_gan_day(sl8, DATES))['slot'] == 0


def test_cong_r38_va_noi_fireant():
    ok = {'ket_luan': 'ĐỦ ĐỂ XUỐNG TIỀN'}
    tt = dict(TT, dd=-11.6)
    d = [f'2025-{1 + i // 28:02d}-{1 + i % 28:02d}' for i in range(260)]
    c = [20.0] * 100 + [16.0] * 160                                  # −20%: chưa tới cổng
    k = G.ke_hoach(_t(), 12.5, tt, d, c, {}, ok, [], None)
    assert k['muc'] == 'cho_gia' and k['cong_r38']['gia_cong'] == 15.0
    k = G.ke_hoach(_t(), 12.5, tt, d, c[:-1] + [14.9], {}, ok, [], None)
    assert k['muc'] == 'mua' and k['cong_r38']['dat']
    assert G.ke_hoach(dict(_t(), cong_r38=False), 12.5, tt, d, c, {}, ok, [], None)['muc'] == 'mua'
    # nối: FireAnt dài hơn nến web → dùng FireAnt, nối phiên web mới hơn
    D = {'candles': {'X': {'bars': [['2025-01-02', 0, 0, 0, 10.0], ['2025-01-03', 0, 0, 0, 11.0]]}}}
    fd, fc = G.chuoi_gia(D, 'X', 'HOSE', (['2024-12-30', '2024-12-31', '2025-01-02'], [8.0, 9.0, 5.0]))
    assert fd[-1] == '2025-01-03' and abs(fc[-1] - 5.5) < 1e-9
    assert G.chuoi_gia(D, 'X', 'HOSE', ([], []))[1] == [10.0, 11.0]


def test_diem_dieu_chinh_cot_loi():
    loc = {'pe': 6, 'pe_tv': 22, 'pb': 0.93, 'pb_tv': 0.98, 'np4_yoy': 300, 'roe': 16}
    t = {'pitch_diem': {'dinh_gia_sai': 5, 'dieu_chinh': {'dinh_gia_rel': 0.95, 'roe': 11}}}
    d = G.diem_70_30(t, loc, {'ten': 'căng thẳng'}, {'dat': 9, 'tong': 9}, [])
    assert d['chi_tiet']['dinh_gia'] == 7 and d['chi_tiet']['roe'] == 4 and d['chi_tiet']['dieu_chinh']
