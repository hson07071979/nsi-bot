# -*- coding: utf-8 -*-
"""CHUOI CO BAN 12 QUY CHO TUNG MA — de trang ve bieu do tai chinh.

Xuat ra `data/funda_series.json`:

    { "FPT": {
        "q":   ["Q3/23", ... "Q2/26"],          12 quy gan nhat DA CONG BO
        "rev": [13762, ...],                    doanh thu, ty dong
        "np":  [1739, ...],                     loi nhuan sau thue, ty dong
        "ry":  [23.4, ...],                     %YoY doanh thu
        "ny":  [19.6, ...],                     %YoY loi nhuan
        "roe": [21.5, ...],                     %
        "pe":  [13.96, ...],
        "pb":  [3.00, ...],
        "tim": [0,0,1,...],                     1 = quy do lai den tu hoat dong bat thuong
        "vi":  ["...", null, ...]               ly do den tim, chi co khi tim=1
      }, ... }

VI SAO PHAI CO DEN TIM: mot doanh nghiep ban mieng dat hay thanh ly nha may thi
LNST quy do vot len. Bo cham diem nhin vao tuong la doanh nghiep dang khoe, mua
vao, roi quy sau khong con khoan do nua thi so lieu sup. Tach loi nhuan LOI (tu
ban hang) ra khoi loi nhuan KHAC (mot lan) la cach duy nhat thay duoc chuyen do.

KHONG NHIN TRUOC: chi lay quy co ngay cong bo <= phien du lieu gan nhat.
"""
import datetime as dt
import json
import sys

from prep import parse_funda

SO_QUY = 12


def ty(x):
    return None if x is None else round(x / 1e9, 1)


def pc(x):
    return None if x is None else round(x * 100, 1)


def build(asof=None):
    fu = parse_funda('data/funda_raw2.json')
    if asof is None:
        d = json.load(open('data/site_data2.json', encoding='utf-8'))
        asof = dt.date.fromisoformat(d['asof'])

    out = {}
    for s, rows in fu.items():
        # chi giu quy DA cong bo tinh den phien du lieu — khong nhin truoc
        rows = [r for r in rows if r.get('avail') and r['avail'] <= asof]
        if len(rows) < 5:
            continue
        idx = {(r['y'], r['q']): r for r in rows}
        lay = rows[-SO_QUY:]

        q, rev, np_, ry, ny, roe, pe, pb, tim, vi = ([] for _ in range(10))
        for r in lay:
            q.append(f"Q{r['q']}/{str(r['y'])[2:]}")
            rev.append(ty(r.get('rev')))
            np_.append(ty(r.get('npat')))
            py = idx.get((r['y'] - 1, r['q']))

            def yoy(k):
                a, b = r.get(k), (py.get(k) if py else None)
                return pc(a / b - 1) if (a is not None and b is not None and b > 0) else None
            ry.append(yoy('rev'))
            ny.append(yoy('npat'))
            roe.append(pc(r.get('roe')))
            pe.append(None if r.get('pe') is None else round(r['pe'], 2))
            pb.append(None if r.get('pb') is None else round(r['pb'], 2))

            # --- den tim ---
            oth, npat, pre = r.get('other'), r.get('npat'), r.get('pretax')
            ly = None
            if oth is not None and npat and npat > 0 and oth / npat > 0.30:
                ly = 'lợi nhuận khác chiếm %.0f%% LNST' % (oth / npat * 100)
            elif py is not None and pre is not None and oth is not None:
                # So CUNG MOT GOC: truoc thue (tong) voi loi (tong). Lay LNST cua
                # co dong cong ty me so voi loi tong la hai muc do khac nhau —
                # loi ich co dong thieu so doi la co ket luan sai.
                _p, _o = py.get('pretax'), py.get('other')
                if _p is not None and _o is not None and (_p - _o) > 0 and _p > 0:
                    lo, lo_py = pre - oth, _p - _o
                    pre_yoy = pre / _p - 1
                    if pre_yoy > 0 and lo / lo_py - 1 < 0:
                        ly = ('lợi nhuận trước thuế +%.0f%% nhưng lợi nhuận lõi %.0f%%'
                              % (pre_yoy * 100, (lo / lo_py - 1) * 100))
            tim.append(1 if ly else 0)
            vi.append(ly)

        out[s] = dict(q=q, rev=rev, np=np_, ry=ry, ny=ny, roe=roe, pe=pe, pb=pb,
                      tim=tim, vi=vi)
    return out


if __name__ == '__main__':
    r = build()
    json.dump(r, open('data/funda_series.json', 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    import os
    n_tim = sum(1 for v in r.values() if v['tim'] and v['tim'][-1])
    print(f"{len(r)} ma | {os.path.getsize('data/funda_series.json')/1e6:.2f} MB "
          f"| {n_tim} ma dang bat den tim o quy moi nhat")
    for s, v in sorted(r.items()):
        if v['tim'] and v['tim'][-1]:
            print(f"  {s:5s} {v['q'][-1]}: {v['vi'][-1]}")
