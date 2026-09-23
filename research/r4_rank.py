import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import json, numpy as np
from common import pmap, line, meta, run
import engine2 as E
CUR=dict(pyr_caps=True,max_n_in_loop=True,use_cond8=False)
def c(**k): x=dict(CUR); x.update(k); return x
J=[]
for rm in E.RANKERS:
    J.append((f'rank {rm}',c(rank_mode=rm)))
    J.append((f'rank {rm} slip0.2%',c(rank_mode=rm,slip=0.002)))
    J.append((f'rank {rm} next_open',c(rank_mode=rm,entry_mode='next_open')))
R=pmap(J,2)
for s in R: print(line(s))
# random-miss robustness for each ranker (10 seeds, 20% miss)
J2=[(f'rank {rm} miss20 s{sd}',c(rank_mode=rm,miss_prob=0.2,miss_seed=sd)) for rm in E.RANKERS for sd in range(10)]
R2=pmap(J2,2)
agg={}
for rm in E.RANKERS:
    xs=[s for s in R2 if s['name'].startswith(f'rank {rm} miss20')]
    agg[rm]=dict(ret_med=float(np.median([s['metrics']['total_return'] for s in xs])),
                 pf_med=float(np.median([s['metrics']['pf'] for s in xs])),
                 dd_med=float(np.median([s['metrics']['maxdd'] for s in xs])))
    print(f'{rm:14s} miss20%: ret med {agg[rm]["ret_med"]*100:+.0f}% PF med {agg[rm]["pf_med"]:.2f} DD med {agg[rm]["dd_med"]*100:.1f}%')
# same-day competition study (CUR ranking) with forward outcomes
s0,r0=run(c(log_cands=True),'CUR',keep=True)
d=r0['d']; AC=d['AdjClose']; S=[str(x) for x in d['sym']]; jm={s:k for k,s in enumerate(S)}
comp=[]
for day in r0['cands']:
    if len(day['cands'])<2: continue
    i=day['i']; rows=[]
    for x in day['cands']:
        j=jm[x['sym']]
        f10=AC[min(i+10,len(AC)-1),j]/AC[i,j]-1; f20=AC[min(i+20,len(AC)-1),j]/AC[i,j]-1
        w=AC[i+1:i+21,j]; mfe=np.nanmax(w)/AC[i,j]-1 if len(w) else np.nan
        rows.append(dict(x,f10=round(float(f10),4),f20=round(float(f20),4),mfe20=round(float(mfe),4)))
    comp.append(dict(date=day['date'],light=day['light'],cands=rows))
bound=[c_ for c_ in comp if any(not r['taken'] for r in c_['cands'])]
tk=[r['f20'] for c_ in bound for r in c_['cands'] if r['taken']]
nt=[r['f20'] for c_ in bound for r in c_['cands'] if not r['taken']]
print(f'days with >=2 candidates: {len(comp)} ; days where capital/caps excluded someone: {len(bound)}')
print(f'  taken   n={len(tk)} f20 mean {np.mean(tk)*100:+.1f}% median {np.median(tk)*100:+.1f}%')
print(f'  skipped n={len(nt)} f20 mean {np.mean(nt)*100:+.1f}% median {np.median(nt)*100:+.1f}%')
from collections import Counter
print('  skip reasons:',Counter(r['why'] for c_ in bound for r in c_['cands'] if not r['taken']))
# rank-bucket (within-day percentile of score) vs forward return, all multi-candidate days
def bucket(key,hb=True):
    b={0:[],1:[],2:[]}
    for c_ in comp:
        xs=c_['cands']; v=[x[key] for x in xs]; pr=E._pr(v,hb)
        for x,p in zip(xs,pr): b[min(2,int(p*3))].append(x['f20'])
    return {k:(len(v),round(float(np.mean(v))*100,1) if v else None) for k,v in b.items()}
for k,hb in (('sc',True),('base',False),('oi',True),('volr',True),('rs',True),('pct',True)):
    print(f'  rank bucket by {k:5s} (0=worst third..2=best): n,f20%:',bucket(k,hb))
json.dump(dict(meta=meta(dict(base='PROD+pyr_caps+max_n_in_loop+cond8off')),runs=R,miss20=agg,competition=comp),
          open('evidence/audit_r4_rank.json','w'),ensure_ascii=False,indent=1,default=str)
