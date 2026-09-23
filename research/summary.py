"""Assemble evidence/audit_summary.json (compact, embedded in the site's admin page)."""
import sys,os,json; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from common import meta
E='evidence/'
L=lambda f: json.load(open(E+f,encoding='utf-8'))
def m(s): 
    x=s['metrics']; a=s.get('p2019_2022') or {}; b=s.get('p2023_2026') or {}
    return dict(name=s['name'],ret=x['total_return'],dd=x['maxdd'],pf=x['pf'],sh=x['sharpe'],deals=s['unique_deals'],
                r1=a.get('ret'),pf1=a.get('pf'),r2=b.get('ret'),pf2=b.get('pf'))
r1=L('audit_r1_fixes.json'); r2=L('audit_r2_exec.json'); r3=L('audit_r3_cfo.json'); r4=L('audit_r4_rank.json')
r5=L('audit_r5_parity.json'); r6=L('audit_r6_bootstrap.json')
obs=[]
for f in ('/home/claude/obs/ordimb_obs.jsonl',):
    try: obs=[{k:v for k,v in json.loads(l).items() if k not in('ordimb','sample')} for l in open(f)]
    except Exception: pass
out=dict(meta=meta(dict(note='audit 23/09/2026 — research on CUR = PROD after audit fixes')),
  baseline0=dict(git_sha='d8c27acd3cf1ecaa38edf8eb092a6e6774ed0bdc',data_asof='2026-09-23',config_hash='1f4fcbf7ec22',
                 ret=6.9677,cagr=0.3092,dd=0.0946,pf=5.84,sharpe=1.96,winrate=0.461,avg_win=22.18,avg_loss=-2.71,rr=8.19,
                 deals=116,rows=141,final_nav=7967673344),
  fixes=[m(s) for s in r1['runs']], execution=[m(s) for s in r2['exec']], forced_miss=[m(s) for s in r2['forced']],
  random_miss=r2['random'], cfo=[m(s) for s in r3['runs']],
  cfo_cohort={k:v for k,v in r3['cohort']['cohort'].items()}, cfo_cohort_deals=r3['cohort']['cohort_deals'][:25],
  ranking=[m(s) for s in r4['runs']], ranking_miss20=r4['miss20'],
  parity_old=dict(recall=r5['recall'],entries=len(r5['entries']),false_mua_2023_2026=len(r5['false_mua_2023']),
                  false_mua_cond9_fail=sum(1 for x in r5['false_mua_2023'] if not x['oi_ok'])),
  concentration=r6['concentration'],pareto=r6['pareto'],bootstrap=r6['bootstrap'],top_deals=r6['top_deals'][:10],
  cond9_obs=obs)
json.dump(out,open(E+'audit_summary.json','w'),ensure_ascii=False,indent=1,default=str)
print('ok',len(json.dumps(out))//1024,'KB')
