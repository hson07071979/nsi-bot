# -*- coding: utf-8 -*-
"""Do nguon thu 3 cho dong tien HNX (tam, chi in ra). So voi hnx.vn tren cac phien cu."""
import json, sys, os, traceback, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sources import hnx
UA = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
SYMS = [('SHS', 'NY'), ('PVS', 'NY'), ('CEO', 'NY'), ('ACV', 'UC')]

def show(name, fn):
    print(f'\n===== {name}')
    try:
        r = fn(); t = r.text
        print('HTTP', r.status_code, r.headers.get('content-type'), len(t)); print(t[:1500])
    except Exception:
        traceback.print_exc()

for s, m in SYMS:
    try:
        st, rows, tot = hnx.cungcau(s, m, n=8)
        print(f'\n##### hnx.vn {s}: ' + json.dumps([{k: r[k] for k in ('date', 'BuyCount', 'BuyQuantity', 'SellCount', 'SellQuantity')} for r in rows]))
    except Exception:
        traceback.print_exc()
    show(f'SSI stock-info {s}', lambda: requests.get(
        'https://iboard-api.ssi.com.vn/statistics/company/ssmi/stock-info',
        params=dict(symbol=s, page=1, pageSize=8, fromDate='25/09/2026', toDate='10/10/2026'),
        headers={**UA, 'Origin': 'https://iboard.ssi.com.vn', 'Referer': 'https://iboard.ssi.com.vn/'}, timeout=30))
    show(f'VNDirect stock_prices {s}', lambda: requests.get(
        'https://api-finfo.vndirect.com.vn/v4/stock_prices',
        params=dict(sort='date', q=f'code:{s}~date:gte:2026-09-25', size=8), headers=UA, timeout=30))
    show(f'FireAnt {s}', lambda: requests.get(
        'https://www.fireant.vn/api/Data/Companies/HistoricalQuotes',
        params=dict(symbol=s, startDate='2026-10-06', endDate='2026-10-10'),
        headers={**UA, 'Referer': 'https://fireant.vn/'}, timeout=30))
