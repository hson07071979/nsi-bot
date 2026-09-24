import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import json, numpy as np
from common import pmap, line, meta, run
from dealstats import deals
CUR=dict()   # = PROD (pyr_caps=False, max_n_in_loop=True, use_cond8=False) since 24/09
def c(**k): x=dict(CUR); x.update(k); return x
J=[('CUR signal close',c()),
   ('signal high',c(entry_mode='signal_high')),
   ('signal high +0.2% slip',c(entry_mode='signal_high',slip_buy=0.002)),
   ('same-session VWAP',c(entry_mode='same_vwap')),
   ('close +0.2% slip (both sides)',c(slip=0.002)),
   ('next open',c(entry_mode='next_open')),
   ('next VWAP',c(entry_mode='next_vwap')),
   ('fill 75%',c(fill_ratio=0.75)),('fill 50%',c(fill_ratio=0.5)),('fill 25%',c(fill_ratio=0.25)),
   ('two-stage 25% + confirm',c(stage1=0.25)),('two-stage 50% + confirm',c(stage1=0.5)),
   ('two-stage 75% + confirm',c(stage1=0.75)),
   ('two-stage 50% +0.2% slip',c(stage1=0.5,slip=0.002)),
]
R=pmap(J,2)
for s in R: print(line(s))
# forced misses of top winners (deal-level, CUR run)
s0,r0=run(CUR,'CUR',keep=True)
D=sorted(deals(r0['trades']),key=lambda x:-x['pnl_vnd'])
J2=[(f'force-miss top {k}',c(force_miss=[(x['sym'],x['entry']) for x in D[:k]])) for k in (1,3,5,10)]
R2=pmap(J2,2)
for s in R2: print(line(s))
print('top winners:',[(x['sym'],x['entry'],round(x['pnl_vnd']/1e6),x['pnl_pct']) for x in D[:10]])
# random misses: 20 seeds each
J3=[(f'miss {int(p*100)}% seed{sd}',c(miss_prob=p,miss_seed=sd)) for p in (0.05,0.10,0.20,0.30) for sd in range(20)]
R3=pmap(J3,2)
agg={}
for p in (5,10,20,30):
    xs=[s for s in R3 if s['name'].startswith(f'miss {p}% ')]
    tr=np.array([s['metrics']['total_return'] for s in xs]); dd=np.array([s['metrics']['maxdd'] for s in xs]); pf=np.array([s['metrics']['pf'] for s in xs])
    agg[p]=dict(ret_p10=float(np.percentile(tr,10)),ret_med=float(np.median(tr)),ret_p90=float(np.percentile(tr,90)),
                dd_med=float(np.median(dd)),dd_max=float(dd.max()),pf_med=float(np.median(pf)),pf_min=float(pf.min()))
    print(f'miss {p}%: ret p10 {agg[p]["ret_p10"]*100:+.0f}% med {agg[p]["ret_med"]*100:+.0f}% p90 {agg[p]["ret_p90"]*100:+.0f}% | DD med {agg[p]["dd_med"]*100:.1f}% max {agg[p]["dd_max"]*100:.1f}% | PF med {agg[p]["pf_med"]:.2f} min {agg[p]["pf_min"]:.2f}')
json.dump(dict(meta=meta(dict(base='PROD')),exec=R,forced=R2,random=agg,
               top_winners=D[:10]),open('evidence/audit_r2_exec.json','w'),ensure_ascii=False,indent=1,default=str)
