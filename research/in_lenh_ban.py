# -*- coding: utf-8 -*-
"""TAM. In ke hoach BAN cho phien ke tiep tu site_data2.json (engine chay tren du lieu 09/10). Chi doc."""
import json, csv
import numpy as np
D = json.load(open('data/site_data2.json', encoding='utf-8'))
z = np.load('data/fa.npz', allow_pickle=True); S = [str(s) for s in z['sym']]; i = len(z['cal']) - 1
cur = {r['symbol']: r['exchange'] for r in csv.DictReader(open('data/by_exchange.csv', encoding='utf-8'))}
def of(sym):
    j = S.index(sym) if sym in S else None
    return None if j is None else bool(z['BuyCount'][i, j] > 0 and z['SellCount'][i, j] > 0)
print('PHIEN CUOI:', str(z['cal'][i]), '| asof:', D.get('asof'))
print('\n=== LENH DA THOAT phien 08/10-09/10 (engine) ===')
for t in D.get('trades') or []:
    if str(t.get('exit', '')) >= '2026-10-08':
        print(f"  {t['sym']:5} {cur.get(t['sym'],'?'):5} vao {t['entry']} ra {t['exit']} ly do {t.get('reason')} lai {t.get('pnl_pct')}")
print('\n=== VI THE DANG CAM (engine) + KE HOACH PHIEN TOI ===')
for p in D.get('open_positions') or []:
    k = p.get('ke_hoach') or {}
    print(f"  {p['sym']:5} san {cur.get(p['sym'],'?'):5} dong_tien_09/10={of(p['sym'])}  viec={k.get('viec')} ly_do={k.get('ly_do')} "
          f"nguong={k.get('nguong')} dong_cua={k.get('dong_cua')} gia_von={k.get('gia_von')} held={k.get('held')} sell_from={k.get('sell_from')} moc={k.get('moc')}")
print('\n=== SO TAY (manual.json) ===')
for k in D.get('ke_hoach_so_tay') or []:
    print(f"  {k.get('sym'):5} san {cur.get(k.get('sym'),'?'):5} viec={k.get('viec')} ly_do={k.get('ly_do')} nguong={k.get('nguong')} dong_cua={k.get('dong_cua')}")
try:
    pf = json.load(open('data/portfolio.json', encoding='utf-8'))
    print('\n=== SO GHI TIEN (portfolio.json dang dang) mo:', [p.get('sym') for p in pf.get('open') or []], 'session_done', pf.get('session_done'))
except Exception as e:
    print('portfolio.json:', e)
