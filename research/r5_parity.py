"""Replay: for every engine entry, rebuild lookup.build() AS OF the previous session
(what thresholds.json would have said the night before) and evaluate the live
scanner's MUA rule on the signal-session row. Measures recall of live vs engine,
and precision (live MUA on days the engine did not buy)."""
import sys,os; sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import json, numpy as np
from collections import Counter
import engine2 as E, lookup
from vn300 import build_topn
from common import run, meta
from produce2 import PROD
CUR=dict(PROD,pyr_caps=True,max_n_in_loop=True,use_cond8=False)
s,r=run(dict(pyr_caps=True,max_n_in_loop=True,use_cond8=False),'CUR',keep=True)
d,I,tls,sect=E.load()
C=dict(E.CFG); C.update(CUR)
TOPN=build_topn(I,C['top_n'])
cal=[str(x) for x in d['cal']]; S=[str(x) for x in d['sym']]; jm={s_:k for k,s_ in enumerate(S)}
lookup._loai=lambda: set()        # history must not be filtered by today's manual list
def sl(D,i): return {k:(v[:i+1] if hasattr(v,'shape') and v.ndim in (1,2) and v.shape[0]==len(cal) else v) for k,v in D.items()}
cache={}
def lk(i):
    if i not in cache:
        cache[i]=lookup.build(sl(d,i),sl(I,i),tls,sect,C,TOPN[:i+1])
    return cache[i]
def live_eval(t,i,j,ordimb_known=True):
    """Exactly the live MUA rule (server live_scan.py, current main)."""
    close=d['PriceClose'][i,j]; basic=d['PriceBasic'][i,j]; vol=d['Volume'][i,j]; tv=d['TotalValue'][i,j]
    hi=d['PriceHigh'][i,j]; lo=d['PriceLow'][i,j]
    pct=close/basic-1; volr=vol/t['vma20'] if t['vma20'] else 0
    cond={'pct':pct*100>=t['thr'],'vol':volr>=C['vol_floor'],'gtgd':tv>=C['gtgd_min'],
          'cond8':(close>=(hi+lo)/2) if hi>lo else True}
    oi=I['ordimb'][i,j]
    return cond, (oi>=C['ordimb_min'])
res=[]; states=Counter()
entries={(x['sym'],x['date']) for x in r['signals']}
for sg in r['signals']:
    i=cal.index(sg['date']); j=jm[sg['sym']]
    L=lk(i-1); t=L.get(sg['sym'])
    st=t['state'] if t else 'absent'
    states[st]+=1
    cond,oiok=live_eval(t,i,j) if t else ({},False)
    res.append(dict(sym=sg['sym'],date=sg['date'],state=st,miss=(t or {}).get('miss'),
                    live4=all(cond.values()) if cond else False,oi_ok=bool(oiok)))
recall=sum(1 for x in res if x['state']=='cho' and x['live4'])
print('engine entries:',len(res),' lookup state night before:',dict(states))
print('live MUA (state cho + 4 intraday conds) on engine entries:',recall,'/',len(res))
miss_reasons=Counter(m for x in res if x['state']!='cho' for m in (x['miss'] or ['(blocked)']))
print('why state != cho on engine entries:',miss_reasons.most_common(8))
# precision over 2023-2026 : scan all days, every sym with state cho and 4 live conds
fp=[]; tp=0
i0=cal.index(next(c for c in cal if c>='2023-01-01'))
for i in range(i0,len(cal)):
    trig=np.where((d['PriceClose'][i]/d['PriceBasic'][i]-1)>=I['thr'])[0]
    trig=[j for j in trig if TOPN[i-1,j]]
    if not trig: continue
    L=lk(i-1)
    for j in trig:
        t=L.get(S[j])
        if not t or t['state']!='cho': continue
        cond,oiok=live_eval(t,i,j)
        if all(cond.values()):
            key=(S[j],cal[i])
            if key in entries: tp+=1
            else: fp.append(dict(sym=S[j],date=cal[i],oi_ok=bool(oiok),oi=float(I['ordimb'][i,j])))
print(f'2023-26 live-MUA(current server rule, no Cond9): engine-entries {tp}, NOT engine entries {len(fp)}; of those Cond9 fails: {sum(1 for x in fp if not x["oi_ok"])}')
print('examples:',fp[:12])
json.dump(dict(meta=meta(),entries=res,states=dict(states),recall=recall,false_mua_2023=fp),open('evidence/audit_r5_parity.json','w'),ensure_ascii=False,indent=1,default=str)
