# -*- coding: utf-8 -*-
"""Cong thi truong v2: G1 do rong (breadth) + G2 VN-Index/MA50 + G3 ngay phan phoi + FTD."""
import numpy as np, json, datetime as dt

def _ffill(a):
    out=a.copy()
    for i in range(1,len(out)):
        if np.isnan(out[i]): out[i]=out[i-1]
    return out

def build_regime(d, I, cfg):
    cal=d['cal']; N=len(cal)
    AC=d['AdjClose']
    # ---- G1: chi so deu trong so cua vu tru (dung log-return, chan outlier)
    ret=np.full(AC.shape,np.nan,dtype=np.float64); ret[1:]=AC[1:]/AC[:-1]-1
    valid=(d['MarketCap']>1000e9)&(I['nbars']>=250)
    ret=np.where(valid, ret, np.nan)
    ret=np.where(np.abs(ret)>0.20, np.nan, ret)
    eq=np.nanmean(ret,axis=1); eq=np.nan_to_num(eq,nan=0.0)
    g1=np.cumprod(1+eq)*1000.0
    g1ma=np.full(N,np.nan)
    for i in range(199,N): g1ma[i]=g1[i-199:i+1].mean()
    # ---- do rong: % ma tren MA50 / MA200
    above50=np.nanmean((AC>I['ma50'])&valid, axis=1)/np.maximum(np.nanmean(valid,axis=1),1e-9)
    above200=np.nanmean((AC>I['ma200'])&valid, axis=1)/np.maximum(np.nanmean(valid,axis=1),1e-9)
    # ---- VN-Index
    vni_raw=json.load(open('data/VNINDEX.json'))
    vmap={dt.datetime.utcfromtimestamp(t).date().isoformat():(c,v) for t,c,v in zip(vni_raw['t'],vni_raw['c'],vni_raw['v'])}
    vc=_ffill(np.array([vmap.get(x,(np.nan,np.nan))[0] for x in cal],dtype=float))
    vv=_ffill(np.array([vmap.get(x,(np.nan,np.nan))[1] for x in cal],dtype=float))
    vma50=np.full(N,np.nan); vma200=np.full(N,np.nan)
    for i in range(49,N): vma50[i]=np.nanmean(vc[i-49:i+1])
    for i in range(199,N): vma200[i]=np.nanmean(vc[i-199:i+1])
    # ---- ngay phan phoi
    dd=[]; dcount=np.zeros(N,dtype=int)
    for i in range(1,N):
        chg=vc[i]/vc[i-1]-1 if vc[i-1]>0 else 0
        if chg<-0.002 and vv[i]>vv[i-1]: dd.append((i,vc[i]))
        dd=[(k,p) for k,p in dd if (i-k)<=25 and vc[i]<p*1.05]
        dcount[i]=len(dd)
    # ---- FTD: sau khi G1 thung MA200, tim ngay but pha
    ftd=np.zeros(N,dtype=bool); rally=np.zeros(N,dtype=int)
    day1_low=None; cnt=0
    for i in range(1,N):
        red = (not np.isnan(g1ma[i])) and g1[i]<g1ma[i]
        if not red: day1_low=None; cnt=0; rally[i]=0; continue
        if day1_low is None:
            if vc[i]>vc[i-1]: day1_low=vc[i]*0.995; cnt=1
        else:
            if vc[i]<day1_low: day1_low=None; cnt=0
            else:
                cnt+=1
                chg=vc[i]/vc[i-1]-1
                if cnt>=4 and chg>=cfg['ftd_gain'] and vv[i]>vv[i-1]:
                    ftd[i]=True
        rally[i]=cnt
    # ---- he den
    light=[]; size=np.zeros(N)
    ftd_on=False; ftd_age=0
    for i in range(N):
        red = (not np.isnan(g1ma[i])) and g1[i]<g1ma[i]
        if not red: ftd_on=False; ftd_age=0
        else:
            if ftd[i] and cfg['use_ftd']: ftd_on=True; ftd_age=0
            elif ftd_on:
                ftd_age+=1
                if vc[i]<vma50[i]*0.97: ftd_on=False   # that bai -> tat lai
        if red and not ftd_on: l='DO'
        elif dcount[i]>=5: l='CAM'
        elif (not np.isnan(vma50[i]) and vc[i]<vma50[i]) or dcount[i]>=3 or ftd_on: l='VANG'
        elif np.isnan(g1ma[i]): l='VANG'
        else: l='XANH'
        light.append(l); size[i]=cfg['size_map'][l]
    return dict(g1=g1,g1ma=g1ma,vni=vc,vma50=vma50,vma200=vma200,dcount=dcount,
                light=light,size=size,ftd=ftd,above50=above50,above200=above200,rally=rally)
