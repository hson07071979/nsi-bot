import json, sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import pmap, line, meta
J=[('BASELINE_0 (PROD)',{}),
   ('pyr_caps',dict(pyr_caps=True)),
   ('max_n_in_loop',dict(max_n_in_loop=True)),
   ('pyr_caps+max_n',dict(pyr_caps=True,max_n_in_loop=True)),
   ('cond8 OFF',dict(use_cond8=False)),
   ('cond9 OFF (A/B ref)',dict(use_ordimb=False)),
   ('hard stop from T+0 (counterfactual)',dict(hs_from=0)),
   ('PROD slip0.2%',dict(slip=0.002)),
   ('pyr_caps+max_n slip0.2%',dict(pyr_caps=True,max_n_in_loop=True,slip=0.002)),
   ('cond8 OFF slip0.2%',dict(use_cond8=False,slip=0.002)),
]
R=pmap(J,2)
for s in R: print(line(s))
json.dump(dict(meta=meta(),runs=R),open('evidence/audit_r1_fixes.json','w'),ensure_ascii=False,indent=1)
