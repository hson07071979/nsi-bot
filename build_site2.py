# -*- coding: utf-8 -*-
"""DUNG TRANG WEB — gop du lieu + khuon + ma JavaScript thanh mot file index.html.

Ngoai du lieu backtest, trang con NHUNG SAN mot anh chup cua ba file song:
  data/portfolio.json  so lenh may chu tu ghi
  data/manual.json     so tay anh Son da dang
  data/config.json     dia chi cau noi real-time
Nho vay mo file bang duong dan file:// tren may van thay danh muc, thay vi mot
trang trong khong. Khi chay tren web that thi lop truc tiep tai lai ban moi hon
va de len anh chup nay.
"""
import json

data = json.load(open('data/site_data2.json'))

try:
    data['live'] = json.load(open('data/live_scan.json'))
except Exception:
    data['live'] = {'hits': [], 'asof': '', 'scanned': 0, 'universe': 0}

# --- cac khoi du lieu roi, nhung san lam anh chup du phong ---
# funda_series.json = chuoi 12 quy cua tung ma, cho trang Chi tiet ma. 0,5 MB —
# nhung thang vao trang thay vi tai rieng thi mo bang file tren may van xem duoc.
for khoa, duong in (('portfolio', 'data/portfolio.json'),
                    ('manual',    'data/manual.json'),
                    ('config',    'data/config.json'),
                    ('funda',     'data/funda_series.json'),
                    ('robust',    'data/robust.json'),
                    ('congb',     'data/cong_b.json'),
                    ('data_health', 'data/data_health.json'),
                    ('audit',     'evidence/audit_summary.json')):
    try:
        data[khoa] = json.load(open(duong, encoding='utf-8'))
    except Exception:
        data[khoa] = None

# p7.js phai o CUOI: no chay bo dieu huong, doi moi ham trang da khai bao xong.
# p12.js khai bao mo hinh du lieu chung nen phai dung truoc p7.
js = ''.join(open(f'site/{p}', encoding='utf-8').read() for p in [
    'part2.js', 'p3.js', 'p4.js', 'p5.js', 'part6.js',
    'p8.js', 'p9.js', 'p10.js', 'p11.js', 'p12.js',
    # p13 = lop real-time VPS (ghi de napRealtime cua p11 -> phai SAU p11)
    # p14 = trang Kiem dinh (khai bao pageKiemDinh, duoc p3 tham chieu — ham
    #       khai bao duoc keo len dau pham vi nen dat sau van chay dung)
    'p13.js', 'p14.js',
    # p15 = kien truc thong tin huong khach hang (pageHomNay/pageCoHoi/pageHieuQua)
    'p15.js',
    # p16 = trang So sanh trong nganh (pageNganh). Phai sau p9 vi dung `so` va
    #       `_cpId` khai bao o do; truoc p7 vi p7 chay bo dieu huong ngay khi nap.
    'p16.js',
    # p18 = trang Chan doan & kiem toan (audit 23/09/2026), truoc p7.
    'p18.js',
    'p7.js',
    # p17 = lop dien thoai + cai thanh app (service worker, thanh dieu huong duoi).
    #       Day la file DUY NHAT duoc nam SAU p7.js: no DOC `secs` va `go` ma p7
    #       khai bao, va chi them giao dien chu khong dinh nghia trang nao — nen
    #       dat sau khong pha thu tu. Dung them file nao khac vao sau p7.
    'p17.js'])

html = open('site/part1.html', encoding='utf-8').read()
# CHAN NaN/Infinity: Python ghi ra duoc, JSON.parse cua trinh duyet thi KHONG
# -> mot o NaN lam ca trang trang. Doi het thanh null truoc khi nhung vao trang.
data = json.loads(json.dumps(data), parse_constant=lambda c: None)

html = html.replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))

# Thu vien bieu do nen (Lightweight Charts cua TradingView, Apache 2.0) duoc NHUNG
# THANG vao trang chu khong tai tu CDN. Ly do: trang nay la mot file duy nhat, anh
# Son van mo bang duong dan tren may. Tai tu CDN thi mo offline la bieu do trang.
try:
    lwc = open('vendor/lwc.js', encoding='utf-8').read()
    html += '<script>' + lwc.replace('</', '<\\/') + '</script>\n'
    print('nhung thu vien bieu do', round(len(lwc) / 1024), 'KB')
except FileNotFoundError:
    print('CANH BAO: thieu vendor/lwc.js — trang Chi tiet ma se khong ve duoc bieu do')

html += '<script>' + js + "\n</script>\n</body>\n</html>\n"
open('site/index.html', 'w', encoding='utf-8').write(html)
print('bytes', len(html))
