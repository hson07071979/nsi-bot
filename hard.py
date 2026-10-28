# -*- coding: utf-8 -*-
"""LỆNH HARD — anh Sơn chủ động mua / bán trên DANH MỤC HỆ THỐNG, không chờ tín hiệu bot.

Anh Sơn chốt 27–28/10/2026:
  * Bấm ở trang quản trị (Sổ tay) → ghi thẳng `manual.json` → khoá `hard` (không file nào khác).
  * Tác động lên chính sổ của bộ máy (engine2, NAV 1 tỷ từ 2019) VÀ sổ ghi tiến (portfolio.py).
  * Hard Buy: anh nhập % NAV + giá; vẫn bị chặn bởi trần mỗi mã, trần tổng vốn, trần ngành,
    tiền mặt, số mã tối đa. Mua thêm mã đang cầm thì tính lại giá vốn bình quân.
    Sau khi mua, bot quản lý điểm bán như lệnh thường; anh vẫn Hard Sell được bất cứ lúc nào.
  * Hard Sell: anh chọn 25/50/100% vị thế + nhập giá. Làm tròn xuống lô 100 cp; phần còn lại
    dưới 100 cp thì bán hết. Hàng chưa về (T+sell_from) thì không bán được.
    Bán xong bot vẫn được mua lại mã đó khi có tín hiệu.
  * Giá anh điền phải nằm trong biên độ trần/sàn của phiên. Phí như lệnh thường (0,15% / 0,25%).
  * Lệnh bấm sau giờ đóng cửa tính vào phiên hôm đó (trang tự gán `ngay`).
  * Hoàn tác (`huy`) được cho tới khi bản dựng tối đã xử lý lệnh (id nằm trong thresholds.hard.seen).
  * Lệnh Hard tính chung NAV / lịch sử lệnh / win rate / PF, có nhãn "Hard".

Khuôn một lệnh trong manual.json -> hard:
  {"id": "H20261028T153012-HPG", "loai": "mua" | "ban", "sym": "HPG",
   "ngay": "2026-10-28",            phiên của lệnh (YYYY-MM-DD)
   "gia": 26.55,                    giá khớp, NGHÌN đồng, giá thô
   "pct_nav": 10,                   (mua) % NAV muốn mua, trên NAV hiện tại của sổ
   "phan": 0.5,                     (bán) 0.25 / 0.5 / 1
   "tran": 28.4, "san": 24.7,       biên độ phiên trang đã kiểm lúc bấm (nghìn đồng)
   "luc": "2026-10-28T15:30:12+07:00", "ghi_chu": "", "huy": null | "<lúc hoàn tác>"}

File này thuần Python (không numpy) để engine2, produce2, publish và lớp kiểm tra cùng dùng.
"""
import json
import os
import re

NGUON = ('data/manual.json', 'manual.json')
PHAN_HOP_LE = (0.25, 0.5, 1.0)
LY_DO_BAN = 'Hard Sell — anh Sơn bán chủ động'


def _so(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if x == x and x not in (float('inf'), float('-inf')) else None


def chuan(o):
    """Một lệnh thô -> dict chuẩn, hoặc (None, lý do) nếu hỏng khuôn."""
    if not isinstance(o, dict):
        return None, 'không phải object'
    oid = str(o.get('id') or '').strip()
    if not oid or len(oid) > 80:
        return None, 'thiếu id'
    loai = str(o.get('loai') or '').strip().lower()
    if loai not in ('mua', 'ban'):
        return None, f'{oid}: loai phải là mua/ban'
    sym = str(o.get('sym') or '').strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{3,10}', sym):
        return None, f'{oid}: mã không hợp lệ'
    ngay = str(o.get('ngay') or '').strip()[:10]
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', ngay):
        return None, f'{oid}: ngày không hợp lệ'
    gia = _so(o.get('gia'))
    if gia is None or gia <= 0 or gia > 10000:
        return None, f'{oid}: giá không hợp lệ'
    out = dict(id=oid, loai=loai, sym=sym, ngay=ngay, gia=round(gia, 4),
               luc=str(o.get('luc') or ''), ghi_chu=str(o.get('ghi_chu') or '')[:300],
               huy=(str(o['huy']) if o.get('huy') else None),
               tran=_so(o.get('tran')), san=_so(o.get('san')))
    if loai == 'mua':
        pct = _so(o.get('pct_nav'))
        if pct is None or not (0 < pct <= 100):
            return None, f'{oid}: % NAV phải trong (0, 100]'
        out['pct_nav'] = round(pct, 4)
    else:
        ph = _so(o.get('phan'))
        if ph is None or min(abs(ph - x) for x in PHAN_HOP_LE) > 1e-9:
            return None, f'{oid}: phần bán phải là 25/50/100%'
        out['phan'] = float(ph)
    return out, None


def doc_tho(path=None):
    """manual.json -> danh sách lệnh thô (kể cả đã huỷ). Không có file / hỏng -> []."""
    for p in ([path] if path else NGUON):
        if p and os.path.exists(p):
            try:
                M = json.load(open(p, encoding='utf-8'))
            except Exception:
                return []
            h = M.get('hard') if isinstance(M, dict) else None
            return h if isinstance(h, list) else []
    return []


def doc(path=None, ke_ca_huy=False):
    """Lệnh hợp lệ, chưa huỷ (mặc định), xếp theo (ngày, lúc, id). Trả (lệnh, lỗi khuôn)."""
    ok, loi, seen = [], [], set()
    for o in doc_tho(path):
        x, e = chuan(o)
        if x is None:
            loi.append(e)
            continue
        if x['id'] in seen:
            loi.append(f"{x['id']}: id trùng — bỏ lệnh sau")
            continue
        seen.add(x['id'])
        if x['huy'] and not ke_ca_huy:
            continue
        ok.append(x)
    ok.sort(key=lambda x: (x['ngay'], x['luc'], x['id']))
    return ok, loi


def bien_do(san_giao_dich):
    """Biên độ dao động giá trong phiên theo sàn (HOSE 7%, HNX 10%, UPCoM 15%)."""
    e = str(san_giao_dich or 'HOSE').upper()
    return {'HOSE': 0.07, 'HSX': 0.07, 'HNX': 0.10, 'UPCOM': 0.15}.get(e, 0.07)


def trong_bien_do(gia, tran, san, eps=1e-6):
    return (san - eps) <= gia <= (tran + eps)
