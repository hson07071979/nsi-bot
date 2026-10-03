# -*- coding: utf-8 -*-
"""R34 — chot 1/3 khi lai du cao (15/20/25%), 2/3 con lai theo luat cu. Grid + Monte Carlo (miss 10%, 30 seed)."""
import os,sys,json,warnings;warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research import common as C
CF={'PROD':{}}
for t in (0.15,0.20,0.25):
    CF['Chot 1/3 @%d%% dong cua'%(t*100)]=dict(tp_part=t)
    CF['Chot 1/3 @%d%% dat lenh san'%(t*100)]=dict(tp_part=t,tp_part_mode='touch')
J=[(n,o) for n,o in CF.items()]+[(f'{n}|{s}',dict(o,miss_prob=0.10,miss_seed=s)) for n,o in CF.items() for s in range(1,31)]
res=C.pmap(J,procs=2)
for s in res[:len(CF)]: print(C.line(s),'| 2026',s['yearly'].get('2026'))
json.dump(res,open('/home/claude/w/r34_tp.json','w'),ensure_ascii=False,default=str); print('done',len(res))
