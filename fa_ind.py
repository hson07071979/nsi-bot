# -*- coding: utf-8 -*-
"""Chi bao ky thuat tren du lieu FireAnt."""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
import signal_spec as _SP

def sma(a,n):
    out=np.full(a.shape,np.nan,dtype=np.float32)
    if a.shape[0]<n: return out
    w=sliding_window_view(a,n,axis=0)
    out[n-1:]=np.nanmean(w,axis=-1)
    cnt=np.sum(~np.isnan(w),axis=-1)
    out[n-1:][cnt<n*0.8]=np.nan
    return out
def sma_seq(a,n=_SP.MEAN_N,need=_SP.MEAN_NEED):
    """Trung binh n phien DUNG CHUNG voi lop quet trong phien (signal_spec.mean20):
    cong float64 TUAN TU tu phien cu nhat toi moi nhat (bo NaN), chia so phien co
    so lieu, luu float32; NaN neu < need phien. np.nanmean float32 cong theo thu tu
    noi bo (SIMD) — khong tai hien duoc ngoai numpy, nen lech ty le ULP voi live
    (parity 26/09/2026). Chi dung cho cac mang ma lop live phai tai hien: vma20,
    tvma20, volat20."""
    out=np.full(a.shape,np.nan,dtype=np.float32)
    T=a.shape[0]
    if T<n: return out
    N=T-n+1
    s=np.zeros((N,)+a.shape[1:],dtype=np.float64); c=np.zeros((N,)+a.shape[1:],dtype=np.int64)
    for k in range(n):
        w=a[k:k+N].astype(np.float64); m=~np.isnan(w)
        s=s+np.where(m,w,0.0); c+=m
    with np.errstate(invalid='ignore',divide='ignore'):
        mean=s/np.where(c>0,c,1)
    mean[(c<need)|(c<=0)]=np.nan
    out[n-1:]=mean
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
    """Phan vi cat ngang TUNG PHIEN — dinh nghia duy nhat la signal_spec.pct_ranks
    (so ma KHAC nho hon han / (n-1), dong hang lay hang thap nhat, >= 40 gia tri).
    Ban cu argsort().argsort() xep cac gia tri BANG NHAU theo thu tu tuy y cua
    quicksort — lop live khong the tai hien (parity 26/09/2026)."""
    out=np.full(a.shape,np.nan,dtype=np.float32)
    for i in range(a.shape[0]):
        row=a[i]; m=~np.isnan(row)
        if m.sum()<_SP.RANK_MIN_N: continue
        out[i,m]=_SP.pct_ranks([float(x) for x in row[m]])
    return out

THR_HOSE, THR_HNX = 0.056, 0.088

def indicators(d, base_len=30):
    AC=d['AdjClose']; AH=d['AdjHigh']; AL=d['AdjLow']; AO=d['AdjOpen']
    C=d['PriceClose']; B=d['PriceBasic']; V=d['Volume']; TV=d['TotalValue']
    I={}
    for n in (5,10,20,30,50,200): I['ma%d'%n]=sma(AC,n)
    I['vma20']=sma_seq(V,20); I['tvma20']=sma_seq(TV,20)
    I['pct']=C/np.where(B>0,B,np.nan)-1
    # Dieu kien 1 (bien do tang gia). HOSE 5,8% -> 5,6% ngay 25/09/2026 (R11: Monte
    # Carlo + ca hai nua ky, evidence/r11_progress.json). PHAI trung produce2.PROD
    # trig_hose/trig_hnx (tests/test_regressions.py kiem).
    I['thr']=np.where(d['exch']=='HNX',THR_HNX,THR_HOSE).astype(np.float32)
    I['thr_hard']=np.where(d['exch']=='HNX',0.098,0.068).astype(np.float32)
    I['volr']=V/np.where(I['vma20']>0,I['vma20'],np.nan)
    rng=(AH-AL)/np.where(AC>0,AC,np.nan)
    I['volat20']=sma_seq(rng,20)
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
