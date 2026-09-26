# -*- coding: utf-8 -*-
"""DIAG ONLY: fresh PROD backtest -> metrics + trade list (json)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine2 as E
from produce2 import PROD
r = E.run(PROD, log=True)
m = E.metrics(r)
tr = [(t['sym'], t['entry'], t['exit'], t['pnl_pct'], t.get('reason')) for t in r['trades']]
json.dump(dict(m=m, trades=tr), open(sys.argv[1], 'w'), default=str)
print('BACKTEST', sys.argv[1], json.dumps(m))
