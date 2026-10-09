# -*- coding: utf-8 -*-
"""Cao NGAY CONG BO BAN DAU cua BCTC quy tu Vietstock + CafeF -> data/ngay_cong_bo.json

    {"FPT": {"vs": {"2026Q2": "2026-07-27T22:34", ...},
             "cf": {"2026Q2": "2026-07-28T09:51", ...}}, ...}

prep.parse_funda dung file nay khi bat NGAY_DA_NGUON (mac dinh TAT — anh Son
duyet so backtest truoc). Nguon hong thi ma do chi thieu nguon do; khong bao gio
lam hong day chuyen: prep tu lui ve cach cu cho quy khong co ngay.
"""
import json, os, sys, time, threading
from concurrent.futures import ThreadPoolExecutor
from sources import bctc_ngay as B

OUT = 'data/ngay_cong_bo.json'
WORKERS = 3
_lock = threading.Lock(); _ke = [0.0]
LOI = {'vs': 0, 'cf': 0}


def _cho(khoang=0.35):
    with _lock:
        now = time.monotonic(); w = max(0.0, _ke[0] - now); _ke[0] = max(now, _ke[0]) + khoang
    if w: time.sleep(w)


def _thu(fn, sym, nguon):
    for i in range(3):
        try:
            _cho(); return fn(sym)
        except Exception as e:
            err = e; time.sleep(1.5 * (i + 1))
    with _lock: LOI[nguon] += 1
    print(f'  {sym} {nguon}: {type(err).__name__}: {str(err)[:120]}', flush=True)
    return {}


def mot(sym):
    return sym, {'vs': _thu(B.vietstock, sym, 'vs'), 'cf': _thu(B.cafef, sym, 'cf')}


if __name__ == '__main__':
    u = json.load(open('data/universe.json', encoding='utf-8'))
    if len(sys.argv) > 1: u = sys.argv[1:]
    print('ngay cong bo:', len(u), 'ma', flush=True)
    out = {}
    with ThreadPoolExecutor(WORKERS) as ex:
        for i, (s, d) in enumerate(ex.map(mot, u)):
            out[s] = d
            if i % 100 == 0: print(i, s, len(d['vs']), len(d['cf']), flush=True)
    co_vs = sum(1 for d in out.values() if d['vs']); co_cf = sum(1 for d in out.values() if d['cf'])
    print(f'xong {len(out)} ma | Vietstock co {co_vs} ma (loi {LOI["vs"]}) | CafeF co {co_cf} ma (loi {LOI["cf"]})')
    try:
        import data_health as DH
        DH.put('ngay_cong_bo', dict(source='Vietstock + CafeF', status='OK' if (co_vs or co_cf) else 'FAIL',
                                    expected=len(u), vietstock=co_vs, cafef=co_cf, loi=dict(LOI)))
    except Exception as e:
        print('data_health:', e)
    if not (co_vs or co_cf):
        sys.exit('HONG: ca hai nguon ngay cong bo deu khong tra du lieu — giu file cu')
    tmp = OUT + '.tmp'
    json.dump(out, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, OUT)
