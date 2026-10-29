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


def kiem(D: dict, luan: dict[str, dict], st: dict, co_gia_lap: list[dict] | None = None, gui_that: bool = True,
         quy_live: dict[str, str] | None = None, review: dict | None = None) -> dict:
    """st = trạng thái đã báo {'quy': {ma: q}, 'ky_review': q, 'co': [id]}. Trả về st mới + danh sách tin đã gửi.
    quy_live = {mã: quý mới nhất đọc thẳng BCTC Vietcap} (29/10/2026: có số là dùng, không chờ trang 45 ngày).
    review = danh_sach.lap()['review_quy'] — báo MỘT lần mỗi quý danh sách mã máy thấy cần người review."""
    st = dict(quy=dict(st.get('quy') or {}), ky_review=st.get('ky_review'), co=list(st.get('co') or []),
              review_bao=dict(st.get('review_bao') or {}))
    fu = {s: {'q': [q]} for s, q in (quy_live or {}).items() if q} or (D.get('funda') or {})
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
    if len(moi) > 5:          # nhiều mã cùng sang quý (mùa BCTC) → gộp một tin, khỏi dội chuông
        tin.append((f'{len(moi)} mã có BCTC mới',
                    ', '.join(f'{s} {q}' for s, q in moi) + '. Máy tự xét từng luận điểm; mã cần anh xem sẽ có trong tin "Review quý".'))
        moi = []
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
    rv = review or {}
    can = [x['ma'] for x in rv.get('can_review') or []]
    if rv.get('quy') and can:
        moi_bao = sorted(set(can) - set(st['review_bao'].get(rv['quy']) or []))
        if moi_bao:
            tin.append((f"Review quý {rv['quy']}: {len(moi_bao)} mã",
                        'Máy đã tự cập nhật số quý mới; các mã sau có thay đổi cần anh xem lại luận điểm: ' +
                        '; '.join(f"{x['ma']} ({', '.join(x['ly_do'][:2])})" for x in rv['can_review'] if x['ma'] in moi_bao)
                        + f". Tự gia hạn (không cần làm gì): {len(rv.get('tu_gia_han') or [])} mã."))
            st['review_bao'][rv['quy']] = sorted(set(st['review_bao'].get(rv['quy']) or []) | set(moi_bao))
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
