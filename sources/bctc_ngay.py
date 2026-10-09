# -*- coding: utf-8 -*-
"""NGAY CONG BO BAN DAU cua bao cao tai chinh quy — hai nguon doc lap voi Vietcap.

Vi sao can (09/10/2026): Vietcap ghi publicDate cua quy 2 va quy 4 la ngay ban
SOAT XET / KIEM TOAN (cuoi thang 8, cuoi thang 3), trong khi ban dau ra cuoi
thang 7 / cuoi thang 1. Hai nguon duoi day liet ke TUNG FILE kem thoi diem dang,
tach ban dau va ban soat xet:

  Vietstock  POST https://finance.vietstock.vn/data/getdocument
             code, type=1 (BCTC), page, pageSize, __RequestVerificationToken
             -> moi file: Title/FullName, LastUpdate (ngay gio dang)
  CafeF      GET  https://cafef.vn/du-lieu/Ajax/PageNew/FileBCTC.ashx?Symbol=&Type=1&Year=0
             -> moi file: Name, Quarter, Year, id (ObjectId: 4 byte dau = thoi diem tao)
             ObjectId truoc 10/03/2023 la ngay CafeF chuyen kho (02/03/2023), KHONG dung.

Thoi diem dang file khong the som hon ngay doanh nghiep cong bo — huong sai (neu
co) chi la MUON hon, khong bao gio nhin truoc. Chi lay file HOP NHAT khi ma do co
file hop nhat: bo may dung so hop nhat, ngay cua ban cong ty me (co khi ra truoc)
se cho bo may doc so hop nhat truoc khi no ton tai.
"""
import re, json, time, threading, datetime as dt
import requests

VN = dt.timezone(dt.timedelta(hours=7))
CAFEF = "https://cafef.vn/du-lieu/Ajax/PageNew/FileBCTC.ashx"
VS = "https://finance.vietstock.vn"
CAFEF_TU = dt.date(2023, 3, 10)        # ObjectId truoc moc nay = ngay chuyen kho
TU_NAM = 2018

_QUY = re.compile(r'qu[ýy]\s*([1-4])\s*(?:n[ăa]m\s*)?(\d{4})', re.I)
_BO = re.compile(r'so[áa]t\s*x[ée]t|ki[ểe]m\s*to[áa]n|6\s*th[áa]ng|9\s*th[áa]ng|b[áa]n\s*ni[êe]n|gi[ảa]i\s*tr[ìi]nh', re.I)
_HN = re.compile(r'h[ợo]p\s*nh[ấa]t', re.I)


def phan_loai(ten):
    """'Bao cao tai chinh Hop nhat quy 2 nam 2026' -> ((2026, 2), True). Ban soat
    xet / kiem toan / ban nien / giai trinh -> None (khong phai ban dau cua quy)."""
    if not ten or _BO.search(ten):
        return None
    m = _QUY.search(ten)
    if not m:
        return None
    return (int(m.group(2)), int(m.group(1))), bool(_HN.search(ten))


def gom(files):
    """files: [((y,q), hop_nhat, 'YYYY-MM-DDTHH:MM')] -> {'YYYYQq': thoi diem som nhat}.
    Quy nao co file hop nhat thi CHI tinh file hop nhat."""
    theo = {}
    for k, hn, t in files:
        theo.setdefault(k, []).append((hn, t))
    out = {}
    for (y, q), ds in theo.items():
        co_hn = [t for hn, t in ds if hn]
        out[f'{y}Q{q}'] = min(co_hn or [t for _, t in ds])
    return out


# ---------------- Vietstock ----------------
_vs_lock = threading.Lock()
_vs = {}

def _vs_phien():
    with _vs_lock:
        if 's' not in _vs:
            s = requests.Session()
            s.headers.update({"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest",
                              "Referer": VS + "/FPT/tai-tai-lieu.htm?doctype=1"})
            h = s.get(VS + "/FPT/tai-tai-lieu.htm?doctype=1", timeout=30).text
            m = (re.search(r'__RequestVerificationToken[^>]*value="?([^" >]+)', h)
                 or re.search(r'_tokenString\s*=\s*["\']([^"\']+)', h))
            if not m:
                raise RuntimeError('Vietstock: khong tim thay token')
            _vs['s'], _vs['tok'] = s, m.group(1)
        return _vs['s'], _vs['tok']


def _vs_ngay(v):
    """LastUpdate: '/Date(1785175440000)/' hoac '2026-07-27T22:34:00'."""
    if v is None:
        return None
    m = re.search(r'Date\((\d+)', str(v))
    if m:
        return dt.datetime.fromtimestamp(int(m.group(1)) / 1000, VN).strftime('%Y-%m-%dT%H:%M')
    return str(v)[:16]


def vietstock(sym, so_trang=30, kich=20):
    s, tok = _vs_phien()
    files = []
    for trang in range(1, so_trang + 1):
        r = s.post(VS + "/data/getdocument", timeout=30, data={
            "code": sym, "type": 1, "page": trang, "pageSize": kich,
            "__RequestVerificationToken": tok})
        r.raise_for_status()
        rows = r.json() or []
        for x in rows:
            p = phan_loai(x.get('FullName') or x.get('Title'))
            t = _vs_ngay(x.get('LastUpdate'))
            if p and t:
                files.append((p[0], p[1], t))
        cuoi = _vs_ngay(rows[-1].get('LastUpdate')) if rows else None
        if len(rows) < kich or (cuoi and int(cuoi[:4]) < TU_NAM):
            break
        time.sleep(0.3)
    return gom(files)


# ---------------- CafeF ----------------
def cafef(sym):
    r = requests.get(CAFEF, params={"Symbol": sym, "Type": 1, "Year": 0}, timeout=30,
                     headers={"User-Agent": "Mozilla/5.0", "Referer": "https://cafef.vn/"})
    r.raise_for_status()
    files = []
    for x in (r.json() or {}).get('Data') or []:
        p = phan_loai(x.get('Name'))
        oid = str(x.get('id') or '')
        if not p or not re.fullmatch(r'[0-9a-f]{24}', oid):
            continue
        t = dt.datetime.fromtimestamp(int(oid[:8], 16), VN)
        if t.date() < CAFEF_TU:
            continue
        files.append((p[0], p[1], t.strftime('%Y-%m-%dT%H:%M')))
    return gom(files)
