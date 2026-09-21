# -*- coding: utf-8 -*-
"""
Cao bao cao tai chinh tu Vietcap IQ.

LOI DA SUA (20/08/2026)
- Ban cu KHONG CO THU LAI.
- Mot loi mang thoang qua (ConnectionResetError) co the lam mot ma mat sach
  bao cao ket qua kinh doanh.
- rev_yoy / npat_yoy / cagr3 thanh None, keo diem CANSLIM xuong ma khong bao loi.

Do thuc te:
- 41/694 ma tung bi dinh loi mang.
- Co BID, HPG, VCI, LPB, GEX, IDC.
- LPB thang 4/2026 chi duoc 44,5 diem thay vi qua san 45 do mat du lieu growth.

Ban 20/08:
- Retry 4 lan cho tung request.
- Chan chuong trinh neu ty le thieu KQKD > 3%.

VA 21/09/2026:
1. Them chan doan HTTP / Exception thay vi nuot loi.
2. Them browser-like headers: Origin / Referer / Accept-Language.
3. Giam burst request: 4 workers + global throttle.
4. Probe 3 ma lon truoc khi cao toan bo universe.
5. Neu probe khong lay duoc KQKD -> fail fast.
6. KHONG ghi de funda_raw2.json neu integrity check that bai.
7. Van giu hard fail neu >3% universe bi thieu KQKD.

KHONG thay doi bat ky trading rule / scoring threshold nao.
"""

import json
import os
import sys
import time
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import requests


# ============================================================
# CONFIG
# ============================================================

H = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://iq.vietcap.com.vn",
    "Referer": "https://iq.vietcap.com.vn/",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

B = "https://iq.vietcap.com.vn/api/iq-insight-service/v1/company/"

TRIES = 4
WORKERS = 4

# Khoang cach toi thieu giua HAI request bat ky cua TOAN chuong trinh.
# 0.18s ~= toi da 5.5 request/s.
MIN_INTERVAL = 0.18

MAX_MISSING_IS = 0.03

TARGET_FILE = "data/funda_raw2.json"
TEMP_FILE = "data/funda_raw2.json.tmp"


# ============================================================
# THREAD-SAFE DIAGNOSTICS
# ============================================================

_err_lock = threading.Lock()
_err_counts = Counter()
_err_sample = {}


def _note_err(msg, url):
    """Dem loi va giu lai 1 URL vi du moi loai."""
    with _err_lock:
        _err_counts[msg] += 1
        _err_sample.setdefault(msg, url)


def _clean_preview(text, limit=180):
    """Rut gon response de log khong bi qua dai."""
    if text is None:
        return ""

    s = " ".join(
        str(text)
        .replace("\r", " ")
        .replace("\n", " ")
        .split()
    )

    return s[:limit]


# ============================================================
# GLOBAL RATE LIMIT
# ============================================================

_rate_lock = threading.Lock()
_next_request_at = 0.0


def _throttle():
    """
    Global throttle:
    du 4 worker cung chay thi request van cach nhau MIN_INTERVAL.
    """
    global _next_request_at

    with _rate_lock:
        now = time.monotonic()

        if now < _next_request_at:
            wait = _next_request_at - now
        else:
            wait = 0.0

        base = max(now, _next_request_at)
        _next_request_at = base + MIN_INTERVAL

    if wait > 0:
        time.sleep(wait)


# ============================================================
# PER-THREAD SESSION
# ============================================================

_tls = threading.local()


def _session():
    """
    Moi worker dung mot requests.Session rieng.
    Session giup reuse connection nhung khong share Session cross-thread.
    """
    s = getattr(_tls, "session", None)

    if s is None:
        s = requests.Session()
        s.headers.update(H)
        _tls.session = s

    return s


# ============================================================
# HTTP
# ============================================================

