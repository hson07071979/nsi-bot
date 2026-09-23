"""Impact of UPCOM-today symbols labelled HOSE/HNX by fireant.suy_ra_san (audit 24/09/2026).
They can never be BOUGHT (no fundamentals -> skipped) but they take TOP-N slots,
enter RS/momentum percentile ranks and market breadth. Variant: exclude them from TOP-N."""
import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import json, numpy as np, pandas as pd
from common import run, line, meta
import vn300, engine2 as E
b=pd.read_csv('data/by_exchange.csv'); b=b[b.type=='STOCK']; ex=dict(zip(b.symbol,b.exchange))
d,I,_,_=E.load(); S=[str(x) for x in d['sym']]
up=np.array([ex.get(s)=='UPCOM' for s in S])
base,_r=run({},'PROD',keep=True)
orig=vn300.build_topn
def patched(I_,n=300):
    tv=I_['tvma20'].copy(); tv[:,up]=np.nan
    return orig(dict(I_,tvma20=tv),n)
vn300.build_topn=patched
alt,_=run({},'PROD, TOP-N without UPCOM-today names',keep=True)
vn300.build_topn=orig
T0=orig(I,120); T1=patched(I,120)
share=float((T0&up[None,:]).sum(1).mean())
print(line(base)); print(line(alt))
print(f'avg UPCOM-today names inside TOP-120 per session: {share:.1f}')
json.dump(dict(meta=meta(),base=base,alt=alt,avg_upcom_in_top120=share),open('evidence/audit_r7_upcom.json','w'),ensure_ascii=False,indent=1,default=str)
