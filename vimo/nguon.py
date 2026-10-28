# -*- coding: utf-8 -*-
"""Nguồn số liệu vĩ mô — chỉ nguồn công khai, không cần khoá (28/10/2026).

  fred(id)    FRED (Fed St. Louis) qua fredgraph.csv — không cần API key. Chuỗi ngày và chuỗi tháng (IMF giá hàng hoá).
  yahoo(sym)  Yahoo Finance chart API — giá thị trường cập nhật nhanh (hợp đồng tương lai, chỉ số, tỷ giá).
  stooq(sym)  Stooq CSV — dự phòng thứ hai.
  vcb_usd()   Tỷ giá USD/VND chuyển khoản Vietcombank (XML công khai) — dự phòng trong nước cho tỷ giá.

Mọi hàm trả list[(ngày 'YYYY-MM-DD', giá trị)] tăng dần theo ngày; lỗi mạng / định dạng → [] (một nguồn hỏng không làm
sập cả buổi). Không bao giờ ném lỗi ra ngoài.
"""
from __future__ import annotations

import csv
import io
import re
import time
from datetime import datetime, timedelta, timezone

import requests

VN = timezone(timedelta(hours=7))
UA = 'Mozilla/5.0 (compatible; nsi-vimo/1.0; +https://nguyensonfinance.com.vn)'
LOI: list[str] = []          # nhật ký lỗi nguồn của lượt chạy (in ra log, ghi vào tóm tắt)


def _get(url: str, params: dict | None = None, tries: int = 3, timeout: int = 25) -> requests.Response | None:
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={'User-Agent': UA})
            if r.status_code == 200:
                return r
            last = f'HTTP {r.status_code}'
            if r.status_code in (403, 404):
                break
        except requests.RequestException as e:        # noqa: PERF203
            last = str(e)[:120]
        time.sleep(2 * (i + 1))
    LOI.append(f'{url.split("?")[0]} {params or ""}: {last}')
    return None


def _so(x) -> float | None:
    try:
        v = float(str(x).replace(',', ''))
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def doc_csv_fred(text: str) -> list[tuple[str, float]]:
    out = []
    for r in csv.reader(io.StringIO(text)):
        if len(r) < 2 or not re.match(r'\d{4}-\d{2}-\d{2}$', r[0]):
            continue
        v = _so(r[1])
        if v is not None:
            out.append((r[0], v))
    return out


def fred(sid: str) -> list[tuple[str, float]]:
    r = _get('https://fred.stlouisfed.org/graph/fredgraph.csv', {'id': sid})
    return doc_csv_fred(r.text) if r is not None else []


def doc_json_yahoo(j: dict) -> list[tuple[str, float]]:
    try:
        res = j['chart']['result'][0]
        ts, cl = res['timestamp'], res['indicators']['quote'][0]['close']
    except (KeyError, IndexError, TypeError):
        return []
    d = {}
    for t, c in zip(ts, cl):
        if c is not None:
            d[datetime.fromtimestamp(t, VN).date().isoformat()] = float(c)
    return sorted(d.items())


def yahoo(sym: str, rng: str = '5y') -> list[tuple[str, float]]:
    for host in ('query1', 'query2'):
        r = _get(f'https://{host}.finance.yahoo.com/v8/finance/chart/{sym}', {'range': rng, 'interval': '1d'}, tries=2)
        if r is not None:
            try:
                s = doc_json_yahoo(r.json())
            except ValueError:
                s = []
            if s:
                return s
    return []


def doc_csv_stooq(text: str) -> list[tuple[str, float]]:
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        d, c = r.get('Date') or r.get('Data'), _so(r.get('Close') or r.get('Zamkniecie'))
        if d and c is not None and re.match(r'\d{4}-\d{2}-\d{2}$', d):
            out.append((d, c))
    return out


def stooq(sym: str) -> list[tuple[str, float]]:
    r = _get('https://stooq.com/q/d/l/', {'s': sym, 'i': 'd'}, tries=2)
    return doc_csv_stooq(r.text) if r is not None else []


def doc_xml_vcb(text: str) -> list[tuple[str, float]]:
    m = re.search(r'<DateTime>(\d+)/(\d+)/(\d{4})', text)
    u = re.search(r'CurrencyCode="USD"[^>]*Transfer="([\d,\.]+)"', text)
    if not (m and u):
        return []
    v = _so(u.group(1))
    return [(f'{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}', v)] if v else []


def vcb_usd() -> list[tuple[str, float]]:
    r = _get('https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx', tries=2)
    return doc_xml_vcb(r.text) if r is not None else []


NGUON = dict(fred=fred, yahoo=yahoo, stooq=stooq, vcb=lambda _=None: vcb_usd())
