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


RSS_XML = b'''<?xml version="1.0"?><rss><channel>
<item><title>CPI th\xc3\xa1ng 9 t\xc4\x83ng 3,85% so v\xe1\xbb\x9bi c\xc3\xb9ng k\xe1\xbb\xb3 - VnEconomy</title><pubDate>Mon, 06 Oct 2026 03:00:00 GMT</pubDate><source>VnEconomy</source></item>
<item><title>Tin ng\xc3\xa0y mai</title><pubDate>Fri, 30 Oct 2026 03:00:00 GMT</pubDate><source>X</source></item>
</channel></rss>'''


def test_rss_chi_nhan_so_co_trong_tin():
    tin = {'cpi_vn': V.tin_rss('cpi_vn', NGAY, get=lambda *a, **k: _Resp2(RSS_XML))}
    assert len(tin['cpi_vn']) == 1 and tin['cpi_vn'][0]['ngay'] == '2026-10-06'
    ok = V.tu_rss(dict(bien=dict(cpi_vn=dict(gia_tri=3.85, so_trong_tin='3,85%', tin='cpi_vn#0', ky='09/2026'))), tin)
    assert ok['bien']['cpi_vn']['ngay_cong_bo'] == '2026-10-06' and 'VnEconomy' in ok['bien']['cpi_vn']['nguon']
    bia = V.tu_rss(dict(bien=dict(cpi_vn=dict(gia_tri=4.1, so_trong_tin='4,1%', tin='cpi_vn#0'))), tin)
    assert bia['bien'] == {}
    rec, _ = V.kiem('cpi_vn', ok['bien']['cpi_vn'], NGAY, None)
    assert rec['gia_tri'] == 3.85


class _Resp2:
    def __init__(self, c):
        self.content, self.status_code = c, 200


def test_den_lich():
    assert not V.den_lich('2026-10-29', '2026-10-28')          # thứ Năm, ngày 29, mới chạy hôm qua
    assert V.den_lich('2026-11-02', '2026-10-29')              # thứ Hai
    assert V.den_lich('2026-11-05', '2026-11-04')              # ngày 1–10
    assert V.den_lich('2026-10-28', '2026-10-20') and V.den_lich('2026-10-28', None)


def test_tu_nso_chi_nhan_so_trong_bai():
    bai = dict(tieu_de='Báo cáo quý III', ngay='2026-10-06',
               van_ban='CPI tháng Chín tăng 5,08% so với cùng kỳ; kim ngạch xuất khẩu hàng hóa đạt 434,30 tỷ USD, tăng 24,5%')
    out = dict(bien=dict(cpi_vn=dict(gia_tri=5.08, so_trong_tin='5,08%', ky='09/2026'),
                         xuat_khau_vn=dict(gia_tri=24.6, so_trong_tin='24,6%'),
                         lam_bay=dict(gia_tri=1)))
    tu = V.tu_nso(out, bai)
    assert list(tu) == ['cpi_vn'] and tu['cpi_vn']['ngay_cong_bo'] == '2026-10-06' and 'Cục Thống kê' in tu['cpi_vn']['nguon']