def _get(url, params=None):
    """
    GET co retry.

    Return:
        dict/list JSON neu thanh cong
        None neu:
          - 400/404
          - that bai sau TRIES lan

    Moi failure that sau retry duoc ghi vao diagnostic counter.
    """

    last_err = None

    for attempt in range(TRIES):
        retry_after = None

        try:
            _throttle()

            r = _session().get(
                url,
                params=params,
                timeout=45,
            )

            status = r.status_code

            # ---------------- SUCCESS ----------------
            if status == 200:
                try:
                    payload = r.json()

                except Exception as e:
                    last_err = (
                        "HTTP 200 but invalid JSON: "
                        f"{type(e).__name__}: {e}; "
                        f"body={_clean_preview(r.text)!r}"
                    )

                else:
                    # Vietcap IQ thuong tra:
                    # {"successful": true, "data": ...}
                    if (
                        isinstance(payload, dict)
                        and payload.get("successful") is False
                    ):
                        last_err = (
                            "HTTP 200 API successful=false: "
                            f"{_clean_preview(payload.get('msg'))!r}"
                        )

                    else:
                        return payload

            # ---------------- LEGIT MISSING ----------------
            elif status in (400, 404):
                return None

            # ---------------- OTHER HTTP ERRORS ----------------
            else:
                last_err = (
                    f"HTTP {status}: "
                    f"{_clean_preview(r.text)!r}"
                )

                if status == 429:
                    ra = r.headers.get("Retry-After")

                    if ra:
                        try:
                            retry_after = float(ra)
                        except Exception:
                            pass

        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"

        # Backoff
        sleep_for = 1.5 * (attempt + 1)

        if retry_after is not None:
            sleep_for = max(
                sleep_for,
                retry_after,
            )

        time.sleep(sleep_for)

    if last_err:
        full_url = url

        if params:
            full_url += f" params={params}"

        _note_err(
            last_err,
            full_url,
        )

    return None


# ============================================================
# FETCH ONE TICKER
# ============================================================

def one(sym):
    out = {}

    # Financial ratios
    j = _get(
        B + sym + "/statistics-financial"
    )

    if isinstance(j, dict):
        out["ratio"] = j.get("data") or []
    else:
        out["ratio"] = []

    # Financial statements
    for sec, key in [
        ("INCOME_STATEMENT", "is"),
        ("CASH_FLOW", "cf"),
    ]:
        j = _get(
            B + sym + "/financial-statement",
            {
                "section": sec
            },
        )

        if isinstance(j, dict):
            data = j.get("data") or {}

            if isinstance(data, dict):
                out[key] = (
                    data.get("quarters") or []
                )

            else:
                out[key] = []

        else:
            out[key] = []

    return sym, out


# ============================================================
# DIAGNOSTICS
# ============================================================

