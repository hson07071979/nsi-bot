"""CafeF 'Thong ke dat lenh' (order-placement statistics) - public, no auth.
URL: https://cafef.vn/du-lieu/Ajax/PageNew/DataHistory/ThongKeDL.ashx?Symbol=HPG&StartDate=&EndDate=&PageIndex=1&PageSize=N
StartDate/EndDate format dd/mm/yyyy (optional). Fields: SoLenhMua, KLDatMua, SoLenhDatBan, KLDatBan.
Usage: python probe_cafef.py HPG SHS [--date 2026-09-23] [--days 5]
"""
import sys, json, datetime, argparse, time, requests
URL = "https://cafef.vn/du-lieu/Ajax/PageNew/DataHistory/ThongKeDL.ashx"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://cafef.vn/du-lieu/lich-su-giao-dich-vnindex-2.chn"}

def fetch_rows(symbol, days=5, start=None, end=None, retries=3):
    p = {"Symbol": symbol, "StartDate": start or "", "EndDate": end or "", "PageIndex": 1, "PageSize": days}
    for i in range(retries):
        try:
            r = requests.get(URL, params=p, headers=UA, timeout=20)
            r.raise_for_status()
            return r.json()["Data"]["Data"] or []
        except Exception:
            if i == retries - 1: raise
            time.sleep(1.5)

def ordimb(bq, bc, sq, sc):
    try:
        return (bq / bc) / (sq / sc) if bc and sc and sq else None
    except ZeroDivisionError:
        return None

def probe(symbol, date=None, days=5):
    fetched = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).isoformat(timespec="seconds")
    out = []
    try:
        rows = fetch_rows(symbol, days)
    except Exception as e:
        return [{"source": "cafef", "symbol": symbol, "fetched_at": fetched, "available": False, "error": str(e)}]
    for r in rows:
        d = datetime.datetime.strptime(r["Date"], "%d/%m/%Y").date().isoformat()
        if date and d != date: continue
        bc, bq, sc, sq = r["SoLenhMua"], r["KLDatMua"], r["SoLenhDatBan"], r["KLDatBan"]
        oi = ordimb(bq, bc, sq, sc)
        out.append({"source": "cafef", "symbol": symbol, "fetched_at": fetched, "date": d,
                    "BuyCount": bc, "BuyQuantity": bq, "SellCount": sc, "SellQuantity": sq,
                    "ordimb_or_proxy": oi, "available": oi is not None})
    if date and not out:
        out.append({"source": "cafef", "symbol": symbol, "fetched_at": fetched, "date": date, "available": False})
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("symbols", nargs="+"); ap.add_argument("--date"); ap.add_argument("--days", type=int, default=5)
    a = ap.parse_args()
    res = {s: probe(s, a.date, a.days) for s in a.symbols}
    print(json.dumps(res, ensure_ascii=False, indent=1))
