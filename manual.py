# -*- coding: utf-8 -*-
"""QUYEN THU CONG CUA ANH SON — hai file van ban, sua truc tiep tren GitHub.

  ghim.txt   ma GHIM  — luon co mat trong watchlist du diem so co tut, de theo doi
  loai.txt   ma LOAI  — KHONG BAO GIO vao watchlist, KHONG BAO GIO keu chuong

Moi dong mot ma. Dong bat dau bang '#' la ghi chu. Chu thuong hay chu hoa deu duoc.
Vi du:

    # khong thich hang nay
    HAG      # ban lai hoai
    ROS

QUAN TRONG — hai file nay chi chi phoi cai NHIN VE TUONG LAI (watchlist, bo loc,
chuong bao). Chung KHONG duoc dung vao backtest. Lich su phai giu nguyen si:
neu bo mot ma ra khoi qua khu chi vi hom nay khong thich no thi con so hieu suat
tro thanh vo nghia.
"""
import os
import re

GHIM_FILE = 'ghim.txt'
LOAI_FILE = 'loai.txt'

# Danh sach ghim ban dau cua anh Son — dung khi chua co ghim.txt.
GHIM_MAC_DINH = "MSN HAG ACB HDB STB BAF GMD IDC POW KBC SAB".split()


def doc_ds(path):
    """Doc mot file danh sach ma. Khong co file thi tra ve danh sach rong."""
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path, encoding='utf-8'):
        line = line.split('#')[0].strip().upper()
        if not line:
            continue
        for tok in re.split(r'[\s,;]+', line):
            if re.fullmatch(r'[A-Z0-9]{3,10}', tok):
                out.append(tok)
    # bo trung, giu thu tu
    seen = set()
    return [x for x in out if not (x in seen or seen.add(x))]


def ghim():
    """Cac ma anh Son ghim thu cong."""
    ds = doc_ds(GHIM_FILE)
    return ds if ds else list(GHIM_MAC_DINH)


def loai():
    """Cac ma anh Son loai thu cong — set de tra cuu nhanh."""
    return set(doc_ds(LOAI_FILE))


if __name__ == '__main__':
    g, l = ghim(), loai()
    print(f'ghim.txt : {len(g)} ma  {" ".join(g) if g else "(trong)"}')
    print(f'loai.txt : {len(l)} ma  {" ".join(sorted(l)) if l else "(trong)"}')
    x = set(g) & l
    if x:
        print('CANH BAO: ma vua ghim vua loai — LOAI thang the: ' + ' '.join(sorted(x)))
