# -*- coding: utf-8 -*-
"""data/data_health.json — one status block per data source, written by each
fetch step and read by verify_build.py and the admin diagnostics page."""
import json, os, datetime as dt
F = 'data/data_health.json'

def load():
    try:
        return json.load(open(F, encoding='utf-8'))
    except Exception:
        return {}

def put(name, block):
    D = load()
    b = dict(block)
    b.setdefault('updated', dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z')
    if b.get('status') == 'OK':
        b['last_success'] = b['updated']
    elif name in D and D[name].get('last_success'):
        b['last_success'] = D[name]['last_success']
    D[name] = b
    tmp = F + '.tmp'
    json.dump(D, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    os.replace(tmp, F)
