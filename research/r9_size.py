"""If the sector rule goes, is it really the ~30% effective entry size that earns the return?"""
import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import json
from common import pmap, line, meta
J=[(f'no sector cap, base {b:.2f}',dict(sector_cap=1.0,base_size=b)) for b in (0.26,0.28,0.30,0.32,0.34,0.36,0.42)]
J+=[(f'no sector cap, base {b:.2f} slip0.2%',dict(sector_cap=1.0,base_size=b,slip=0.002)) for b in (0.28,0.30,0.32)]
R=pmap(J,2)
for s in R: print(line(s))
json.dump(dict(meta=meta(),runs=R),open('evidence/audit_r9_size.json','w'),ensure_ascii=False,indent=1,default=str)
