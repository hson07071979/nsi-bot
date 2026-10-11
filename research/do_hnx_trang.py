# -*- coding: utf-8 -*-
"""TAM. Do cac trang bao cao khac cua hnx.vn. Thu tu: (1) tim endpoint, (2) KIEM NGAY 09/10 TRUOC,
(3) chi in mau dong de nguoi doc xet co phai so THEO TUNG MA khong. Chua viet parser, chua doi chung."""
import re, sys, os, html
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sources import hnx
S = hnx.S; V = hnx._bundle()
urls = set()
for page in ('https://www.hnx.vn/cophieu-etfs/chi-tiet-chung-khoan-ny-shs.html',
             'https://www.hnx.vn/thong-tin-giao-dich/thong-ke-giao-dich.html',
             'https://www.hnx.vn/'):
    try:
        t = S.get(page, verify=V, timeout=60).text
        print(f'GET {page}: {len(t)} bytes')
        for js in set(re.findall(r'src="([^"]+\.js[^"]*)"', t)):
            if 'hnx' in js or js.startswith('/'):
                try: t += S.get(('https://www.hnx.vn' + js) if js.startswith('/') else js, verify=V, timeout=30).text
                except Exception: pass
        urls |= set(re.findall(r'(/Module\w+/[\w/]+(?:Datas|Data|Search)\w*)', t))
    except Exception as e:
        print('loi', page, e)
urls.discard('/ModuleIssuer/Report_NY/TK_CungCauListSearch_Datas')
print(f'\n{len(urls)} endpoint tim thay (tru TK_CungCau dang dung):')
for u in sorted(urls): print('  ', u)
P = {'p_issearch': 1, 'p_market': 'NY', 'p_symbol': 'SHS', 'p_keysearch': 'SHS', 'p_code': 'SHS',
     'p_orderby': '', 'p_ordertype': '', 'p_currentpage': 1, 'p_record_on_page': 10,
     'p_fromdate': '08/10/2026', 'p_todate': '09/10/2026', 'p_tradingdate': '09/10/2026'}
print('\n=== KIEM NGAY (buoc 3 truoc): endpoint nao tra ve chuoi 09/10/2026?')
for u in sorted(urls):
    try:
        r = S.post('https://www.hnx.vn' + u, data=P, verify=V, timeout=40,
                   headers={'Referer': 'https://www.hnx.vn/cophieu-etfs/chi-tiet-chung-khoan-ny-shs.html'})
        t = r.text; c9 = '09/10/2026' in t; c8 = '08/10/2026' in t
        print(f'{u}: HTTP {r.status_code} {len(t)}B  co 09/10={c9}  co 08/10={c8}  co SHS={"SHS" in t}')
        if c9:
            i = t.index('09/10/2026')
            print('   MAU:', re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' | ', t[max(0, i - 600):i + 900])))[:1200])
    except Exception as e:
        print(f'{u}: loi {e}')
