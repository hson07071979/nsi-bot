# -*- coding: utf-8 -*-
"""Vĩ mô VN tự động: chọn model rẻ nhất, chống bịa, giữ số cũ (29/10/2026)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'vimo'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'port'))
import vn_ai as V  # noqa: E402
import ho_so as HS  # noqa: E402

NGAY = '2026-10-29'


def test_chon_model_lite_truoc():
    ten = ['gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-3.0-flash-lite-preview', 'gemini-3.0-flash',
           'gemini-2.5-flash-image', 'gemini-2.5-pro']
    assert V.chon_model(ten) == ['gemini-3.0-flash-lite-preview', 'gemini-2.5-flash-lite', 'gemini-3.0-flash', 'gemini-2.5-flash']


def _r(v=3.5, ngay='2026-10-06', ky='09/2026'):
    return dict(gia_tri=v, ky=ky, ngay_cong_bo=ngay, xu_huong='giam', ly_do='x', nguon='Cục Thống kê 06/10')


def test_kiem_loai_so_bia():
    assert V.kiem('cpi_vn', _r(v=55), NGAY, None)[0] is None             # ngoài khoảng
    assert V.kiem('cpi_vn', _r(ngay='2026-11-05'), NGAY, None)[0] is None  # tương lai
    assert V.kiem('cpi_vn', _r(ngay='2026-03-01'), NGAY, None)[0] is None  # cũ
    assert V.kiem('cpi_vn', dict(_r(), nguon=''), NGAY, None)[0] is None
    assert V.kiem('cpi_vn', _r(v='3,5%'), NGAY, None)[0]['gia_tri'] == 3.5


def test_xu_huong_code_tinh_khi_co_ky_truoc():
    rec, _ = V.kiem('cpi_vn', _r(v=5.4), NGAY, dict(gia_tri=5.08, ky='08/2026'))
    assert rec['xu_huong'] == 'tang' and rec['xu_huong_tu'].startswith('code')
    rec, _ = V.kiem('von_ngoai_vn', _r(v=-12, ky='10/2026'), NGAY, None)
    assert rec['xu_huong'] == 'giam'


def test_gop_giu_so_cu_khi_hong():
    cu = dict(cpi_vn=dict(ten='CPI', gia_tri=5.08, ky='08/2026', ngay='2026-09-06', xu_huong='tang', nguon='GSO'))
    bien, loai = V.gop(cu, None, NGAY)
    assert bien['cpi_vn']['gia_tri'] == 5.08 and 'giữ số cũ' in bien['cpi_vn']['loi'] and loai['cpi_vn'] == 'lượt hỏng'


class _Resp:
    def __init__(self, j, code=200):
        self.status_code, self._j, self.text = code, j, json.dumps(j)

    def json(self):
        return self._j


def test_hoi_bat_buoc_grounding(monkeypatch):
    monkeypatch.setenv('GEMINI_MODELS_VIMO', 'm1,m2')
    txt = '```json\n{"bien": {"cpi_vn": {"gia_tri": 3.5}}}\n```'
    khong = dict(candidates=[dict(content=dict(parts=[dict(text=txt)]))])
    co = dict(candidates=[dict(content=dict(parts=[dict(text=txt)]),
                               groundingMetadata=dict(webSearchQueries=['cpi'], groundingChunks=[dict(web=dict(title='nso.gov.vn'))]))])
    seq = iter([_Resp(khong), _Resp(co)])
    out, meta = V.hoi('k', 'p', post=lambda *a, **k: next(seq))
    assert out['bien']['cpi_vn']['gia_tri'] == 3.5 and meta['model'] == 'm2' and 'groundingMetadata' in meta['loi']['m1']


def test_ho_so_lay_ban_tu_dong_khi_moi_hon():
    tay = dict(cpi_vn=dict(ten='CPI', xu_huong='tang', ngay='2026-10-07'), gdp_vn=dict(ten='GDP', xu_huong='tang', ngay='2026-10-06'))
    ai = dict(bien=dict(cpi_vn=dict(ten='CPI', gia_tri=3.9, xu_huong='giam', ngay='2026-10-28'),
                        gdp_vn=dict(ten='GDP', gia_tri=8.0, xu_huong='giam', ngay='2026-07-06')))
    b = HS.bien_hom_nay({}, tay, ai)
    assert b['cpi_vn']['xu_huong'] == 'giam' and b['cpi_vn']['tu_dong']
    assert b['gdp_vn']['xu_huong'] == 'tang' and not b['gdp_vn']['tu_dong']
