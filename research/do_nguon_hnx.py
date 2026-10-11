# -*- coding: utf-8 -*-
"""Do nguon thu 3 cho dong tien HNX (tam). Doi chung Vietstock (ExchangeID 1/2/3) + CafeF voi hnx.vn."""
import json, sys, os, re, datetime, traceback, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sources import hnx, vietstock, cafef
F = ('BuyCount', 'BuyQuantity', 'SellCount', 'SellQuantity')
SYMS = [('SHS', 'NY'), ('PVS', 'NY'), ('CEO', 'NY'), ('MBS', 'NY'), ('IDC', 'NY'), ('ACV', 'UC'), ('BSR', 'UC')]

def vs(sym, exid):
    s, tok = vietstock._session()
    d = {"Code": sym, "OrderBy": "", "OrderDirection": "desc", "PageIndex": 1, "PageSize": 10,
         "FromDate": "2026-09-25", "ToDate": "2026-10-11", "ExportType": "default",
         "Cols": "LDM,LDB,KLDM,KLDB,TKLGD", "ExchangeID": exid, "__RequestVerificationToken": tok}
    out = {}
    for r in s.post(vietstock.BASE + "/data/gettradingresult", data=d, timeout=30).json().get("Data") or []:
        ms = int(re.search(r"\d+", r["TradingDate"]).group())
        day = (datetime.datetime.utcfromtimestamp(ms / 1000) + datetime.timedelta(hours=7)).date().isoformat()
        out[day] = dict(BuyCount=r["TotalBuyTrade"], BuyQuantity=r["TotalBuyVol"], SellCount=r["TotalSellTrade"], SellQuantity=r["TotalSellVol"])
    return out

def cf(sym):
    out = {}
    for r in cafef.fetch_rows(sym, days=10) or []:
        day = datetime.datetime.strptime(r["Date"], "%d/%m/%Y").date().isoformat()
        out[day] = dict(BuyCount=r["SoLenhMua"], BuyQuantity=r["KLDatMua"], SellCount=r["SoLenhDatBan"], SellQuantity=r["KLDatBan"])
    return out

def cmp(name, ref, got):
    tot = ok = 0; lines = []
    for day, rr in sorted(ref.items()):
        g = got.get(day)
        if not g: continue
        tot += 1
        d = {k: (float(g[k]) / rr[k] - 1) if rr[k] and g.get(k) is not None else None for k in F}
        good = all(v is not None and abs(v) <= 0.01 for v in d.values()); ok += good
        lines.append(f'{day} {"OK " if good else "LECH"} ' + ' '.join(f'{k}={g.get(k)}/{rr[k]:.0f}' for k in F))
    print(f'  {name}: {ok}/{tot} phien khop (<=1%), co ngay 2026-10-09: {"2026-10-09" in got}')
    for l in lines[:3]: print('    ', l)

for s, m in SYMS:
    print(f'\n##### {s} ({m})')
    try:
        _, rows, _ = hnx.cungcau(s, m, n=10); ref = {r['date']: r for r in rows}
        print('  hnx.vn ngay moi nhat:', max(ref) if ref else None)
    except Exception:
        traceback.print_exc(); continue
    for ex in (1, 2, 3):
        try: cmp(f'vietstock ExchangeID={ex}', ref, vs(s, ex))
        except Exception as e: print(f'  vietstock ExchangeID={ex} loi: {e}')
    try: cmp('cafef', ref, cf(s))
    except Exception as e: print('  cafef loi:', e); traceback.print_exc()
