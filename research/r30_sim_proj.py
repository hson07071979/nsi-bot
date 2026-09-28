import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json, glob, numpy as np, datetime as dt, engine2 as E
from produce2 import PROD
from engine import as_of, risk_gate, canslim_score
FIN=json.load(open('/tmp/fin28.json'))
def shares(hhmm):
    for f in glob.glob('/tmp/snaps/*.json'):
        L=json.load(open(f))
        if L.get('session')=='2026-09-28' and L['asof'][11:16]==hhmm:
            return np.array([h['vol']/FIN[h['sym']] for h in L['hits'] if FIN.get(h['sym']) and h.get('vol')])
S={'14:11':shares('14:11'),'14:23':shares('14:23')}
CURVE={'14:11':0.83,'14:23':0.885}   # live VOL_CURVE tai 14:11 / 14:23
r=E.run(PROD,log=True); d=r['d']; I=r['I']; cal=[str(x) for x in d['cal']]; SY=[str(x) for x in d['sym']]
base=E.metrics(r)
sig=[(s['sym'],s['date'],float(I['volr'][cal.index(s['date']),SY.index(s['sym'])])) for s in r['signals']]
# near-miss: du moi dieu kien tru KL (final volr 1.2-2.0), bat ke Cond9 -> se bi bao nham
C=dict(E.CFG); C.update(PROD)
b,bo,TOPN,trig=E.prep_masks(d,I,C)
nm=[]
_,_,TLS,SECT=E.load()
i0=next(k for k,c in enumerate(cal) if c>='2019-01-01')
AC=d['AdjClose']
for i in range(i0,len(cal)-3):
    day=dt.date.fromisoformat(cal[i])
    C2=dict(C); C2['vol_floor']=1.2
    for x in E.screen(i,d,I,TLS,SECT,C2,TOPN,b,bo,trig,day,ignore_ordimb=True):
        v=x['volr']
        if v<2.0:
            j=x['j']; t3=AC[i+3,j]*(1-C['fee_sell'])/(AC[i,j]*(1+C['fee_buy']))-1
            nm.append((v, float(t3)))
nm=np.array(nm); print('near-miss (KL 1,2-2,0x, du dieu kien khac):',len(nm),'lan / 7,7 nam')
rng=np.random.default_rng(7)
for tt in ('14:11','14:23'):
    sh=S[tt]; cv=CURVE[tt]
    for name,a,bb in (('KL hien tai >= 2,0x (hien nay)',2.0,0),('KL >= 1,7x va du phong >= 2,0x',1.7,2.0),('KL >= 1,6x va du phong >= 1,9x',1.6,1.9),('KL >= 1,5x va du phong >= 1,8x',1.5,1.8)):
        rets=[]; caught=[]
        for sd in range(12):
            s_=rng.choice(sh,len(sig))
            now=np.array([v for _,_,v in sig])*s_
            ok=(now>=a)&(now/cv>=bb)
            fm=[(sy,dd) for (sy,dd,_),o in zip(sig,ok) if not o]
            rets.append(E.metrics(E.run(dict(PROD,force_miss=fm),log=False))['total_return']); caught.append(ok.mean())
        s2=rng.choice(sh,len(nm)); now2=nm[:,0]*s2; fa=(now2>=a)&(now2/cv>=bb)
        print(f"{tt} {name:34s} bat {np.mean(caught):.0%} tin hieu | backtest trung vi {np.median(rets)*100:+.0f}% (P10 {np.percentile(rets,10)*100:+.0f}%) | bao nham {fa.sum()} lan, T+3 TB {nm[fa,1].mean()*100 if fa.any() else 0:+.2f}%")
print('goc',base['total_return'])
