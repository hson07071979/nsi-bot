# -*- coding: utf-8 -*-
"""Cao du lieu truc tiep tu FireAnt (khong can token).
   Cho ra: gia dieu chinh, gia tham chieu (de bat TRAN chinh xac),
   GTGD thuc, khoi ngoai, thong ke lenh mua/ban, von hoa tung ngay."""
import requests, json, time, os, sys
import pandas as pd, numpy as np
from concurrent.futures import ThreadPoolExecutor

H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36',
   'Referer':'https://fireant.vn/','Accept':'application/json'}
BASE='https://www.fireant.vn/api/Data'
START='2017-01-01'

def daily(sym, start=START, end=None):
    end = end or time.strftime('%Y-%m-%d')
    for a in range(4):
        try:
            r=requests.get(BASE+'/Companies/HistoricalQuotes',
                params={'symbol':sym,'startDate':start,'endDate':end}, headers=H, timeout=90)
            d=r.json()
            if isinstance(d,list): return d
        except Exception:
            time.sleep(1.5*(a+1))
    return None

def intraday(sym):
    try:
        r=requests.get(BASE+'/Markets/IntradayQuotes', params={'symbol':sym}, headers=H, timeout=30)
        d=r.json()
        return d if isinstance(d,list) else []
    except Exception: return []

KEEP=['Date','PriceOpen','PriceHigh','PriceLow','PriceClose','PriceBasic','PriceAverage',
      'Volume','TotalValue','PutthroughVolume','AdjRatio','AdjOpen','AdjHigh','AdjLow','AdjClose',
      'BuyForeignQuantity','SellForeignQuantity','BuyCount','SellCount','BuyQuantity','SellQuantity',
      'TotalTrade','Shares','MarketCap']

def compact(rows):
    rows=sorted(rows, key=lambda x:x['Date'])
    out={}
    out['d']=[r['Date'][:10] for r in rows]
    for k in KEEP[1:]:
        out[k]=[ (None if r.get(k) is None else round(float(r[k]),4)) for r in rows]
    return out

def universe():
    """DANH SACH MA — bao gom ca ma DA CHET.

    ⚠️ LOI SURVIVORSHIP BIAS DA SUA (30/08/2026).
    Ban cu loc `exchange in ['HSX','HNX']`, ma cot `exchange` cua vnstock la
    TRANG THAI HOM NAY. Nghia la moi ma da huy niem yet hoac bi day xuong UPCOM
    trong 2019-2026 deu bi vut khoi vu tru backtest — 1.637 ma DELISTED va 818 ma
    UPCOM. Trong so do co FLC, ROS, HAI, AMD, KLF, GAB, ITA, HNG, POM...

    Vi sao dieu nay giet chet do tin cay cua backtest: he thong nay mua CHINH XAC
    kieu phien ma nhom FLC tao ra nam 2021 — tran, khoi luong gap doi, sau mot nen
    tich luy. Bo chung ra khoi qua khu roi do "he bat tran co lai khong" thi da tra
    loi truoc cau hoi roi. Backtest chi con thay nhung cu bat tran CUA MA SONG SOT.

    Nen bay gio lay het. San lich su suy ra tu bien do gia quan sat duoc, vi vnstock
    chi biet san HOM NAY chu khong biet san nam 2021.
    """
    d = pd.read_csv('data/by_exchange.csv')
    d = d[d.type == 'STOCK']
    song = d[d.exchange.isin(['HSX', 'HNX'])]
    chet = d[d.exchange.isin(['DELISTED', 'UPCOM'])]
    ex = {r.symbol: ('HOSE' if r.exchange == 'HSX' else 'HNX') for r in song.itertuples()}
    # ma chet: chua biet san lich su, danh dau de suy ra sau khi co gia
    for r in chet.itertuples():
        ex[r.symbol] = '?'
    print(f'universe: {len(song)} ma dang niem yet + {len(chet)} ma da chet/xuong UPCOM', flush=True)
    return ex


def suy_ra_san(rows):
    """Suy ra san NIEM YET LICH SU tu bien do gia quan sat duoc.

    HOSE bien do +-7%, HNX +-10%, UPCOM +-15%. Lay phan vi 98 cua |thay doi so
    gia tham chieu| trong 250 phien DAU (luc ma con dang niem yet binh thuong),
    roi chon san co bien do gan nhat. Khong hoan hao, nhung dung hon nhieu so voi
    viec dan nhan san HOM NAY cho du lieu cua nam 2021.
    """
    import numpy as _np
    v = []
    for r in rows[:250]:
        c, b = r.get('PriceClose'), r.get('PriceBasic')
        if c and b and b > 0:
            v.append(abs(float(c) / float(b) - 1))
    if len(v) < 60:
        return 'HOSE'
    p98 = float(_np.percentile(v, 98))
    # chon san co tran gan p98 nhat
    return min((('HOSE', 0.07), ('HNX', 0.10), ('UPCOM', 0.15)),
               key=lambda x: abs(p98 - x[1]))[0]

if __name__=='__main__':
    ex=universe(); syms=sorted(ex)
    print('universe',len(syms),flush=True)
    res={}; bad=[]
    def job(s):
        d=daily(s)
        if not d: return s, None, None
        # Suy ra san NGAY TAI DAY roi vut du lieu tho di. Giu lai ca 1.751 cuc
        # du lieu tho de xu ly sau thi het sach bo nho — da bi giet mot lan vi vay.
        san = suy_ra_san(sorted(d, key=lambda x: x['Date'])) if ex.get(s) == '?' else None
        return s, compact(d), san
    t0=time.time()
    n_suy = 0
    with ThreadPoolExecutor(8) as pool:
        for i,(s,c,san) in enumerate(pool.map(job,syms)):
            if c and len(c['d'])>=250:
                res[s]=c
                if san: ex[s]=san; n_suy+=1
            else:
                bad.append(s); ex.pop(s, None)
            if i%200==0: print(i,len(res),round(time.time()-t0),'s',flush=True)
    print(f'suy ra san lich su cho {n_suy} ma da chet', flush=True)
    from collections import Counter
    print('  phan bo:', dict(Counter(ex[s] for s in res)), flush=True)
    # UPCOM khong nam trong pham vi giao dich cua he — bo khoi vu tru
    bo_upcom = [s for s in res if ex.get(s) == 'UPCOM']
    for s in bo_upcom: res.pop(s, None); ex.pop(s, None)
    print(f'bo {len(bo_upcom)} ma suy ra la UPCOM (he chi giao dich HOSE + HNX)', flush=True)
    json.dump({'ex':ex,'data':res}, open('data/fireant_daily.json','w'))
    print('OK',len(res),'bad',len(bad),'time',round(time.time()-t0),'s',
          'size MB',round(os.path.getsize('data/fireant_daily.json')/1e6,1))
