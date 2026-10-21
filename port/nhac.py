# -*- coding: utf-8 -*-
"""Nhắc anh Sơn review port khi nguyensonfinance có BCTC quý mới (anh Sơn 22/10/2026).

Review định kỳ 1 lần/quý, ngay sau mùa BCTC. Code theo dõi quý mà trang nguyensonfinance đang dùng cho từng mã của
port (D.funda[mã].q[-1]). Mã nào sang quý mới → chuông "MÃ có BCTC Qx — review luận điểm". Khi mọi mã trong port và
hàng chờ đều đã sang quý mới → chuông "đủ số cả port — đến kỳ review quý". Ngoài lịch, các cờ của sổ giả lập
(lỗ 10%, thủng hỗ trợ) cũng báo một lần.

Kênh: secret NTFY_TOPIC (và TELEGRAM_TOKEN/TELEGRAM_CHAT nếu có) — cùng kênh với chuông của bot.
"""
from __future__ import annotations

import json
import os
import urllib.request


def gui(tieu_de: str, noi_dung: str) -> bool:
    ok = False
    topic = os.environ.get('NTFY_TOPIC', '').strip()
    if topic:
        try:
            body = json.dumps({'topic': topic, 'title': tieu_de[:200], 'message': noi_dung[:3900],
                               'priority': 3, 'tags': ['memo']}).encode('utf-8')
            h = {'Content-Type': 'application/json'}
            if os.environ.get('NTFY_TOKEN', '').strip():
                h['Authorization'] = 'Bearer ' + os.environ['NTFY_TOKEN'].strip()
            req = urllib.request.Request(os.environ.get('NTFY_URL', 'https://ntfy.sh').rstrip('/'), data=body, headers=h)
            urllib.request.urlopen(req, timeout=20)
            ok = True
        except Exception as e:  # noqa: BLE001 — chuông hỏng không được làm hỏng lượt chạy
            print('ntfy lỗi:', type(e).__name__, e)
    tok, chat = os.environ.get('TELEGRAM_TOKEN', '').strip(), os.environ.get('TELEGRAM_CHAT', '').strip()
    if tok and chat:
        try:
            body = json.dumps(dict(chat_id=chat, text=f'{tieu_de}\n{noi_dung}')).encode('utf-8')
            req = urllib.request.Request(f'https://api.telegram.org/bot{tok}/sendMessage', data=body,
                                         headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=20)
            ok = True
        except Exception as e:  # noqa: BLE001
            print('telegram lỗi:', type(e).__name__, e)
    return ok


def _q_key(q: str):
    try:
        qq, yy = q[1:].split('/')
        return int(yy), int(qq)
    except (ValueError, AttributeError):
        return (0, 0)


def kiem(D: dict, luan: dict[str, dict], st: dict, co_gia_lap: list[dict] | None = None, gui_that: bool = True) -> dict:
    """st = trạng thái đã báo {'quy': {ma: q}, 'ky_review': q, 'co': [id]}. Trả về st mới + danh sách tin đã gửi."""
    st = dict(quy=dict(st.get('quy') or {}), ky_review=st.get('ky_review'), co=list(st.get('co') or []))
    fu = D.get('funda') or {}
    theo_doi = sorted(s for s, t in luan.items() if t.get('trang_thai') in ('trong_port', 'nghien_cuu'))
    tin = []
    moi = []
    for s in theo_doi:
        q = ((fu.get(s) or {}).get('q') or [None])[-1]
        if not q:
            continue
        cu = st['quy'].get(s)
        if cu and _q_key(q) > _q_key(cu):
            moi.append((s, q))
        st['quy'][s] = q if not cu or _q_key(q) > _q_key(cu) else cu
    for s, q in moi:
        tt = luan[s].get('trang_thai')
        tin.append((f'{s} có BCTC {q}',
                    f"nguyensonfinance đã có số {q} của {s} ({'đang trong port' if tt == 'trong_port' else 'hàng chờ'}). "
                    'Review luận điểm: phép thử quý, mốc cơ bản, mục tiêu T1/T2. Mở /port → Đọc BCTC.'))
    qs = [st['quy'].get(s) for s in theo_doi if st['quy'].get(s)]
    if qs and len(qs) == len(theo_doi):
        thap = min(qs, key=_q_key)
        if not st['ky_review'] or _q_key(thap) > _q_key(st['ky_review']):
            if st['ky_review']:          # lần chạy đầu chỉ ghi mốc, không báo
                tin.append((f'Đến kỳ review port {thap}',
                            f'Cả {len(theo_doi)} mã trong port và hàng chờ đã có BCTC {thap}. Đến kỳ review quý.'))
            st['ky_review'] = thap
    for c in co_gia_lap or []:
        k = f"{c['ma']}-{c['loai']}-{c['ngay']}"
        if k in st['co']:
            continue
        st['co'].append(k)
        tin.append((f"Cờ review {c['ma']}", c['noi_dung']))
    st['co'] = st['co'][-200:]
    da_gui = []
    for tieu_de, nd in tin:
        if gui_that:
            gui(tieu_de, nd)
        da_gui.append(dict(tieu_de=tieu_de, noi_dung=nd))
    st['lan_cuoi'] = da_gui
    return st
