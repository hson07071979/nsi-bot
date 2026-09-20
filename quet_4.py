# -*- coding: utf-8 -*-
"""GIAI DOAN 4 — kiem chung ung vien truoc khi dam de xuat.
   Ba cau hoi: (1) 1,40 la cao nguyen hay mui nhon? (2) con song khong khi co
   truot gia? (3) neu chi duoc nhin 2019-2022 de chon thi 2023-2026 co tot khong?"""
import json, numpy as np, engine2 as E
from produce2 import PROD
UV = dict(top_n=120, base_range=0.22, ordimb_min=1.40)

def _nam(r):
    d={}
    for dd,nv,*_ in r['eq']: d.setdefault(dd[:4],[]).append(float(nv))
    o={};p=None
    for y in sorted(d):
        s=p if p is not None else d[y][0]; o[y]=round(d[y][-1]/s-1,4); p=d[y][-1]
    return o

def lat(r,a,b):
    eq=[v for dd,v,*_ in r['eq'] if a<=dd[:4]<=b]
    if len(eq)<30: return None
    x=np.array(eq); dd_=float((1-x/np.maximum.accumulate(x)).max())
    tr=[t for t in r['trades'] if a<=t['exit'][:4]<=b]
    gp=sum(t['pnl_vnd'] for t in tr if t['pnl_vnd']>0); gl=abs(sum(t['pnl_vnd'] for t in tr if t['pnl_vnd']<0))
    return dict(loi=round(float(x[-1]/x[0]-1),4),dd=round(dd_,4),
                pf=round(gp/gl,2) if gl else None,lenh=len(tr))

def chay(ten,gd,truot=False,ra=True):
    c=dict(PROD); c.update(gd)
    if truot: c['slip']=0.002
    r=E.run(c,log=False); m=E.metrics(r)
    v=sorted((t['pnl_vnd'] for t in r['trades']),reverse=True); gp=sum(x for x in v if x>0)
    d=dict(ten=ten,**{k:float(x) if isinstance(x,(np.floating,np.integer)) else x for k,x in m.items()},
           deal=len({(t['sym'],t['entry']) for t in r['trades']}),
           dau=lat(r,'2019','2022'),cuoi=lat(r,'2023','2026'),nam=_nam(r),
           top3=round(sum(v[:3])/gp*100,1) if gp else None)
    if ra:
        print(f"{ten:38s} {d['total_return']*100:8.1f}%  DD {d['maxdd']*100:5.2f}%  PF {d['pf']:5.2f}  "
              f"Sh {d['sharpe']:4.2f}  deal {d['deal']:3d}  top3 {d['top3']:4.1f}% | "
              f"19-22 {d['dau']['loi']*100:6.1f}%  23-26 {d['cuoi']['loi']*100:6.1f}%",flush=True)
    return d

K={}
print('=== A. Nguong dong tien co phai cao nguyen? (top120, nen 22%) ===',flush=True)
K['oi']=[chay(f'dong tien {o:.2f}',dict(top_n=120,base_range=0.22,ordimb_min=o)) for o in (1.28,1.32,1.36,1.40,1.44,1.48)]

print('\n=== B. 1,40 tren cau hinh DANG CHAY (tach rieng tuong tac) ===',flush=True)
K['tuongtac']=[chay('top110 nen18 + dong tien 1,40',dict(ordimb_min=1.40)),
               chay('top120 nen18 + dong tien 1,40',dict(top_n=120,ordimb_min=1.40)),
               chay('top110 nen22 + dong tien 1,40',dict(base_range=0.22,ordimb_min=1.40))]

print('\n=== C. Co truot gia 0,2% — co song khong? ===',flush=True)
K['truot']=[chay('NEN: dang chay',{},truot=True),
            chay('UNG VIEN: t120/n22/dt1,40',UV,truot=True),
            chay('UNG VIEN + co vi the 60%',dict(UV,base_size=0.60,max_pos=0.60),truot=True)]

print('\n=== D. Nac rui ro: co vi the tren ung vien (khong truot) ===',flush=True)
K['size']=[chay(f'ung vien + co {int(b*100)}%',dict(UV,base_size=b,max_pos=max(0.5,b))) for b in (0.42,0.50,0.60,0.70)]

print('\n=== E. Nen va ung vien, tung nam ===',flush=True)
nen=chay('NEN dang chay',{}); uv=chay('UNG VIEN t120/n22/dt1,40',UV)
K['nen']=nen; K['uv']=uv
print(f"\n{'nam':>6} {'nen':>9} {'ung vien':>10}")
for y in sorted(uv['nam']):
    print(f"{y:>6} {nen['nam'].get(y,0)*100:8.1f}% {uv['nam'][y]*100:9.1f}%")
json.dump(K,open('/tmp/quet4.json','w'),ensure_ascii=False)
print('\nxong')
