"""Sector cap sweep (anh Son 24/09: bo tran nganh neu khong giup loi nhuan)."""
import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import json
from common import pmap, line, meta
J=[]
for sc in (0.30,0.35,0.40,0.45,0.50,1.0):
    J.append((f'sector_cap {sc:.2f}',dict(sector_cap=sc)))
    J.append((f'sector_cap {sc:.2f} slip0.2%',dict(sector_cap=sc,slip=0.002)))
J.append(('NO sector cap next_open',dict(sector_cap=1.0,entry_mode='next_open')))
J.append(('sector 0.30 next_open',dict(entry_mode='next_open')))
R=pmap(J,2)
for s in R: print(line(s), '| top1', s['concentration']['top1'])
json.dump(dict(meta=meta(),runs=R),open('evidence/audit_r8_sector.json','w'),ensure_ascii=False,indent=1,default=str)
