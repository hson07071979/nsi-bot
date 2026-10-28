# -*- coding: utf-8 -*-
"""Hồ sơ doanh nghiệp (28/10/2026): thuận/nghịch theo chiều × xu hướng, sổ điểm-thời-gian, đo độ nhạy, cờ lật NGHỊCH."""
import json
import os
import sys
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'port'))
import ho_so as HS  # noqa: E402
from test_port_moi import _ngay  # noqa: E402

HSO = dict(ma='HPG', bien=[dict(bien='us10y', chieu=-1, kenh='lãi vay'), dict(bien='hrc_my', chieu=1, kenh='giá bán'),
                           dict(bien='ls_vn', chieu=-1, kenh='lãi vay VN')])


def _vm(xh10, xhhrc):
    return dict(ngay='2026-10-28', bien=dict(
        us10y=dict(ten='Mỹ 10 năm', gia_tri=5.0, xu_huong=xh10, do='diem', cua_so=20),
        hrc_my=dict(ten='HRC Mỹ', gia_tri=900, xu_huong=xhhrc, do='pct', cua_so=20)))


def test_thuan_nghich():
    vn = dict(ls_vn=dict(ten='Lãi huy động VN', xu_huong='giam', ngay='2026-10-21', nguon='TBTC'))
    t = HS.trang_thai(HSO, HS.bien_hom_nay(_vm('giam', 'tang'), vn))
    assert t['tong'] == 'THUẬN' and t['diem'] == 3 and [b['tt'] for b in t['bien']] == ['THUẬN'] * 3
    t = HS.trang_thai(HSO, HS.bien_hom_nay(_vm('tang', 'ngang'), {}))
    assert t['tong'] == 'NGHỊCH' and t['thieu'] == 1           # ls_vn không có → thiếu, không tính
    t = HS.trang_thai(HSO, HS.bien_hom_nay(_vm('tang', 'tang'), {}))
    assert t['tong'] == 'TRUNG TÍNH'


def _B(n=600, beta=2.0, seed=1):
    rng = np.random.default_rng(seed)
    x = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))           # biến
    v = 1000 * np.cumprod(1 + rng.normal(0, 0.005, n))         # VN-Index
    a = np.empty(n)
    a[0] = 10
    for i in range(1, n):
        a[i] = a[i - 1] * (v[i] / v[i - 1]) * (1 + beta * (x[i] / x[i - 1] - 1))
    lich = _ngay(n, )
    return SimpleNamespace(lich=lich, vni=v, c={'A': a}), x


def test_do_nhay_va_de_xuat(tmp_path):
    B, x = _B(beta=2.0)
    d = HS.do_nhay(B, 'A', x)
    assert d['n'] >= 25 and d['r'] > 0.8 and d['t'] > 2
    vdir = tmp_path / 'vi_mo'
    (vdir / 'chuoi').mkdir(parents=True)
    with open(vdir / 'chuoi' / 'dong.csv', 'w', encoding='utf-8') as f:
        f.write('ngay,gia_tri\n' + ''.join(f'{d},{v}\n' for d, v in zip(B.lich, x)))
    hs = {'A': dict(ma='A', bien=[dict(bien='dong', chieu=-1)])}        # viết ngược chiều thực tế
    h = HS.hoc_do_nhay(hs, B, vdir, dict(bien=dict(dong=dict(do='pct'))))
    assert h['theo_ma']['A']['dong']['khop'] is False and h['de_xuat'][0]['ma'] == 'A'
    hs['A']['bien'][0]['chieu'] = 1
    assert HS.hoc_do_nhay(hs, B, vdir, dict(bien=dict(dong=dict(do='pct'))))['de_xuat'] == []


def test_so_va_cham():
    B, _ = _B(n=120)
    so = HS.ghi_so([], B.lich[10], {'A': dict(dau=1, diem=2)})
    so = HS.ghi_so(so, B.lich[10], {'A': dict(dau=-1, diem=-1)})       # chạy lại cùng ngày: thay, không nhân đôi
    assert len(so) == 1 and so[0]['dau'] == -1
    c = HS.cham_so(so, B)
    assert c['20p']['NGHỊCH']['n'] == 1 and c['20p']['THUẬN']['n'] == 0


def test_chay_co_lat_nghich(tmp_path):
    root, state = tmp_path / 'port', tmp_path / 'port' / 'state'
    (root / 'ho_so').mkdir(parents=True)
    (state / 'vi_mo').mkdir(parents=True)
    (root / 'ho_so' / 'HPG.json').write_text(json.dumps(HSO), encoding='utf-8')
    (state / 'vi_mo' / 'moi_nhat.json').write_text(json.dumps(_vm('giam', 'tang')), encoding='utf-8')
    gui = []
    r = HS.chay(root, state, None, '2026-10-27', vi_the={'HPG'}, gui=lambda a, b: gui.append(b))
    assert r['trang_thai']['HPG']['tong'] == 'THUẬN' and not r['co']
    (state / 'vi_mo' / 'moi_nhat.json').write_text(json.dumps(_vm('tang', 'giam')), encoding='utf-8')
    r = HS.chay(root, state, None, '2026-10-28', vi_the={'HPG'}, gui=lambda a, b: gui.append(b))
    assert r['co'] and 'HPG lật sang NGHỊCH' in gui[0]
    r = HS.chay(root, state, None, '2026-10-29', vi_the={'HPG'}, gui=lambda a, b: gui.append(b))
    assert not r['co'] and len(gui) == 1                                  # đã NGHỊCH từ hôm qua → không chuông lại
