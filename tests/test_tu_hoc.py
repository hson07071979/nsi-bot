# -*- coding: utf-8 -*-
"""Vòng học tự đổi (24/10/2026): pool_hoc học thang pool, tu_hoc tự đổi + chờ 28 ngày.
Run: PORT_KHONG_CHUONG=1 python -m pytest -q tests/test_tu_hoc.py"""
import os
import sys
from datetime import date, timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'port'))
import nhan_dinh as ND   # noqa: E402
import pool as PO        # noqa: E402
import pool_hoc as PH    # noqa: E402
import tu_hoc as TH      # noqa: E402


def _mau(seed=1, nam=(2020, 2021, 2022, 2023, 2024, 2025), tin_hieu='vol', thieu=()):
    """Mẫu giả: mức hơn VN-Index sau 60 phiên phụ thuộc phần `tin_hieu`; phần khác là nhiễu."""
    rng = np.random.default_rng(seed)
    out = []
    for y in nam:
        d = date(y, 1, 6)
        while d.year == y:
            for j in range(30):
                x = {k: float(rng.choice([0, 0.33, 0.67, 1.0])) for k in PH.K}
                co = {k: k not in thieu for k in PH.K}
                if not co['vol']:
                    x['vol'] = 0.0
                yy = 8 * x[tin_hieu] + rng.normal(0, 4)
                out.append(dict(ngay=d.isoformat(), ma=f'M{j}', x=x, co=co, y={20: yy / 2, 60: yy, 120: yy}))
            d += timedelta(days=7)
    return out


def test_hoc_tim_dung_phan_co_ich_va_qua_bai_thi():
    r = PH.hoc(_mau(tin_hieu='vol'), dict(PO.THANG))
    t = r['de_xuat']['thang']
    assert sum(t.values()) in (99, 100, 101)
    assert t['vol'] == max(t.values()) and t['vol'] > PO.THANG['vol']
    assert r['dat_chuan'] and r['nam_hon'] * 3 >= r['so_nam'] * 2 and r['t'] >= 2
    assert r['ic_tung_phan']['vol']['ic'] > 0.3


def test_khong_doi_khi_thang_dang_dung_da_tot():
    m = _mau(tin_hieu='nen')
    tot = PH.luyen(m, 60, dict(PO.THANG))['thang']
    r = PH.hoc(m, tot)
    assert not r['dat_chuan']


def test_phan_thieu_du_lieu_giu_nguyen():
    r = PH.hoc(_mau(tin_hieu='nen', thieu=('vol',)), dict(PO.THANG))
    assert 'vol' in r['de_xuat']['giu_nguyen'] and r['de_xuat']['thang']['vol'] == PO.THANG['vol']


def test_cham_theo_thang():
    pg = dict(thap=25, nen=15, vol=0, bien=5, nganh=10, dinh_gia=0, ln_hoi=0, roe=5)
    t = dict(PO.THANG, thap=50, vol=0)
    p = PO.theo_thang(pg, t)
    assert p['thap'] == 50 and p['vol'] == 0 and p['nen'] == 15


def test_tu_doi_cho_28_ngay_va_giu_lich_su(tmp_path, monkeypatch):
    gui = []
    monkeypatch.setattr(TH.NH, 'gui', lambda a, b: gui.append(a) or True)
    a = TH.ap_dung(tmp_path, 'thang_pool', dict(ten='moi', thang={'thap': 30}), dict(ten='cu'), '2026-10-24', 'T', 'N')
    assert a and gui == ['T'] and TH.doc(tmp_path, 'thang_pool')['thang'] == {'thap': 30}
    assert TH.ap_dung(tmp_path, 'thang_pool', dict(ten='moi2'), None, '2026-11-10', 'T', 'N') is None
    assert TH.con_cho(tmp_path, 'thang_pool', '2026-11-10') == 11
    assert TH.ap_dung(tmp_path, 'thang_pool', dict(ten='moi3'), None, '2026-11-21', 'T', 'N')
    ls = TH.lich_su(tmp_path, 'thang_pool')
    assert [x['moi']['ten'] for x in ls] == ['moi', 'moi3'] and ls[0]['cu']['ten'] == 'cu' and len(gui) == 2


def test_mau_lui_tren_gia_gia():
    """Chạy lùi trên giá giả: ra mẫu, chỉ trong nhóm qua luật nền thấp, có nhãn, không nhìn trước."""
    rng = np.random.default_rng(3)
    lich, d = [], date(2019, 1, 2)
    while len(lich) < 900:
        if d.weekday() < 5:
            lich.append(d.isoformat())
        d += timedelta(days=1)
    gia = {}
    for j in range(20):
        r = rng.normal(-0.0004, 0.012, len(lich))
        gia[f'M{j}'] = dict(zip(lich, 20 * np.exp(np.cumsum(r))))
    B = ND.Bang(lich, list(np.linspace(1000, 1100, len(lich))), gia)
    V = {s: rng.uniform(1e5, 3e5, len(lich)) for s in gia}
    m = PH.mau_lui(B, V, {}, {s: 'Thép' for s in gia}, buoc=20)
    assert m
    assert all(x['ngay'] >= PH.TU for x in m)
    assert all(0 <= v <= 1 for x in m for v in x['x'].values())
    assert any(x['y'][60] is not None for x in m) and any(x['y'][60] is None for x in m)   # cuối kỳ chưa có nhãn
    assert all(x['co']['vol'] for x in m)
