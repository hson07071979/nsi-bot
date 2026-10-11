# -*- coding: utf-8 -*-
"""NUT VUOT CONG DONG TIEN — do anh Son bam, dung MOT phien, MOT san (11/10/2026).

Cong "dong tien phien cuoi >= 80% ma thanh khoan" (verify_build.py muc 8c-d) giu NGUYEN mac
dinh. Khi nguon (FireAnt + hnx.vn) khong co so cua mot phien, anh Son quyet tung lan o trang
Chan doan (quan tri): nut ghi override.json len repo trang, dang

  {"bo_qua_dong_tien": [{"san": "HNX", "phien": "2026-10-09", "luc": "...", "ghi_chu": "..."}]}

Bot chi doi chan -> canh bao khi san VA phien KHOP DUNG phien dang dung (asof). Phien khac,
san khac, file hong / thieu -> van chan. Khong bao gio dien so 0: san do khong co tin hieu
MUA phien do (dieu kien 9 truot), trang hien dong canh bao cho khach.
"""
import json

FILE = 'data/override.json'
SAN = ('HOSE', 'HNX')


def doc(path=FILE):
    try:
        o = json.load(open(path, encoding='utf-8'))
        ds = o.get('bo_qua_dong_tien') if isinstance(o, dict) else None
        return [x for x in ds if isinstance(x, dict)] if isinstance(ds, list) else []
    except Exception:
        return []


def khop(san, phien, path=FILE):
    """Muc vuot dung san + dung phien, hoac None."""
    if not phien or san not in SAN:
        return None
    for x in doc(path):
        if str(x.get('san', '')).upper() == san and str(x.get('phien', '')) == str(phien):
            return x
    return None


def dang_vuot(phien, path=FILE):
    """Cac san dang duoc vuot cho phien nay (de trang hien canh bao)."""
    return [s for s in SAN if khop(s, phien, path)]