def print_errors():
    if not _err_counts:
        print(
            "\nKhong ghi nhan HTTP/Exception failure sau retry.",
            flush=True,
        )
        return

    print(
        "\nLy do request that bai sau khi retry "
        "(top 10, kem 1 URL vi du):",
        flush=True,
    )

    for msg, count in _err_counts.most_common(10):
        print(
            f"  {count:4d}x  {msg}",
            flush=True,
        )

        print(
            f"         vd: {_err_sample[msg]}",
            flush=True,
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Universe
    # --------------------------------------------------------

    with open(
        "data/universe.json",
        encoding="utf-8",
    ) as f:
        u = json.load(f)

    print(
        "n",
        len(u),
        flush=True,
    )

    if not u:
        sys.exit(
            "HONG: universe.json rong"
        )

    # --------------------------------------------------------
    # PRE-FLIGHT TEST
    #
    # Neu API / WAF dang chan GitHub Actions
    # hoac endpoint KQKD bi hong thi dung ngay.
    # --------------------------------------------------------

    preferred_probes = [
        "FPT",
        "VCB",
        "HPG",
    ]

    probes = [
        s
        for s in preferred_probes
        if s in u
    ]

    if len(probes) < 3:
        for s in u:
            if s not in probes:
                probes.append(s)

            if len(probes) >= 3:
                break

    print(
        "\nPRE-FLIGHT Vietcap IQ:",
        ", ".join(probes),
        flush=True,
    )

    probe_res = {}

    for sym in probes:
        s, d = one(sym)

        probe_res[s] = d

        print(
            f"  {s}: "
            f"ratio={len(d['ratio'])} "
            f"is={len(d['is'])} "
            f"cf={len(d['cf'])}",
            flush=True,
        )

    # Chi coi la PASS neu lay duoc INCOME STATEMENT.
    # Ratio co du lieu ma KQKD rong thi van la loi nghiem trong.
    probe_ok = sum(
        1
        for d in probe_res.values()
        if d["is"]
    )

    if probe_ok == 0:
        print_errors()

        sys.exit(
            "HONG PRE-FLIGHT: ca 3 ma probe deu khong lay duoc "
            "bao cao KQKD tu Vietcap IQ. "
            "Dung som de tranh cao ca universe vo ich."
        )

    print(
        f"PRE-FLIGHT OK: "
        f"{probe_ok}/{len(probes)} ma co KQKD.",
        flush=True,
    )

    # --------------------------------------------------------
    # FULL FETCH
    # --------------------------------------------------------

    # Giu lai ket qua probe, tranh request lai.
    res = dict(probe_res)

    remaining = [
        s
        for s in u
        if s not in res
    ]

    print(
        f"\nBat dau cao "
        f"{len(remaining)} ma con lai "
        f"voi {WORKERS} workers...",
        flush=True,
    )

    with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as ex:

        for i, (s, d) in enumerate(
            ex.map(
                one,
                remaining,
            ),
            start=len(res),
        ):
            res[s] = d

            if i % 50 == 0:
                print(
                    i,
                    s,
                    len(d["ratio"]),
                    len(d["is"]),
                    len(d["cf"]),
                    flush=True,
                )

    # --------------------------------------------------------
    # DIAGNOSTICS FIRST
    # --------------------------------------------------------

    print_errors()

    # --------------------------------------------------------
    # INTEGRITY CHECK
    # --------------------------------------------------------

    no_is = [
        s
        for s, v in res.items()
        if not v["is"]
    ]

    no_ra = [
        s
        for s, v in res.items()
        if not v["ratio"]
    ]

    print(
        f"\nxong {len(res)} ma"
    )

    print(
        "  thieu bao cao KQKD : "
        f"{len(no_is)} ma "
        f"({len(no_is) / len(res):.1%})"
    )

    print(
        "  thieu chi so ty le : "
        f"{len(no_ra)} ma "
        f"({len(no_ra) / len(res):.1%})"
    )

    if no_is:
        print(
            "  ma thieu KQKD:",
            " ".join(
                sorted(no_is)[:40]
            ),
        )

    # --------------------------------------------------------
    # HARD FAIL
    #
    # >3% thieu KQKD -> KHONG dung data nay.
    #
    # QUAN TRONG:
    # Chua ghi de funda_raw2.json o thoi diem nay.
    # --------------------------------------------------------

    missing_ratio = (
        len(no_is)
        / len(res)
    )

    if missing_ratio > MAX_MISSING_IS:

        # Xoa file tmp cu neu co
        try:
            if os.path.exists(TEMP_FILE):
                os.remove(TEMP_FILE)

        except Exception:
            pass

        sys.exit(
            f"HONG: {len(no_is)} ma thieu bao cao KQKD "
            f"({missing_ratio:.1%}) - vuot nguong "
            f"{MAX_MISSING_IS:.0%}. "
            "KHONG GHI DE funda_raw2.json. "
            "Khong dung du lieu vua cao de backtest/cham diem."
        )

    # --------------------------------------------------------
    # ATOMIC WRITE
    #
    # Chi toi day moi cho phep thay file production.
    # --------------------------------------------------------

    with open(
        TEMP_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            res,
            f,
            ensure_ascii=False,
        )

    os.replace(
        TEMP_FILE,
        TARGET_FILE,
    )

    print(
        "\nOK: integrity check dat. "
        f"Da cap nhat an toan {TARGET_FILE}.",
        flush=True,
    )
