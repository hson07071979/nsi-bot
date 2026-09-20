# -*- coding: utf-8 -*-
"""GIAI DOAN 3 — soi ky vung ung vien, va thu ket hop.
   Cau hoi phai tra loi: 603% o top120/nen22 la CAO NGUYEN hay MUI NHON?
   Mui nhon = do may, doi du lieu mot chut la bay mat."""
import json, numpy as np, engine2 as E
from produce2 import PROD

def nua(r, a, b):
    eq=[v for d,v,*_ in r['eq'] if a<=d[:4]<=b]
    if len(eq)<30: return None
    x=np.array(eq); return round(float(x[-1]/x[0]-1),4)

def chay(ten, gd, truot=False, im=False):
    c=dict(PROD); c.update(gd)
    if truot: c['slip']=0.002
    r=E.run(c,log=False); m=E.metrics(r)
    d=dict(ten=ten,**{k:float(v) if isinstance(v,(np.floating,np.integer)) else v for k,v in m.items()},
           deal=len({(t['sym'],t['entry']) for t in r['trades']}),
           dau=nua(r,'2019','2022'), cuoi=nua(r,'2023','2026'),
           nam={y:round(float(v),4) for y,v in _nam(r).items()})
    if not im:
        print(f"{ten:34s} {d['total_return']*100:8.1f}%  DD {d['maxdd']*100:5.2f}%  PF {d['pf']:5.2f}  "
              f"Sh {d['sharpe']:4.2f}  deal {d['deal']:3d} | 19-22 {d['dau']*100:6.1f}%  23-26 {d['cuoi']*100:6.1f}%",flush=True)
    return d

def _nam(r):
    d={}
    for dd,nv,*_ in r['eq']: d.setdefault(dd[:4],[]).append(float(nv))
    o={};p=None
    for y in sorted(d):
        s=p if p is not None else d[y][0]; o[y]=d[y][-1]/s-1; p=d[y][-1]
    return o

KQ={}
print('=== A. LUOI MIN quanh ung vien (co phai cao nguyen khong?) ===',flush=True)
print(f"{'':>6}"+''.join(f"{int(b*100):>9}%" for b in (0.20,0.21,0.22,0.23,0.24,0.25)),flush=True)
luoi={}
for tn in (110,115,120,125,130,140):
    hang=[]
    for br in (0.20,0.21,0.22,0.23,0.24,0.25):
        d=chay(f't{tn}_n{int(br*100)}',dict(top_n=tn,base_range=br),im=True)
        luoi[(tn,br)]=d; hang.append(d['total_return']*100)
    print(f"top{tn:>3}"+''.join(f"{v:9.1f}%" for v in hang),flush=True)
KQ['luoi']=[{'top':k[0],'nen':k[1],**v} for k,v in luoi.items()]

print('\n=== B. Ung vien + siet nguong dong tien (bu lai chat luong) ===',flush=True)
KQ['oi']=[chay(f'top120 nen22 + dongtien {o:.2f}',dict(top_n=120,base_range=0.22,ordimb_min=o))
          for o in (1.20,1.30,1.40,1.50)]

print('\n=== C. Ung vien + co vi the lon hon (danh doi rui ro) ===',flush=True)
KQ['size']=[chay(f'top120 nen22 + co {int(bs*100)}%',dict(top_n=120,base_range=0.22,base_size=bs,max_pos=max(0.5,bs)))
            for bs in (0.42,0.50,0.60,0.70)]

json.dump(KQ,open('/tmp/quet3.json','w'),ensure_ascii=False)
print('\nxong')
