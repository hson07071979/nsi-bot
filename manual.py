# -*- coding: utf-8 -*-
"""QUYEN THU CONG CUA ANH SON — ba nguon, gop lai thanh HAI danh sach.

  GHIM = ghim.txt (repo nay)  +  manual.json -> watch   (So tay tren web)
  LOAI = loai.txt (repo nay)  +  manual.json -> loai    (So tay tren web)

LOAI THANG GHIM: ma vua ghim vua loai thi coi nhu bi loai.

ghim.txt / loai.txt : moi dong mot ma, dong bat dau bang '#' la ghi chu.
manual.json         : file anh Son bam "Dang len trang" tu So tay. Workflow da
                      tai san ve data/manual.json o buoc "Lay so lenh va so tay
                      tu trang web", nen o day chi doc file, KHONG goi mang.

QUAN TRONG — hai danh sach nay chi chi phoi cai NHIN VE TUONG LAI (watchlist,
bo loc, chuong bao). Chung KHONG duoc dung vao backtest. Lich su phai giu nguyen
si: neu bo mot ma ra khoi qua khu chi vi hom nay khong thich no thi con so hieu
suat tro thanh vo nghia.
"""
import json
import os
import re

GHIM_FILE = 'ghim.txt'
LOAI_FILE = 'loai.txt'

# So tay da dang. Tim theo thu tu nay: repo private (workflow tai ve data/)
# truoc, roi den repo public (manual.json nam ngay goc, canh live_scan.py).
SOTAY_FILES = ('data/manual.json', 'manual.json')

# Danh sach ghim ban dau cua anh Son — CHI dung khi ghim.txt CHUA TON TAI.
# File co mat ma rong => RONG THAT. Day la lo hong cu: xoa het ma trong ghim.txt
# xong trang van hien 11 ma nhu chua he sua, va khong the bo ghim bang cach nao.
GHIM_MAC_DINH = "MSN HAG ACB HDB STB BAF GMD IDC POW KBC SAB".split()

_CACHE = {}


def _ma_hop_le(x):
    x = str(x or '').strip().upper()
    return x if re.fullmatch(r'[A-Z0-9]{3,10}', x) else None


def _gop(*ds):
    """Gop nhieu danh sach ma, bo ma khong hop le, bo trung, giu thu tu."""
    seen, out = set(), []
    for d in ds:
        for x in (d or []):
            m = _ma_hop_le(x)
            if m and m not in seen:
                seen.add(m)
                out.append(m)
    return out


def doc_ds(path):
    """Doc mot file danh sach ma. Khong co file thi tra ve danh sach rong."""
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path, encoding='utf-8'):
        line = line.split('#')[0].strip()
        if not line:
            continue
        out.extend(re.split(r'[\s,;]+', line))
    return _gop(out)


def so_tay():
    """Noi dung manual.json anh Son da dang. Khong co file, hay file hong, thi
    tra ve rong — bo may van chay bang ghim.txt / loai.txt. TUYET DOI khong
    duoc do vi mot file thieu: buoc tai manual.json trong workflow la
    continue-on-error, no vang mat la chuyen binh thuong."""
    if 'sotay' in _CACHE:
        return _CACHE['sotay']
    o = {}
    for p in SOTAY_FILES:
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding='utf-8') as f:
                j = json.load(f)
            if isinstance(j, dict):
                o = j
                print(f'  so tay ({p}): {len(o.get("watch") or [])} ma ghim, '
                      f'{len(o.get("loai") or [])} ma loai'
                      f' — dang luc {o.get("updated") or "?"}')
                break
        except Exception as e:
            print(f'  CANH BAO: {p} khong doc duoc ({e}) — bo qua so tay')
    _CACHE['sotay'] = o
    return o


def _web(khoa):
    """Danh sach ma tu mot khoa cua manual.json. Chap ca hai dang:
    ["HPG", ...] hoac [{"sym": "HPG", "note": ..., "added": ...}, ...]."""
    return [(w.get('sym') if isinstance(w, dict) else w)
            for w in (so_tay().get(khoa) or [])]


def ghim():
    """Ma anh Son ghim thu cong — ghim.txt + So tay, tru ma da bi loai."""
    goc = doc_ds(GHIM_FILE) if os.path.exists(GHIM_FILE) else list(GHIM_MAC_DINH)
    bo = loai()
    return [x for x in _gop(goc, _web('watch')) if x not in bo]


def loai():
    """Ma anh Son loai thu cong — loai.txt + So tay. LOAI THANG GHIM."""
    return set(_gop(doc_ds(LOAI_FILE), _web('loai')))


if __name__ == '__main__':
    g, l = ghim(), loai()
    print(f'GHIM : {len(g)} ma  {" ".join(g) if g else "(trong)"}')
    print(f'LOAI : {len(l)} ma  {" ".join(sorted(l)) if l else "(trong)"}')
    print(f'nguon: ghim.txt {len(doc_ds(GHIM_FILE))} ma'
          f' · loai.txt {len(doc_ds(LOAI_FILE))} ma'
          f' · so tay {len(_web("watch"))} ghim / {len(_web("loai"))} loai')
