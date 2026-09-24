import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import json, numpy as np, datetime as dt
from collections import Counter
from common import pmap, line, meta, run
import engine2 as E, engine as EN
from dealstats import deals
CUR=dict()   # = PROD (pyr_caps=False, max_n_in_loop=True, use_cond8=False) since 24/09
def c(**k): x=dict(CUR); x.update(k); return x
J=[]
for sl in (0.0,0.002):
    t='' if sl==0 else ' slip0.2%'
    J+=[('CFO_HARD'+t,c(slip=sl)),('CFO_OFF'+t,c(cfo_mode='off',slip=sl)),
        ('CFO_WARN 0.35'+t,c(cfo_mode='warn',cfo_warn_mul=0.35,slip=sl)),
        ('CFO_WARN 0.50'+t,c(cfo_mode='warn',cfo_warn_mul=0.5,slip=sl)),
        ('CFO_WARN 0.65'+t,c(cfo_mode='warn',cfo_warn_mul=0.65,slip=sl)),
        ('CFO_SECTOR 0.50'+t,c(cfo_mode='sector',cfo_warn_mul=0.5,slip=sl)),
        ('CFO_REPEAT 0.50'+t,c(cfo_mode='repeat',cfo_warn_mul=0.5,slip=sl)),
        ('CFO_REPEAT 1.00'+t,c(cfo_mode='repeat',cfo_warn_mul=1.0,slip=sl))]
J+=[('CFO_HARD next_open',c(entry_mode='next_open')),('CFO_OFF next_open',c(cfo_mode='off',entry_mode='next_open')),
    ('CFO_WARN0.5 next_open',c(cfo_mode='warn',entry_mode='next_open'))]
R=pmap(J,2)
for s in R: print(line(s))
# ---- cohort admitted only because CFO veto removed ----
d,I,tls,sect=E.load()
EN.CFG['cfo_mode']='hard'
s_off,r_off=run(c(cfo_mode='off'),'CFO_OFF',keep=True)
EN.CFG['cfo_mode']='hard'
def blocked_by_cfo(sym,date):
    f=E.as_of(tls.get(sym),dt.date.fromisoformat(date)) if tls.get(sym) else None
    if f is None: return False
    EN.CFG['cfo_mode']='hard'; b,w,_=EN.risk_gate(sym,f)
    return b and w=='CFO < 0'
D=deals(r_off['trades'])
coh=[x for x in D if blocked_by_cfo(x['sym'],x['entry'])]
rest=[x for x in D if not blocked_by_cfo(x['sym'],x['entry'])]
def st(X):
    p=np.array([x['pnl_pct'] for x in X]); v=np.array([x['pnl_vnd'] for x in X])
    if not len(p): return {}
    gp=v[v>0].sum(); gl=-v[v<0].sum(); w=sorted(v[v>0],reverse=True)
    return dict(n=len(X),winrate=round(float((p>0).mean()),3),pf=round(float(gp/gl),2) if gl else None,
      avg=round(float(p.mean()),2),median=round(float(np.median(p)),2),avg_loss=round(float(p[p<=0].mean()),2) if (p<=0).any() else None,
      worst=round(float(p.min()),2),best=round(float(p.max()),2),top1_share=round(float(w[0]/gp),3) if w else None,
      top3_share=round(float(sum(w[:3])/gp),3) if w else None,net_mvnd=round(float(v.sum()/1e6)),
      held_med=float(np.median([x['held'] for x in X])),
      sectors=dict(Counter(sect.get(x['sym'],'Khác') for x in X).most_common()),
      years=dict(Counter(x['entry'][:4] for x in X)))
out=dict(cohort=st(coh),rest=st(rest),cohort_deals=sorted(coh,key=lambda x:-x['pnl_vnd']))
print('CFO-only cohort:',json.dumps(out['cohort'],ensure_ascii=False))
print('others        :',json.dumps({k:v for k,v in out['rest'].items() if k not in('sectors','years')},ensure_ascii=False))
print('cohort top:',[(x['sym'],x['entry'],x['pnl_pct']) for x in out['cohort_deals'][:8]])
print('cohort worst:',[(x['sym'],x['entry'],x['pnl_pct']) for x in sorted(coh,key=lambda x:x['pnl_pct'])[:5]])
json.dump(dict(meta=meta(dict(base='PROD')),runs=R,cohort=out),open('evidence/audit_r3_cfo.json','w'),ensure_ascii=False,indent=1,default=str)
