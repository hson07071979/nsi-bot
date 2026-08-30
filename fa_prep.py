# -*- coding: utf-8 -*-
"""Chuyen fireant_daily.json -> ma tran numpy (nhanh)."""
import json, numpy as np, datetime as dt, os
F='data/fa.npz'
def build(force=False):
    if os.path.exists(F) and not force:
        z=np.load(F, allow_pickle=True)
        return {k:z[k] for k in z.files}
    raw=json.load(open('data/fireant_daily.json'))
    ex=raw['ex']; data=raw['data']
    syms=sorted(data)
    cal=sorted({d for s in syms for d in data[s]['d']})
    idx={d:i for i,d in enumerate(cal)}
    N,M=len(cal),len(syms)
    F_={}
    fields=['PriceClose','PriceBasic','PriceOpen','PriceHigh','PriceLow','Volume','TotalValue',
            'AdjClose','AdjOpen','AdjHigh','AdjLow','AdjRatio','MarketCap',
            'BuyForeignQuantity','SellForeignQuantity','BuyCount','SellCount','BuyQuantity','SellQuantity','TotalTrade']
    for f in fields: F_[f]=np.full((N,M),np.nan,dtype=np.float32)
    for j,s in enumerate(syms):
        c=data[s]; ii=np.array([idx[d] for d in c['d']])
        for f in fields:
            v=np.array([np.nan if x is None else x for x in c[f]],dtype=np.float64)
            F_[f][ii,j]=v
    out=dict(sym=np.array(syms), cal=np.array(cal),
             exch=np.array([ex.get(s,'HOSE') for s in syms]), **F_)
    np.savez_compressed(F, **out)
    return out
if __name__=='__main__':
    d=build(force=True)
    print('cal',len(d['cal']), d['cal'][0], d['cal'][-1], 'syms',len(d['sym']))
    print('size MB', round(os.path.getsize(F)/1e6,1))
