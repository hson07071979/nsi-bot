# -*- coding: utf-8 -*-
"""BAO ANH SON KHI TRANG DUNG (11/10/2026). Khong doi luat gi — chi bao.

Chay o buoc cuoi cua daily.yml khi day chuyen hong. Neu trang dang dang con o phien cu va
da qua >= 10 tieng sau dong cua phien moi nhat, gui chuong (ntfy, cung kenh voi live_scan.py)
kem ly do truot (data/verify_ketqua.json) va duong toi nut vuot. Luot 21:00 cung ngay phien
(6 tieng) KHONG bao: nguon co the chi cham. Luot du phong 01:23 (~10,4 tieng) bao.

Kenh: secret NTFY_TOPIC (va TELEGRAM_TOKEN/TELEGRAM_CHAT neu co) trong repo nsi-bot. Chua cai
thi chi in ::error:: (GitHub van gui email "workflow failed").
"""
import datetime as dt, json, os, urllib.request

NGUONG_GIO = 10


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json',
                                               'Referer': 'https://fireant.vn/'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def phien_moi_nhat(now):
    try:
        import numpy as np
        return str(np.load('data/fa.npz', allow_pickle=True)['cal'][-1])[:10]
    except Exception:
        pass
    frm = (now.date() - dt.timedelta(days=12)).isoformat()
    for sym in ('VCB', 'HPG', 'FPT'):
        try:
            rows = _get('https://www.fireant.vn/api/Data/Companies/HistoricalQuotes'
                        f'?symbol={sym}&startDate={frm}&endDate={now.date().isoformat()}')
            if rows:
                return max(str(r.get('Date', ''))[:10] for r in rows)
        except Exception:
            pass
    return ''


def gui(tieu_de, noi_dung):
    ok = False
    topic = os.environ.get('NTFY_TOPIC', '').strip()
    if topic:
        try:
            body = json.dumps({'topic': topic, 'title': tieu_de[:200], 'message': noi_dung[:3900],
                               'priority': 4, 'tags': ['warning']}).encode()
            req = urllib.request.Request(os.environ.get('NTFY_URL', 'https://ntfy.sh').rstrip('/'), data=body,
                                         headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=20); ok = True; print('ntfy: da gui')
        except Exception as e:
            print('ntfy loi:', type(e).__name__, e)
    tok, chat = os.environ.get('TELEGRAM_TOKEN', '').strip(), os.environ.get('TELEGRAM_CHAT', '').strip()
    if tok and chat:
        try:
            body = json.dumps({'chat_id': chat, 'text': tieu_de + '\n' + noi_dung,
                               'disable_web_page_preview': True}).encode()
            req = urllib.request.Request(f'https://api.telegram.org/bot{tok}/sendMessage', data=body,
                                         headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=20); ok = True; print('telegram: da gui')
        except Exception as e:
            print('telegram loi:', type(e).__name__, e)
    return ok


def main():
    now = dt.datetime.utcnow() + dt.timedelta(hours=7)
    phien = phien_moi_nhat(now)
    asof = ''
    try:
        asof = str(_get('https://raw.githubusercontent.com/'
                        f'{os.environ["CHU"]}/{os.environ["REPO"]}/main/thresholds.json').get('asof') or '')
    except Exception as e:
        print('khong doc duoc thresholds.json:', e)
    print(f'phien moi nhat {phien or "?"} | trang dang dung {asof or "?"}')
    if not phien or (asof and asof >= phien):
        print('trang khong dung sau phien moi nhat — khong bao'); return
    gio = (now - dt.datetime.fromisoformat(phien + 'T15:00:00')).total_seconds() / 3600
    if gio < NGUONG_GIO:
        print(f'moi {gio:.1f} tieng sau dong cua (< {NGUONG_GIO}) — nguon co the chi cham, chua bao'); return
    try:
        kq = json.load(open('data/verify_ketqua.json', encoding='utf-8'))
        ly_do = kq.get('fail') or []
    except Exception:
        ly_do = []
    vuot = any('dong tien phien cuoi' in x for x in ly_do)
    run = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ.get('GITHUB_REPOSITORY', '')}" \
          f"/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
    tieu_de = f'Trang đang đứng ở phiên {asof or "?"} — phiên {phien} chưa đăng ({gio:.0f} giờ)'
    noi = ('Lý do:\n' + '\n'.join('• ' + x for x in ly_do[:4]) if ly_do
           else 'Dây chuyền hỏng trước bước kiểm tra — xem log.')
    if vuot:
        noi += ('\n\nNếu nguồn KHÔNG có số phiên này (không phải chậm): trang quản trị → Chẩn đoán → '
                '"Cổng dòng tiền — nút vượt". Anh quyết, bot không tự vượt.')
    noi += f'\n\n{run}'
    print('::error::' + tieu_de)
    print(noi)
    if not gui(tieu_de, noi):
        print('::warning::Chưa cài chuông: thêm secret NTFY_TOPIC (cùng topic với repo trang) vào repo nsi-bot.')


if __name__ == '__main__':
    main()
