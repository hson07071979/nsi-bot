# -*- coding: utf-8 -*-
"""Chi bao ky thuat tren du lieu FireAnt."""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

def sma(a,n):
    out=np.full(a.shape,np.nan,dtype=np.float32)
    if a.shape[0]<n: return out
    w=sliding_window_view(a,n,axis=0)
    out[n-1:]=np.nanmean(w,axis=-1)
    cnt=np.sum(~np.isnan(w),axis=-1)
    out[n-1:][cnt<n*0.8]=np.nan
    return out
def rmax(a,n):
    out=np.full(a.shape,np.nan,dtype=np.float32)
    if a.shape[0]>=n: out[n-1:]=np.nanmax(sliding_window_view(a,n,axis=0),axis=-1)
    return out
def rmin(a,n):
    out=np.full(a.shape,np.nan,dtype=np.float32)
    if a.shape[0]>=n: out[n-1:]=np.nanmin(sliding_window_view(a,n,axis=0),axis=-1)
    return out
def shift(a,k):
    out=np.full(a.shape,np.nan,dtype=np.float32); out[k:]=a[:-k]; return out
def pct_rank(a):
    out=np.full(a.shape,np.nan,dtype=np.float32)
    for i in range(a.shape[0]):
        row=a[i]; m=~np.isnan(row)
        if m.sum()<40: continue
        v=row[m]; out[i,m]=v.argsort().argsort()/(len(v)-1)
    return out

def indicators(d, base_len=30):
    AC=d['AdjClose']; AH=d['AdjHigh']; AL=d['AdjLow']; AO=d['AdjOpen']
    C=d['PriceClose']; B=d['PriceBasic']; V=d['Volume']; TV=d['TotalValue']
    I={}
    for n in (5,10,20,30,50,200): I['ma%d'%n]=sma(AC,n)
    I['vma20']=sma(V,20); I['tvma20']=sma(TV,20)
    I['pct']=C/np.where(B>0,B,np.nan)-1
    I['thr']=np.where(d['exch']=='HNX',0.088,0.058).astype(np.float32)
    I['thr_hard']=np.where(d['exch']=='HNX',0.098,0.068).astype(np.float32)
    I['volr']=V/np.where(I['vma20']>0,I['vma20'],np.nan)
    rng=(AH-AL)/np.where(AC>0,AC,np.nan)
    I['volat20']=sma(rng,20)
    I['hi52']=rmax(AH,250); I['hi10']=rmax(AH,10)
    I['nbars']=np.cumsum(~np.isnan(AC),axis=0)
    # nen: base_len phien TRUOC phien hien tai
    I['base_hi']=shift(rmax(AC,base_len),1); I['base_lo']=shift(rmin(AC,base_len),1)
    I['base_hi_w']=shift(rmax(AH,base_len),1); I['base_lo_w']=shift(rmin(AL,base_len),1)
    # do chat: do lech chuan / trung binh trong nen
    ma=sma(AC,base_len)
    sd=np.full(AC.shape,np.nan,dtype=np.float32)
    if AC.shape[0]>=base_len:
        sd[base_len-1:]=np.nanstd(sliding_window_view(AC,base_len,axis=0),axis=-1)
    I['tight']=shift(sd/np.where(ma>0,ma,np.nan),1)
    # nen phang ngan (shelf) 15 phien
    I['sh_hi']=shift(rmax(AC,15),1); I['sh_lo']=shift(rmin(AC,15),1)
    r12=np.full(AC.shape,np.nan,dtype=np.float32); r12[250:]=AC[250:]/AC[:-250]-1
    r3=np.full(AC.shape,np.nan,dtype=np.float32); r3[60:]=AC[60:]/AC[:-60]-1
    I['rs']=pct_rank(r12)*100; I['mom3']=pct_rank(r3)
    # DONG TIEN LON: co lenh trung binh mua vs ban
    bavg=d['BuyQuantity']/np.where(d['BuyCount']>0,d['BuyCount'],np.nan)
    savg=d['SellQuantity']/np.where(d['SellCount']>0,d['SellCount'],np.nan)
    I['ordimb']=bavg/np.where(savg>0,savg,np.nan)
    I['fnet']=(d['BuyForeignQuantity']-d['SellForeignQuantity'])*C
    I['fnet20']=sma(I['fnet'],20)
    return I
