# -*- coding: utf-8 -*-
"""Nut vuot cong dong tien (11/10/2026): chi DUNG san + DUNG phien, file hong -> van chan.
Chay: python tests/test_vuot.py"""
import os, sys, json, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import vuot


def _f(obj):
    p = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8')
    p.write(obj if isinstance(obj, str) else json.dumps(obj)); p.close()
    return p.name


def test_khop_dung_san_dung_phien():
    p = _f({'bo_qua_dong_tien': [{'san': 'HNX', 'phien': '2026-10-09', 'luc': 'x'}]})
    assert vuot.khop('HNX', '2026-10-09', p)
    assert vuot.dang_vuot('2026-10-09', p) == ['HNX']


def test_phien_khac_san_khac_van_chan():
    p = _f({'bo_qua_dong_tien': [{'san': 'HNX', 'phien': '2026-10-09'}]})
    assert vuot.khop('HNX', '2026-10-12', p) is None          # phien sau: chan lai
    assert vuot.khop('HNX', '2026-10-08', p) is None
    assert vuot.khop('HOSE', '2026-10-09', p) is None         # san khac
    assert vuot.khop('UPCOM', '2026-10-09', p) is None        # khong phai san cua cong
    assert vuot.khop('HNX', '', p) is None


def test_file_hong_hoac_thieu_van_chan():
    for bad in ('', '{', '[]', '{"bo_qua_dong_tien": "HNX"}', '{"bo_qua_dong_tien": [1, null]}'):
        assert vuot.khop('HNX', '2026-10-09', _f(bad)) is None, bad
    assert vuot.khop('HNX', '2026-10-09', '/khong/co/file.json') is None
    assert vuot.dang_vuot('2026-10-09', '/khong/co/file.json') == []


def test_verify_build_dung_nut_khong_tu_vuot():
    # cong van check() mac dinh; chi doi sang warn() khi vuot.khop() tra ve muc
    src = open(os.path.join(ROOT, 'verify_build.py'), encoding='utf-8').read()
    assert 'vuot.khop(_ex, asof)' in src
    assert "check(_c >= 0.80" in src
    assert '_qua_ngay' not in src                              # ban tu vuot theo gio da revert


if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_'): f(); print('PASS', k); n += 1
    print(f'{n}/{n} passed')
