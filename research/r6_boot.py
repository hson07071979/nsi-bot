"""Profit concentration (Pareto) + daily-return BLOCK bootstrap drawdown distribution
+ entry-cohort bootstrap, on the current PROD. Deal-shuffle kept as supplementary."""
import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import json, numpy as np
from common import run, meta
from dealstats import deals
s,r=run({},'PROD',keep=True)
eq=np.array([x[1] for x in r['eq']]); ret=np.diff(eq)/eq[:-1]; N=len(ret)
D=sorted(deals(r['trades']),key=lambda x:-x['pnl_vnd'])
w=[x['pnl_vnd'] for x in D if x['pnl_vnd']>0]; gp=sum(w)
pareto=[round(sum(w[:k])/gp,4) for k in range(1,len(w)+1)]
print('concentration:',s['concentration'])
rng=np.random.default_rng(20260923)
def mdd(path):
    v=np.cumprod(1+path); return float((1-v/np.maximum.accumulate(v)).max())
out={}
for B in (10,15,20):
    dds=[];tots=[]
    for _ in range(3000):
        k=int(np.ceil(N/B)); st=rng.integers(0,N-B+1,size=k)
        path=np.concatenate([ret[a:a+B] for a in st])[:N]
        dds.append(mdd(path)); tots.append(float(np.prod(1+path)-1))
    dds=np.array(dds)
    out[f'block{B}']=dict(p50=float(np.percentile(dds,50)),p75=float(np.percentile(dds,75)),p90=float(np.percentile(dds,90)),
        p95=float(np.percentile(dds,95)),p99=float(np.percentile(dds,99)),worst=float(dds.max()),
        **{f'P_dd_gt_{x}':float((dds>x/100).mean()) for x in (15,20,25,30)},
        ret_p5=float(np.percentile(tots,5)),ret_p50=float(np.percentile(tots,50)))
    o=out[f'block{B}']
    print(f'block {B}: DD p50 {o["p50"]:.1%} p75 {o["p75"]:.1%} p90 {o["p90"]:.1%} p95 {o["p95"]:.1%} p99 {o["p99"]:.1%} worst {o["worst"]:.1%} | P>15% {o["P_dd_gt_15"]:.1%} >20% {o["P_dd_gt_20"]:.1%} >25% {o["P_dd_gt_25"]:.1%} >30% {o["P_dd_gt_30"]:.1%} | ret p5 {o["ret_p5"]:+.0%} p50 {o["ret_p50"]:+.0%}')
# entry-cohort bootstrap: resample calendar MONTHS of entries (keeps simultaneous positions together)
from collections import defaultdict
navd={d_:v for d_,v,*_ in r['eq']}
bym=defaultdict(float)
for x in deals(r['trades']): bym[x['entry'][:7]]+=x['pnl_vnd']/navd.get(x['entry'],eq[0])
months=sorted(bym); vals=np.array([bym[m] for m in months])
res=[]
for _ in range(5000):
    path=np.cumprod(1+vals[rng.integers(0,len(vals),size=len(vals))])
    res.append(float((1-path/np.maximum.accumulate(path)).max()))
res=np.array(res)
out['entry_month_cohort']=dict(p50=float(np.percentile(res,50)),p95=float(np.percentile(res,95)),worst=float(res.max()),
    note='entry-month cohort returns (deal P&L / NAV at entry), resampled with replacement and compounded')
print('entry-month cohort DD: p50 %.1f%% p95 %.1f%% worst %.1f%%'%(out['entry_month_cohort']['p50']*100,out['entry_month_cohort']['p95']*100,out['entry_month_cohort']['worst']*100))
# supplementary: deal shuffle (destroys clustering)
p=np.array([x['pnl_pct'] for x in deals(r['trades'])])/100; f=0.30
sh=[]
for _ in range(3000):
    v=np.cumprod(1+rng.permutation(p)*f); sh.append(float((1-v/np.maximum.accumulate(v)).max()))
out['deal_shuffle_supplementary']=dict(p50=float(np.median(sh)),p95=float(np.percentile(sh,95)),size_frac=f)
print('deal-shuffle (supplementary, 30%% size): DD p50 %.1f%% p95 %.1f%%'%(np.median(sh)*100,np.percentile(sh,95)*100))
json.dump(dict(meta=meta(),concentration=s['concentration'],pareto=pareto,top_deals=D[:20],bootstrap=out,
               actual=dict(maxdd=s['metrics']['maxdd'],total=s['metrics']['total_return'])),
          open('evidence/audit_r6_bootstrap.json','w'),ensure_ascii=False,indent=1,default=str)
