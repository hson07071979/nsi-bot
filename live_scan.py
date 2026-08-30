# -*- coding: utf-8 -*-
"""BO QUET TRONG PHIEN — chay o repo public, moi 20 phut.

Doc `thresholds.json` (do repo private xuat ra moi toi), cao dong du lieu NGAY cua
tung ma tu FireAnt, so voi nguong, roi ghi `live.json` cho trang web doc.

File nay KHONG chua luat giao dich nao. No chi lam mot viec: so gia va khoi luong
hom nay voi hai con so da duoc tinh san. Toan bo he thong nam o repo private.

CANH BAO — dung dung `Markets/IntradayQuotes` de do khoi luong. Feed tick cua
FireAnt bi cat cut, cat nang nhat dung o nhom ma thanh khoan cao. Do thuc te phien
19/08/2026: TDM chi hien 0,4% khoi luong that, POW 13,1%, HDB 11,9%. Luon doc dong
du lieu NGAY (`Companies/HistoricalQuotes`) — no cong don dung trong phien.
"""
import datetime as dt
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36',
     'Referer': 'https://fireant.vn/', 'Accept': 'application/json'}
BASE = 'https://www.fireant.vn/api/Data'

# Duong cong khoi luong luy ke dien hinh cua mot phien HOSE/HNX (gio Viet Nam).
# 9h15 ATO · 9h15-11h30 khop lien tuc · nghi trua · 13h00-14h30 · 14h30-14h45 ATC.
# Ma trong watchlist tang tu muc nay tro len thi keo CHUONG VANG — chi de mat,
# KHONG phai lenh. Nguyen tac vao lenh khong doi mot chu.
DE_MAT_PCT = 2.5

VOL_CURVE = [(9.25, 0.02), (9.50, 0.10), (10.00, 0.24), (10.50, 0.34), (11.00, 0.44),
             (11.50, 0.55), (13.00, 0.55), (13.50, 0.67), (14.00, 0.79), (14.25, 0.86),
             (14.50, 0.92), (14.75, 1.00)]


def gio_vn():
    """Gio Viet Nam, KHONG phu thuoc mui gio may chay. May chu GitHub chay theo UTC."""
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).replace(tzinfo=None)
    except Exception:
        return dt.datetime.utcnow() + dt.timedelta(hours=7)


def clock_frac(now=None):
    """Phien da di duoc bao nhieu phan khoi luong, tinh theo dong ho."""
    now = now or gio_vn()
    if now.weekday() >= 5:
        return 1.0
    t = now.hour + now.minute / 60.0
    if t <= VOL_CURVE[0][0]:
        return 0.02
    if t >= VOL_CURVE[-1][0]:
        return 1.0
    for k in range(1, len(VOL_CURVE)):
        t0, f0 = VOL_CURVE[k - 1]
        t1, f1 = VOL_CURVE[k]
        if t <= t1:
            return f0 + (f1 - f0) * (t - t0) / max(t1 - t0, 1e-9)
    return 1.0


def latest_row(sym, frm, to):
    """Dong du lieu cua PHIEN GAN NHAT trong khoang [frm, to].

    Khong hoi cung mot ngay `today`: truoc 9h15, sau nua dem, hay ngay nghi le thi
    hom nay khong co phien nao ca. Hoi mot khoang vai ngay roi lay dong moi nhat thi
    luc nao cung co so de hien, va co `session` de biet do la phien nao.
    """
    for a in range(3):
        try:
            r = requests.get(BASE + '/Companies/HistoricalQuotes',
                             params={'symbol': sym, 'startDate': frm, 'endDate': to},
                             headers=H, timeout=40)
            d = r.json()
            if isinstance(d, list):
                if not d:
                    return None
                return max(d, key=lambda x: str(x.get('Date', '')))
        except Exception:
            time.sleep(1.2 * (a + 1))
    return None


