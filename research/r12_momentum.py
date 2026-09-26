# -*- coding: utf-8 -*-
"""R12 — Momentum exits after a breakout (anh Son 25/09): "đã mua break thì phải chạy luôn,
không chạy thì ra". One knob at a time on top of START (R11 optimum), same robustness rules
as R11 (research/r11_mc_opt.py). Knobs (engine2, default off = PROD):
  mo_stop / mo_stop_until : early cut at -x% while held <= N sessions (sale allowed from T+2)
  mo_by / mo_need         : by session T+k the trade must have reached +g% at some close, else out
  valve_min / t_valve     : time valve threshold (PROD: T+4, gain <= 0)
  be_trigger / be_level   : break-even lock (PROD: peak >= 8% then back to 1%)"""
import os, sys
os.environ.setdefault('CACHE', 'evidence/r12_cache.json')
os.environ.setdefault('OUT', 'evidence/r12_progress.json')
os.environ.setdefault('START', '{"trig_hose": 0.056, "dk5_hi": 0.0, "base_range": 0.24}')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r11_mc_opt as R
R.STEPS = [
    ('mo_stop', [None, -0.015, -0.02, -0.025, -0.03, -0.035, -0.04, -0.05]),
    ('mo_stop_until', [2, 3, 4, 5, 6, 8]),
    ('mo_need', [0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06]),     # by T+mo_by
    ('mo_by', [2, 3, 4, 5, 6]),
    ('t_valve', [3, 4, 5, 6, 8]),
    ('valve_min', [-0.01, 0.0, 0.01, 0.02, 0.03]),
    ('be_trigger', [0.04, 0.05, 0.06, 0.07, 0.08, 0.10, 0.12]),
    ('be_level', [0.0, 0.005, 0.01, 0.02, 0.03]),
]
R.DEF.update(mo_stop=None, mo_stop_until=4, mo_need=0.0, mo_by=3, t_valve=4, valve_min=0.0,
             be_trigger=0.08, be_level=0.01)
_ex = R.extra_for
def extra_for(knob):
    if knob == 'mo_need':           # rule needs mo_by; 0.0 == off
        return lambda v: dict(mo_by=3) if v else {}
    return _ex(knob)
R.extra_for = extra_for
if __name__ == '__main__':
    R.main()
