import sys,os; sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, engine2 as E
from produce2 import PROD
# instrument: count pyramid events and sector exposure after add in baseline
import allocator
d,I,tls,sect=E.load()
orig=E.run
r=E.run(dict(PROD),log=True)
# reconstruct: signals size vs 30% cap
import collections
sz=[s['size_pct'] for s in r['signals']]
print('entry size pct: max %.1f  share >=29%%: %.2f'%(max(sz),np.mean([x>=29 for x in sz])))
print(collections.Counter(s['binding'] for s in r['signals']))
