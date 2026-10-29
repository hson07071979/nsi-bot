# -*- coding: utf-8 -*-
"""Luận điểm tự sang quý mới (29/10/2026)."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'port'))
import loc_quy as LQ  # noqa: E402
import quy_tu_dong as QT  # noqa: E402


def _bc(q_moi, lnst, lnst0, loi=100.0, loi0=90.0):
    y = int(q_moi.split('/')[1])
    qn = int(q_moi[1])
    q0 = f'Q{qn}/{y - 1}'
    return dict(moi_nhat=q_moi, quy=[dict(q=q0, lnst_me=lnst0, loi=loi0), dict(q=q_moi, lnst_me=lnst, loi=loi)],
                cau_chuyen=['câu 1', 'câu 2'])


def _t(**kw):
    t = dict(ma='X', quy_bctc='Q2/26', dk_luc_viet=dict(a=True, b=True, c=False, d=True),
             kiem_chung=[dict(id='K1', loai='funda', chi_tieu='ny', quy='Q3/26', so_sanh='>=', nguong=0)])
    t.update(kw)
    return t


DK_GIU = {k: dict(dat=v) for k, v in dict(a=True, b=True, c=False, d=True).items()}


def test_khop_khi_chua_co_quy_moi():
    assert QT.xet(_t(quy_bctc='Q3/26'), _bc('Q3/26', 120, 100), DK_GIU)['trang_thai'] == 'khop'


def test_tu_gia_han_khi_khong_doi():
    x = QT.xet(_t(), _bc('Q3/26', 120, 100), DK_GIU)
    assert x['trang_thai'] == 'tu_gia_han', x
    assert x['moc'][0]['ket_qua'] == 'ĐÚNG' and x['so_moi'] == ['câu 1', 'câu 2']


def test_can_review_khi_moc_sai_va_giam_manh():
    x = QT.xet(_t(), _bc('Q3/26', 70, 100), DK_GIU)
    assert x['trang_thai'] == 'can_review'
    assert any('K1' in l for l in x['ly_do']) and any('-30.0%' in l for l in x['ly_do'])


def test_can_review_khi_dieu_kien_doi():
    dk = dict(DK_GIU, a=dict(dat=False))
    x = QT.xet(_t(), _bc('Q3/26', 120, 100), dk)
    assert x['trang_thai'] == 'can_review' and 'điều kiện a' in x['ly_do'][0]


def test_loi_cot_loi_chuyen_am():
    x = QT.xet(_t(kiem_chung=[]), _bc('Q3/26', 120, 100, loi=-5, loi0=50), DK_GIU)
    assert x['trang_thai'] == 'can_review'


def test_rows_den_live_lay_quy_moi_nhung_chay_lui_khong():
    rows = [dict(y=2026, q=2, avail='2026-08-14'), dict(y=2026, q=3, avail='2026-11-14')]
    d = date(2026, 10, 29)
    assert [r['q'] for r in LQ.rows_den(rows, d)] == [2]
    assert [r['q'] for r in LQ.rows_den(rows, d, live=True)] == [2, 3]
    assert [r['q'] for r in LQ.rows_den(rows, date(2026, 9, 15), live=True)] == [2]   # quý chưa kết thúc


def test_hang_review():
    k = dict(A=dict(trang_thai='can_review', quy_moi='Q3/26', ly_do=['x']), B=dict(trang_thai='tu_gia_han', quy_moi='Q3/26'),
             C=dict(trang_thai='khop', quy_moi='Q2/26'))
    h = QT.hang_review(k)
    assert h['quy'] == 'Q3/26' and [x['ma'] for x in h['can_review']] == ['A'] and h['tu_gia_han'] == ['B']
