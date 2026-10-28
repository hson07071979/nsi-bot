# -*- coding: utf-8 -*-
"""Cào vĩ mô (28/10/2026): đọc đúng định dạng từng nguồn, chỉ dùng số trước ngày chạy, nguồn chết thì sang dự phòng,
xu hướng theo z, sổ không sửa dòng cũ. Không gọi mạng."""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'vimo'))
import cao as C  # noqa: E402
import nguon as NG  # noqa: E402


def _chuoi(n, f, tu=(2026, 1, 1)):
    from datetime import date, timedelta
    d0 = date(*tu)
    return [((d0 + timedelta(days=i)).isoformat(), f(i)) for i in range(n)]


def test_doc_dinh_dang_nguon():
    assert NG.doc_csv_fred('observation_date,DGS10\n2026-10-23,5.01\n2026-10-24,.\n2026-10-26,5.00\n') == \
        [('2026-10-23', 5.01), ('2026-10-26', 5.0)]
    j = {'chart': {'result': [{'timestamp': [1761523200, 1761609600], 'indicators': {'quote': [{'close': [110.5, None]}]}}]}}
    assert NG.doc_json_yahoo(j) == [('2025-10-27', 110.5)]
    assert NG.doc_csv_stooq('Date,Open,High,Low,Close\n2026-10-27,1,2,0,25841\n') == [('2026-10-27', 25841.0)]
    x = '<DateTime>10/28/2026 9:25:39 PM</DateTime><Exrate CurrencyCode="USD" CurrencyName="US DOLLAR" Buy="25,811.00" Transfer="25,841.00" Sell="26,201.00" />'
    assert NG.doc_xml_vcb(x) == [('2026-10-28', 25841.0)]
    assert NG.doc_json_yahoo({}) == [] and NG.doc_xml_vcb('rác') == []


def test_z_xu_huong():
    tang = _chuoi(400, lambda i: 100 + (i % 20) * 0.1 + (30 if i > 380 else 0))
    z, xh = C.z_xu_huong(tang, 20, 'pct')
    assert xh == 'tang' and z > 0.5
    phang = _chuoi(400, lambda i: 100.0)
    assert C.z_xu_huong(phang, 20, 'pct')[1] == 'ngang'
    assert C.z_xu_huong(_chuoi(30, lambda i: i), 20, 'pct') == (None, 'thiếu')
    assert C.thay_doi([('a', 5.0), ('b', 5.2)], 1, 'diem') == 0.2


def test_chup_khong_nhin_truoc_va_du_phong(tmp_path, monkeypatch):
    s = _chuoi(400, lambda i: 100 + i * 0.01)            # tới 2027-02-04
    goi = []

    def fred(sym):
        goi.append(('fred', sym))
        return [] if sym == 'DGS10' else s                # DGS10 hỏng → sang Yahoo

    def yahoo(sym):
        goi.append(('yahoo', sym))
        return s
    monkeypatch.setattr(C, 'BIEN', {k: C.BIEN[k] for k in ('us10y', 'brent', 'quang_sat')})
    anh, chuoi = C.chup('2026-06-01', dict(fred=fred, yahoo=yahoo, stooq=lambda x: [], vcb=lambda x=None: []))
    assert anh['us10y']['nguon'] == 'yahoo:^TNX' and anh['us10y']['ngay_so'] == '2026-05-31'   # chỉ số trước ngày chạy
    assert anh['brent']['doi_chieu']['nguon'] == 'fred:DCOILBRENTEU'
    assert all(x[0] < '2026-06-01' for x in chuoi['brent'])
    C.ghi(tmp_path, '2026-06-01', anh, chuoi)
    C.ghi(tmp_path, '2026-06-02', anh, chuoi)
    C.ghi(tmp_path, '2026-06-02', anh, chuoi)                 # chạy lại cùng ngày: thay dòng hôm đó, không nhân đôi
    rows = list(csv.DictReader(open(tmp_path / 'so_vi_mo.csv', encoding='utf-8')))
    assert [r['ngay'] for r in rows] == ['2026-06-01', '2026-06-02']
    m = json.load(open(tmp_path / 'moi_nhat.json', encoding='utf-8'))
    assert m['lay_duoc'] == 3 and (tmp_path / 'chuoi' / 'brent.csv').exists()


def test_nguon_chet_bi_bo(monkeypatch):
    cu = _chuoi(300, lambda i: 50.0)                     # dừng ở 2026-10-27 → chạy 2027-01-10 là quá 10 ngày
    monkeypatch.setattr(C, 'BIEN', {'brent': C.BIEN['brent']})
    anh, _ = C.chup('2027-01-10', dict(yahoo=lambda x: cu, fred=lambda x: [], stooq=lambda x: [], vcb=lambda x=None: []))
    assert anh['brent']['gia_tri'] is None
