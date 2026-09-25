# -*- coding: utf-8 -*-
"""R14 — Is Condition 9 executable? (anh Son 25/09). The backtest buys at the CLOSE of the
signal session using that session's order counts, which exchanges publish only AFTER the
close (R10). Compare the theoretical PROD with entries a real trader can actually place."""
import os, sys, json
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
import engine2 as E
from produce2 import PROD
from dealstats import stats as DS
from research.common import meta
SC = [
    ('A. Lý thuyết: mua giá đóng cửa, đã biết ĐK9', dict(stage1=None)),
    ('B. Chờ ĐK9 (tối) → mua giá MỞ CỬA phiên sau', dict(stage1=None, entry_mode='next_open')),
    ('C. Chờ ĐK9 (tối) → mua giá TRUNG BÌNH phiên sau', dict(stage1=None, entry_mode='next_vwap')),
    ('D. Bỏ hẳn ĐK9, mua giá đóng cửa (ATC)', dict(stage1=None, use_ordimb=False)),
    ('E1. Hai bước: mua 30% lúc ATC không cần ĐK9, sáng sau đủ ĐK9 thì mua nốt, không đủ thì bán T+2', dict(stage1=0.3, probe_exit='close')),
    ('E2. Hai bước 50%', dict(stage1=0.5, probe_exit='close')),
    ('E3. Mua dò đủ lệnh lúc ATC, trượt ĐK9 thì bán ATC T+2 (PROD 25/09)', dict(stage1=1.0, probe_exit='close')),
    ('E4. E3 + lọc KL đặt mua/bán ≥ 1,2 trước ATC', dict(stage1=1.0, probe_exit='close', pre_proxy='qty', pre_min=1.2)),
]
def run(o):
    C = dict(E.CFG); C.update(PROD); C.update(o); return C, E.run(C, log=False)
out = []
for name, o in SC:
    C, r = run(o); m = E.metrics(r); d = DS(r['trades'])
    eq = r['eq']; seg = lambda a, b: (lambda v: v[-1] / v[0] - 1)([x[1] for x in eq if a <= x[0][:4] <= b])
    mc = [E.metrics(E.run(dict(C, miss_prob=0.1, miss_seed=9000 + s), log=False))['total_return'] for s in range(60)]
    sl = E.metrics(E.run(dict(C, slip=0.002), log=False))
    row = dict(name=name, cfg={k: v for k, v in o.items()}, ret=m['total_return'], cagr=m['cagr'], dd=m['maxdd'], pf=m['pf'], sharpe=m['sharpe'],
               deals=d.get('deals'), wr=d.get('winrate'), h1=seg('2019', '2022'), h2=seg('2023', '2026'),
               mc_p50=float(np.median(mc)), mc_p10=float(np.quantile(mc, .1)), slip_ret=sl['total_return'], slip_dd=sl['maxdd'])
    out.append(row)
    print('%-95s ret %7.1f%% dd %5.2f%% pf %5.2f sh %4.2f deals %s | 19-22 %6.1f%% 23-26 %6.1f%% | MC %6.1f%% p10 %6.1f%% | slip %6.1f%%' % (
        name, row['ret']*100, row['dd']*100, row['pf'], row['sharpe'], row['deals'], row['h1']*100, row['h2']*100,
        row['mc_p50']*100, row['mc_p10']*100, row['slip_ret']*100), flush=True)
json.dump(dict(meta=meta(dict(experiment_version='audit-2026-09-25/r14', note='new PROD 25/09')), rows=out),
          open('evidence/audit_r14_cond9_feasible.json', 'w'), ensure_ascii=False, indent=1, default=float)
