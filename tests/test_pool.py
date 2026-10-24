# -*- coding: utf-8 -*-
"""Pool tuần của Lọc port (port/pool.py, 24/10/2026). Run: PORT_KHONG_CHUONG=1 python -m pytest -q tests/test_pool.py"""
import os
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'port'))
import nhan_dinh as ND   # noqa: E402
import pool as PO        # noqa: E402


def _ngay(n, tu=date(2025, 6, 2)):
    out, d = [], tu
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _gia_nen_thap(n=260, dinh=20.0, day=10.0, nen=0.05):
    """Lên đỉnh rồi rơi về đáy, 40 phiên cuối đi ngang trong biên `nen`."""
    a = [dinh] * 60 + [dinh - (dinh - day) * k / (n - 100) for k in range(n - 100)] + [day] * 40
    for k in range(1, 41):
        a[-k] = day * (1 + (nen if k % 2 else 0))
    return a


def test_dac_trung_va_loai_nen_cao():
    f = PO.dac_trung_gia(_gia_nen_thap(), vols=[1000] * 200 + [400] * 60)
    assert f['tu_dinh'] <= -0.45 and f['nen30'] <= 0.06 and f['vol_ratio'] < 0.6
    k = PO.cham(f, -0.35, {'dinh_gia_rel': 0.55, 'np4_yoy': 5, 'roe': 18}, {'npat_yoy': -20, 'rev_yoy': 3}, {}, 'Thép')
    assert k['dat'] and k['diem'] >= 80 and not k['tru']
    gan_dinh = PO.dac_trung_gia([10.0] * 200 + [10.0 + 0.02 * k for k in range(60)])
    k2 = PO.cham(gan_dinh, None, None, None, {}, '')
    assert not k2['dat'] and any('gần đỉnh' in x for x in k2['loai'])


def test_cfo_no_xau_tru_diem_khong_loai():
    f = PO.dac_trung_gia(_gia_nen_thap(), vols=[1000] * 260)
    sach = PO.cham(f, None, None, {}, {}, 'Thép')
    ban = PO.cham(f, None, None, {'icr': 0.8, 'de': 5}, {'cfo_ty': -500, 'tim': True}, 'Thép')
    assert ban['dat'] and ban['diem'] == sach['diem'] - 10 - 8 - 5 - 3 and len(ban['ly_do_tru']) == 4
    nh = PO.cham(f, None, None, {}, {'cfo_ty': -9000, 'block': 'NPL 3.49% > 3%'}, 'Ngân hàng')
    assert set(nh['tru']) == {'npl'}                     # ngân hàng: CFO không trừ, nợ xấu trừ


def _site(syms, wl):
    lk = {s: dict(inuni=True, sector='Thép' if k % 2 else 'Ngân hàng', name=s, price=10.0) for k, s in enumerate(syms)}
    return dict(lookup=lk, screener=dict(rows=[]), watchlist=dict(members=[{'sym': s} for s in wl]), candles={})


def test_luot_chay_chot_pool_theo_tuan(tmp_path):
    syms = [f'M{k:02d}' for k in range(40)]
    ds = _ngay(260)
    gia = {}
    for k, s in enumerate(syms):
        g = _gia_nen_thap(dinh=20.0, day=10.0 + 0.1 * k) if k < 35 else [10.0] * 200 + [10 + 0.05 * j for j in range(60)]
        gia[s] = dict(zip(ds, g))
    B = ND.Bang(ds, [1000.0] * len(ds), gia)
    D = _site(syms, wl=['M01', 'M38'])
    r = PO.chay(D, {}, B, ds[-1], tmp_path, gui_chuong=False)
    assert r['tu_wl'] == ['M01']                         # M38 trong watchlist nhưng gần đỉnh → không qua lọc
    assert len(r['rieng']) == PO.N_RIENG and 'M01' not in r['rieng']
    assert all(not s.startswith('M3') or int(s[1:]) < 35 for s in r['rieng'])
    n = r['so_tong']
    assert n == 40                                       # sổ pool bóng: mọi mã TOP110, một dòng/tuần
    r2 = PO.chay(D, {}, B, ds[-1], tmp_path, gui_chuong=False)   # cùng tuần → không chốt lại, không ghi thêm
    assert r2['so_tong'] == n and r2['tu_wl'] == r['tu_wl'] and r2['rieng'] == r['rieng']


def test_soat_ma_dang_cam():
    syms = ['AAA', 'BBB']
    ds = _ngay(260)
    gia = {'AAA': dict(zip(ds, _gia_nen_thap())), 'BBB': dict(zip(ds, [10.0] * 200 + [10 + 0.05 * j for j in range(60)]))}
    B = ND.Bang(ds, [1000.0] * len(ds), gia)
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        r = PO.chay(_site(syms, []), {}, B, ds[-1], Path(d), gui_chuong=False,
                    luan={'AAA': {'trang_thai': 'trong_port'}, 'BBB': {'trang_thai': 'trong_port'}})
    m = {x['ma']: x for x in r['soat_luan_diem']}
    assert m['AAA']['trong_pool'] and not m['BBB']['trong_pool'] and m['BBB']['loai']
