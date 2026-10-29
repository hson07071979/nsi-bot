# -*- coding: utf-8 -*-
"""Luận điểm tự sang quý mới (anh Sơn 29/10/2026).

Yêu cầu: (1) bộ máy làm một lần bằng code, không viết lại luận điểm mỗi khi có số; (2) người chỉ review tối đa 1 lần/quý;
(3) công ty nào đã có số quý mới thì dùng luôn số đó; (4) hồ sơ cốt lõi (mô hình kinh doanh, lãnh đạo, chuỗi giá trị,
dẫn ngược vĩ mô) viết một lần.

Cách làm: luận điểm ghi `quy_bctc` = quý đã đọc lúc viết và `dk_luc_viet` = 4 điều kiện lúc viết. Khi BCTC quý mới về
(đọc thẳng data/funda_raw2.json qua bctc.phan_tich — không chờ mốc 45 ngày của bot), máy tự so:
  · mốc kiểm chứng cơ bản (K…) có hạn đúng quý mới → chấm ĐÚNG/SAI bằng LNST công ty mẹ so cùng kỳ;
  · LNST quý mới giảm ≥ 20% so cùng kỳ;
  · lợi nhuận kinh doanh cốt lõi quý mới đổi chiều (cùng kỳ dương → nay âm);
  · 4 điều kiện a–d đổi trạng thái so với lúc viết (đạt → trượt hoặc trượt → đạt).
Không có gì đổi → TỰ GIA HẠN: luận điểm vẫn dùng được, số quý mới do máy tự ghi (câu theo khuôn của bctc.py), không
chặn giải ngân. Có thay đổi → CẦN REVIEW: vào hàng review của quý; chặn giải ngân mã đó tới khi review.
Phần hồ sơ cốt lõi (CO_DINH) không bao giờ bị đòi viết lại vì quý mới.
"""
from __future__ import annotations

CO_DINH = ('mo_hinh_kd', 'lanh_dao', 'chuoi_gia_tri', 'dan_nguoc_vi_mo')
GIAM_MANH = -20.0          # % LNST so cùng kỳ coi là đổi câu chuyện


def _qk(q):
    """'Q3/26' → (2026, 3); None nếu lạ."""
    try:
        qq, yy = str(q)[1:].split('/')
        y = int(yy)
        return (y + 2000 if y < 100 else y, int(qq))
    except (ValueError, AttributeError, TypeError):
        return None


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def lnst_yoy(bc: dict | None, quy: str) -> float | None:
    """% LNST công ty mẹ của `quy` so cùng kỳ, từ bảng quý của bctc.phan_tich."""
    b = {x.get('q'): x for x in (bc or {}).get('quy') or []}
    k = _qk(quy)
    if not k or quy not in b:
        return None
    q0 = f'Q{k[1]}/{str(k[0] - 1)[2:]}'
    a, c = _num(b[quy].get('lnst_me')), _num((b.get(q0) or {}).get('lnst_me'))
    if a is None or c is None or c <= 0:
        return None
    return round((a / c - 1) * 100, 1)


def _loi_doi_chieu(bc: dict | None, quy: str) -> bool:
    b = {x.get('q'): x for x in (bc or {}).get('quy') or []}
    k = _qk(quy)
    if not k or quy not in b:
        return False
    q0 = f'Q{k[1]}/{str(k[0] - 1)[2:]}'
    a, c = _num(b[quy].get('loi')), _num((b.get(q0) or {}).get('loi'))
    return a is not None and c is not None and c > 0 and a < 0


def cham_moc(k: dict, bc: dict | None) -> dict | None:
    """Chấm một mốc kiểm chứng cơ bản bằng số quý mới (chỉ tiêu 'ny' = LNST so cùng kỳ). None = chưa chấm được."""
    if k.get('loai') != 'funda' or k.get('chi_tieu') != 'ny':
        return None
    v = lnst_yoy(bc, k.get('quy'))
    if v is None:
        return None
    ng = float(k.get('nguong') or 0)
    ok = v >= ng if k.get('so_sanh', '>=') == '>=' else v <= ng
    return dict(id=k.get('id'), quy=k.get('quy'), gia_tri=v, ket_qua='ĐÚNG' if ok else 'SAI')


def xet(t: dict, bc: dict | None, dk: dict | None, quy_moi: str | None = None) -> dict:
    """t = luận điểm; bc = bctc.phan_tich của mã; dk = bon_dieu_kien hiện tại; quy_moi = quý mới nhất nếu không có bc.
    → dict(trang_thai='khop'|'tu_gia_han'|'can_review', quy_ld, quy_moi, ly_do=[…], moc=[…], so_moi=[câu…])."""
    q_ld = t.get('quy_bctc')
    q_moi = (bc or {}).get('moi_nhat') or quy_moi
    a, b = _qk(q_ld), _qk(q_moi)
    out = dict(quy_ld=q_ld, quy_moi=q_moi, ly_do=[], moc=[], so_moi=[])
    if not b or (a and b <= a):
        return dict(out, trang_thai='khop')
    ly = out['ly_do']
    for k in t.get('kiem_chung') or []:
        if _qk(k.get('quy')) and a and _qk(k['quy']) > a and _qk(k['quy']) <= b:
            m = cham_moc(k, bc)
            if m:
                out['moc'].append(m)
                if m['ket_qua'] == 'SAI':
                    ly.append(f"mốc {m['id']} {m['quy']} SAI (LNST {m['gia_tri']:+.1f}% so cùng kỳ)")
    g = lnst_yoy(bc, q_moi)
    if g is not None and g <= GIAM_MANH:
        ly.append(f'LNST {q_moi} {g:+.1f}% so cùng kỳ')
    if _loi_doi_chieu(bc, q_moi):
        ly.append(f'lợi nhuận kinh doanh cốt lõi {q_moi} chuyển âm')
    cu = t.get('dk_luc_viet') or {}
    for k in 'abcd':
        v0, v1 = cu.get(k), ((dk or {}).get(k) or {}).get('dat')
        if v0 is True and v1 is False:
            ly.append(f'điều kiện {k} đạt lúc viết, nay trượt')
        elif v0 is False and v1 is True:
            ly.append(f'điều kiện {k} trượt lúc viết, nay đạt — cơ hội, cần xem lại kết luận')
    out['so_moi'] = list((bc or {}).get('cau_chuyen') or [])[:4]
    out['lnst_yoy'] = g
    out['trang_thai'] = 'can_review' if ly else 'tu_gia_han'
    return out


def hang_review(ket: dict[str, dict]) -> dict:
    """Gộp kết quả xet() của mọi mã thành hàng review của quý (một lần/quý)."""
    can = sorted((dict(ma=s, **x) for s, x in ket.items() if x.get('trang_thai') == 'can_review'), key=lambda x: x['ma'])
    gh = sorted(s for s, x in ket.items() if x.get('trang_thai') == 'tu_gia_han')
    qs = [x.get('quy_moi') for x in ket.values() if x.get('quy_moi')]
    return dict(quy=max(qs, key=lambda q: _qk(q) or (0, 0)) if qs else None, can_review=can, tu_gia_han=gh,
                khop=sorted(s for s, x in ket.items() if x.get('trang_thai') == 'khop'))
