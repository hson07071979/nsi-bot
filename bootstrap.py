# -*- coding: utf-8 -*-
"""KHOI TAO — chay tren mot may hoan toan trong, truoc moi thu khac.

Sinh 5 file ma cac buoc sau can:
  data/by_exchange.csv   danh sach ma + san + ten cong ty   (vnstock/VCI)
  industries.csv         nganh ICB tung ma                  (vnstock/VCI)
  data/sector2.json      {ma: ten nganh cap 2}
  data/universe.json     danh sach ma HOSE + HNX
  data/VNINDEX.json      nen ngay VN-Index tu 2017          (DNSE)

Chay: python3 bootstrap.py
"""
import json
import os
import sys
import time
import datetime as dt


def patch_vnstock():
    """vnstock loi UnboundLocalError: hosting_service khi chay tren may chu.
    Va truoc khi import, khong thi moi lenh Listing() deu no."""
    try:
        import vnstock.core.utils.env as env
    except Exception:
        return False
    p = env.__file__
    src = open(p, encoding='utf-8').read()
    if 'hosting_service = "Local or Unknown"' in src:
        return True
    marker = 'def get_hosting_service('
    if marker not in src:
        return False
    i = src.index(marker)
    j = src.index('try:', i)
    indent = ' ' * (len(src[:j].split('\n')[-1]))
    src = src[:j] + 'hosting_service = "Local or Unknown"\n' + indent + src[j:]
    open(p, 'w', encoding='utf-8').write(src)
    print('  đã vá vnstock env.py')
    # nap lai module cho lan import sau
    import importlib
    importlib.reload(env)
    return True


def step_listing():
    from vnstock import Listing
    ls = Listing(source='VCI')
    ex = ls.symbols_by_exchange()
    ex.to_csv('data/by_exchange.csv', index=False)
    print(f'  data/by_exchange.csv — {len(ex)} dòng')

    ind = ls.symbols_by_industries()
    ind.to_csv('industries.csv', index=False)
    print(f'  industries.csv — {len(ind)} dòng')
    return ex, ind


def step_sector(ind):
    sect = {}
    for r in ind.itertuples():
        try:
            if int(getattr(r, 'icb_level', 0)) == 2:
                sect[str(r.symbol)] = str(getattr(r, 'icb_name', 'Khác'))
        except Exception:
            continue
    json.dump(sect, open('data/sector2.json', 'w'), ensure_ascii=False)
    print(f'  data/sector2.json — {len(sect)} mã có ngành')


def step_universe(ex):
    d = ex[(ex.type == 'STOCK') & (ex.exchange.isin(['HSX', 'HNX']))]
    syms = sorted({str(s) for s in d.symbol})
    json.dump(syms, open('data/universe.json', 'w'))
    print(f'  data/universe.json — {len(syms)} mã HOSE + HNX')


def step_vnindex():
    import requests
    to = int(time.time())
    url = ('https://api.dnse.com.vn/chart-api/v2/ohlcs/index'
           f'?symbol=VNINDEX&resolution=1D&from=1483228800&to={to}')
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=45)
            r.raise_for_status()
            j = r.json()
            out = {k: j[k] for k in ('t', 'o', 'h', 'l', 'c', 'v') if k in j}
            if not out.get('t'):
                raise ValueError('DNSE trả về rỗng')
            json.dump(out, open('data/VNINDEX.json', 'w'))
            last = dt.date.fromtimestamp(out['t'][-1]).isoformat()
            print(f"  data/VNINDEX.json — {len(out['t'])} phiên, gần nhất {last}")
            return
        except Exception as e:
            print(f'  DNSE lỗi lần {attempt+1}: {e}')
            time.sleep(5 * (attempt + 1))
    raise SystemExit('KHỞI TẠO HỎNG: không lấy được VN-Index từ DNSE')


if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    print('KHỞI TẠO — sinh các file tĩnh')
    if not patch_vnstock():
        print('  cảnh báo: không vá được vnstock, thử chạy tiếp')
    ex, ind = step_listing()
    step_sector(ind)
    step_universe(ex)
    step_vnindex()
    print('KHỞI TẠO XONG')
