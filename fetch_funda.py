# -*- coding: utf-8 -*-
"""Cao bao cao tai chinh tu Vietcap IQ.

⚠️ LOI DA SUA (20/08/2026) — ban cu KHONG CO THU LAI. Mot loi mang thoang qua
(`ConnectionResetError`) la ca ma do mat sach bao cao ket qua kinh doanh, roi
`rev_yoy` / `npat_yoy` / `cagr3` deu thanh None, keo C1 + C2 + C3 + A1 ve 0 —
tuc mat 45 diem CANSLIM — ma khong bao gi ca.

Do thuc te: 41/694 ma bi dinh, trong do co BID, HPG, VCI, LPB, GEX, IDC.
LPB thang 4/2026 chi duoc 44,5 diem, truot san 45 dung 0,5 diem — chinh vi mat
30 diem tang truong nay. Cao lai lan hai thi ra du 34 quy, chung to du lieu van
co, chi la loi mang.

Nay: thu lai 4 lan cho tung phan, va CHAN chuong trinh neu ty le thieu qua cao.
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

H = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
B = 'https://iq.vietcap.com.vn/api/iq-insight-service/v1/company/'
TRIES = 4


def _get(url, params=None):
    """GET co thu lai. Tra ve JSON, hoac None neu that bai het cac lan."""
    for a in range(TRIES):
        try:
            r = requests.get(url, headers=H, params=params, timeout=45)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (404, 400):
                return None          # ma nay that su khong co, khoi thu lai
        except Exception:
            pass
        time.sleep(1.5 * (a + 1))
    return None


def one(sym):
    out = {}
    j = _get(B + sym + '/statistics-financial')
    out['ratio'] = (j or {}).get('data') or []
    for sec, key in [('INCOME_STATEMENT', 'is'), ('CASH_FLOW', 'cf')]:
        j = _get(B + sym + '/financial-statement', {'section': sec})
        out[key] = ((j or {}).get('data') or {}).get('quarters') or []
    return sym, out


if __name__ == '__main__':
    u = json.load(open('data/universe.json'))
    print('n', len(u), flush=True)
    res = {}
    with ThreadPoolExecutor(8) as ex:
        for i, (s, d) in enumerate(ex.map(one, u)):
            res[s] = d
            if i % 50 == 0:
                print(i, s, len(d['ratio']), len(d['is']), len(d['cf']), flush=True)
    json.dump(res, open('data/funda_raw2.json', 'w'))

    # ---- chot chan: thieu bao nhieu ma? ----
    no_is = [s for s, v in res.items() if not v['is']]
    no_ra = [s for s, v in res.items() if not v['ratio']]
    print(f'\nxong {len(res)} ma')
    print(f'  thieu bao cao KQKD : {len(no_is)} ma ({len(no_is)/len(res):.1%})')
    print(f'  thieu chi so ty le : {len(no_ra)} ma ({len(no_ra)/len(res):.1%})')
    if no_is:
        print('   ', ' '.join(sorted(no_is)[:40]))

    # Mot so ma moi len san that su chua co du bao cao — chap nhan duoi 3%.
    # Vuot nguong do thi gan nhu chac chan la loi mang, dung dung du lieu do de
    # chay backtest hay chap diem.
    if len(no_is) > 0.03 * len(res):
        sys.exit(f'HONG: {len(no_is)} ma thieu bao cao KQKD — nghi loi mang, '
                 f'chay lai truoc khi dung du lieu nay')