def main():
    if not os.path.exists('thresholds.json'):
        sys.exit('HONG: khong co thresholds.json — repo private chua day sang')
    T = json.load(open('thresholds.json', encoding='utf-8'))
    syms = T['syms']

    now = gio_vn()
    today = now.date().isoformat()
    frm = (now.date() - dt.timedelta(days=7)).isoformat()
    frac = clock_frac(now)
    phien_mo = now.weekday() < 5 and 9.0 <= (now.hour + now.minute / 60) <= 15.1

    rows = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for s, r in zip(syms, ex.map(lambda s: latest_row(s, frm, today), syms)):
            if r:
                rows[s] = r

    if not rows:
        # thi truong nghi, hoac phien chua mo
        out = dict(asof=now.isoformat(timespec='seconds'), session=None,
                   open=False, frac=round(frac, 3), scanned=0,
                   base_session=T['asof'], hits=[],
                   note='Chưa lấy được dữ liệu từ FireAnt.')
        json.dump(out, open('live.json', 'w', encoding='utf-8'), ensure_ascii=False)
        print('khong co du lieu phien hom nay')
        return

    # ⚠️ Phai xac dinh phien TRUOC khi tinh du phong. Neu du lieu la cua phien DA DONG
    # ma van lay he so tien do theo dong ho hien tai (vi du 00h06 -> 2%) thi du phong
    # khoi luong bi phong dai 50 lan va moi ma deu trong nhu sap du dieu kien.
    from collections import Counter
    ses = Counter(str(r.get('Date', ''))[:10] for r in rows.values()).most_common(1)[0][0] or today
    if ses != today or not phien_mo:
        phien_mo = False
        frac = 1.0

    hits = []
    for s, r in rows.items():
        t = syms[s]
        try:
            close = float(r.get('PriceClose') or 0)
            basic = float(r.get('PriceBasic') or 0)
            vol = float(r.get('Volume') or 0)
            tv = float(r.get('TotalValue') or 0)
            hi = float(r.get('PriceHigh') or 0)
            lo = float(r.get('PriceLow') or 0)
        except Exception:
            continue
        if close <= 0 or basic <= 0:
            continue

        pct = close / basic - 1
        volr = vol / t['vma20'] if t['vma20'] else 0.0
        volr_proj = volr / frac if frac > 0 else volr
        tv_proj = tv / frac if frac > 0 else tv

        cond = {
            'Biên độ tăng giá': pct * 100 >= t['thr'],
            'Khối lượng ≥ 2× TB20': volr >= T['vol_floor'],
            'GTGD ≥ 15 tỷ': tv >= T['gtgd_min'],
            'Đóng cửa nửa trên nến': close >= (hi + lo) / 2 if hi > lo else True,
        }
        # ba dieu kien nay da chot tu toi qua, khong doi trong phien
        gate_ok = (t['state'] == 'cho')

        n_ok = sum(cond.values())
        fa_ok = (t['state'] == 'fa')      # qua het TRU diem — CHI DE MAT, khong duoc mua

        if gate_ok and all(cond.values()):
            lvl = 'MUA'                   # CHUONG DO — du 8 dieu kien, san sang vao lenh
        elif gate_ok and (n_ok >= 3 or (pct * 100 >= t['thr'] * 0.7 and volr_proj >= T['vol_floor'])):
            lvl = 'SAP_DU'
        elif (gate_ok or fa_ok) and pct * 100 >= DE_MAT_PCT:
            lvl = 'DE_MAT'                # CHUONG VANG — dang tang manh, chi de ngo chung
        elif gate_ok and (volr >= 1.5 or pct * 100 >= t['thr'] * 0.5):
            lvl = 'THEO_DOI'
        else:
            continue

        hits.append(dict(
            sym=s, name=t['name'], level=lvl, fa=fa_ok,
            fund=t.get('fund'),
            price=round(close / 1000, 2), ref=round(basic / 1000, 2),
            pct=round(pct * 100, 2), need_px=t['need_px'],
            volr=round(volr, 2), volr_proj=round(volr_proj, 2),
            need_vol=t['need_vol'], vol=int(vol),
            gtgd=round(tv / 1e9, 1), gtgd_proj=round(tv_proj / 1e9, 1),
            score=t['score'], base=t['base'],
            cond=cond,
            miss=[k for k, v in cond.items() if not v],
        ))

    order = {'MUA': 0, 'SAP_DU': 1, 'DE_MAT': 2, 'THEO_DOI': 3}
    hits.sort(key=lambda x: (order[x['level']], -x['pct']))

    out = dict(
        asof=now.isoformat(timespec='seconds'),
        session=ses,
        open=phien_mo,
        frac=round(frac, 3),
        scanned=len(rows),
        universe=len(syms),
        base_session=T['asof'],
        hits=hits,
        de_mat_pct=DE_MAT_PCT,
        n_mua=sum(1 for h in hits if h['level'] == 'MUA'),
        n_de_mat=sum(1 for h in hits if h['level'] == 'DE_MAT'),
    )
    json.dump(out, open('live.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(f"quét {len(rows)}/{len(syms)} mã · phiên {ses} · đã đi {frac*100:.0f}% "
          f"· {out['n_mua']} MUA · {out['n_de_mat']} để mắt · {len(hits)} mã đáng chú ý")
    for h in hits[:10]:
        print(f"  [{h['level']:8s}] {h['sym']:5s} {h['pct']:+6.2f}% vol {h['volr']:.2f}× "
              f"GTGD {h['gtgd']:.0f} tỷ" + (f" | thiếu: {', '.join(h['miss'])}" if h['miss'] else ''))


if __name__ == '__main__':
    main()
