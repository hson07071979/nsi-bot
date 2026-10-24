# -*- coding: utf-8 -*-
"""Tự đổi trọng số khi mô hình qua bài thi (anh Sơn chốt 24/10/2026: "tự đổi, báo chuông").

Dùng chung cho hai vòng học của Lọc port:
  · nhận định hằng ngày (nhan_dinh.hoc → state/trong_so_tu_hoc.json)
  · thang điểm pool tuần (pool_hoc.hoc → state/thang_pool.json)

Bài thi do từng vòng tự chấm (đi tiến theo năm, chỉ chấm trên năm mô hình CHƯA THẤY):
  thắng bộ đang dùng ở ≥ 2/3 số năm  +  IC trung bình cao hơn và dương  +  t ≥ 2.
Qua bài thi thì file này:
  1. ghi bộ mới vào state (bộ cũ giữ trong sổ lịch sử để quay lại được),
  2. gửi chuông ntfy/Telegram,
  3. không đổi tiếp trong GIAN_CACH_NGAY ngày — tránh nhảy trọng số mỗi tối vì nhiễu.
Quay lại bộ cũ: nhắn Claude, hoặc xóa file state tương ứng trên nhánh port-data.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import nhac as NH

GIAN_CACH_NGAY = 28          # ít nhất ~20 phiên giữa hai lần tự đổi


def _rj(p: Path, default):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def _wj(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def doc(state: Path, ten: str):
    """Bộ đã tự đổi gần nhất (dict) hoặc None."""
    x = _rj(state / f'{ten}.json', None)
    return x if isinstance(x, dict) and x else None


def lich_su(state: Path, ten: str) -> list[dict]:
    return _rj(state / f'lich_su_{ten}.json', []) or []


def con_cho(state: Path, ten: str, asof: str) -> int:
    """Số ngày còn phải chờ trước khi được tự đổi tiếp (0 = được đổi)."""
    ls = lich_su(state, ten)
    if not ls:
        return 0
    try:
        da = (date.fromisoformat(asof) - date.fromisoformat(ls[-1]['ngay_ap'])).days
    except (KeyError, ValueError):
        return 0
    return max(0, GIAN_CACH_NGAY - da)


def ap_dung(state: Path, ten: str, bo_moi: dict, bo_cu: dict | None, asof: str, tieu_de: str, noi_dung: str,
            bang_chung: dict | None = None, gui_chuong: bool = True) -> dict | None:
    """Ghi bộ mới nếu đã qua thời gian chờ. Trả về dòng lịch sử vừa ghi, hoặc None nếu chưa được đổi."""
    if con_cho(state, ten, asof):
        return None
    dong = dict(ngay_ap=asof, moi=bo_moi, cu=bo_cu, bang_chung=bang_chung or {}, ly_do=noi_dung)
    _wj(state / f'{ten}.json', dict(bo_moi, ngay_ap=asof))
    ls = lich_su(state, ten)
    ls.append(dong)
    _wj(state / f'lich_su_{ten}.json', ls[-50:])
    if gui_chuong:
        NH.gui(tieu_de, noi_dung + '\nMở /port để xem. Muốn quay lại bộ cũ: nhắn Claude.')
    return dong
