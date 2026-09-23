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

ERR={}
def daily(sym, start=START, end=None):
    end = end or time.strftime('%Y-%m-%d')
    last=None
    for a in range(4):
        try:
            r=requests.get(BASE+'/Companies/HistoricalQuotes',
                params={'symbol':sym,'startDate':start,'endDate':end}, headers=H, timeout=90)
            if r.status_code!=200:
                last=f'HTTP {r.status_code}: {r.text[:120]!r}'
                if r.status_code in (400,404): break
                ra=r.headers.get('Retry-After')
                time.sleep(float(ra) if (ra and ra.isdigit()) else 1.5*(a+1)); continue
            d=r.json()
            if isinstance(d,list): return d
            last=f'schema: {type(d).__name__} {str(d)[:120]!r}'
        except Exception as e:
            last=f'{type(e).__name__}: {e}'
        time.sleep(1.5*(a+1))
    if last: ERR[sym]=last
    return None

# ---- INTEGRITY GUARD (audit 23/09/2026) -----------------------------------
# A partial fetch must never be published as a normal healthy build. Coverage is
# measured on symbols LISTED TODAY on HOSE/HNX (dead symbols may legitimately be
# short or empty). Below these floors the run FAILS and the previous good file
# stays in place (atomic replace only after the guard passes).
MIN_LIVE_COVER=0.97      # listed HOSE/HNX symbols with a usable history
MIN_LAST_COVER=0.93      # ... of which carry the latest session

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


def universe_live():
    d = pd.read_csv('data/by_exchange.csv')
    d = d[(d.type == 'STOCK') & d.exchange.isin(['HSX', 'HNX'])]
    return {r.symbol: ('HOSE' if r.exchange == 'HSX' else 'HNX') for r in d.itertuples()}


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
    res={}; bad=[]; fetched=set()
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
            if c and c['d']: fetched.add(s)
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
    # ---------------- guard ----------------
    import datetime as _dt
    song=[s for s,v in universe_live().items()]
    got=[s for s in song if s in fetched]            # answered with data (any length)
    last=max((res[s]['d'][-1] for s in res), default='')
    hist=[s for s in song if s in res]                # >= 250 sessions, tradable history
    at_last=[s for s in hist if res[s]['d'][-1]==last]
    # order-flow coverage measured where it matters: liquid names (GTGD >= 5 bn today)
    liq=[s for s in at_last if (res[s]['TotalValue'][-1] or 0)>=5e9]
    oi_last=[s for s in liq if (res[s]['BuyCount'][-1] or 0)>0 and (res[s]['SellCount'][-1] or 0)>0]
    exch={}
    for s in song:
        e=universe_live()[s]; exch.setdefault(e,[0,0]); exch[e][0]+=1; exch[e][1]+= (s in got)
    H_=dict(source='FireAnt HistoricalQuotes', fetched=_dt.datetime.utcnow().isoformat(timespec='seconds')+'Z',
            expected_listed=len(song), received_listed=len(got), coverage=round(len(got)/max(1,len(song)),4),
            latest_session=last, latest_session_coverage=round(len(at_last)/max(1,len(hist)),4),
            by_exchange={k:dict(expected=v[0],received=v[1],coverage=round(v[1]/max(1,v[0]),4)) for k,v in exch.items()},
            orderflow_latest_coverage=round(len(oi_last)/max(1,len(liq)),4), orderflow_liquid_n=len(liq),
            http_errors=len(ERR), error_sample=dict(list(ERR.items())[:10]),
            missing_listed=sorted(set(song)-set(got))[:100])
    ok = H_['coverage']>=MIN_LIVE_COVER and H_['latest_session_coverage']>=MIN_LAST_COVER
    H_['status']='OK' if ok else 'FAIL'
    try:
        import data_health as _dh; _dh.put('fireant_price', H_)
        _dh.put('fireant_orderflow', dict(source='FireAnt HistoricalQuotes Buy/SellCount',
                status=('OK' if H_['orderflow_latest_coverage']>=0.70 else 'DEGRADED'),
                coverage=H_['orderflow_latest_coverage'], freshness=last))
    except Exception as e: print('data_health:',e)
    print(json.dumps({k:v for k,v in H_.items() if k not in ('missing_listed','error_sample')},ensure_ascii=False),flush=True)
    if not ok:
        sys.exit(f"HONG: FireAnt chi phu {H_['coverage']:.1%} ma dang niem yet / {H_['latest_session_coverage']:.1%} "
                 "co phien moi nhat — KHONG ghi de data/fireant_daily.json, KHONG dang ban thieu.")
    tmp='data/fireant_daily.json.tmp'
    json.dump({'ex':ex,'data':res}, open(tmp,'w'))
    os.replace(tmp,'data/fireant_daily.json')
    print('OK',len(res),'bad',len(bad),'time',round(time.time()-t0),'s',
          'size MB',round(os.path.getsize('data/fireant_daily.json')/1e6,1))
