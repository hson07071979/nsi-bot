# -*- coding: utf-8 -*-
"""XUAT BO FILE CHO REPO PUBLIC.

Chay sau build_site2.py + verify_build.py. Tao thu muc `out/` gom:

  index.html        trang web day du
  thresholds.json   nguong gia + khoi luong cua tung ma cho PHIEN KE TIEP
  .nojekyll

`thresholds.json` la thu bo quet trong phien (chay o repo public) can. No CHI chua
CON SO NGUONG, khong chua luat nao ca — nen dat o repo public cung khong lo he thong.
Ban than cac nguong nay da hien cong khai tren thanh tra cuu cua trang web roi.
"""
import json
import os
import shutil
import sys

OUT = 'out'


def main():
    if not os.path.exists('site/index.html'):
        sys.exit('HONG: chua co site/index.html, chay build_site2.py truoc')
    D = json.load(open('data/site_data2.json', encoding='utf-8'))

    os.makedirs(OUT, exist_ok=True)
    shutil.copy('site/index.html', f'{OUT}/index.html')
    open(f'{OUT}/.nojekyll', 'w').close()

    L = D['lookup']
    # chi lay cac ma trong vu tru giao dich — do la nhung ma bot co the mua
    uni = {k: v for k, v in L.items() if v.get('inuni')}

    syms = {}
    for k, v in uni.items():
        syms[k] = dict(
            name=v['name'], exch=v['exch'],
            ref=v['price'],            # gia dong cua phien truoc = gia tham chieu phien toi
            need_px=v['need_px'],      # gia dong cua toi thieu de bat tran
            need_vol=v['need_vol'],    # khoi luong toi thieu (2 x binh quan 20 phien)
            vma20=v['vma20'],
            thr=v['thr'],              # bien do bat tran (%)
            score=v['score'], base=v['base'], fund=v.get('fund'),
            sector=v.get('sector'),
            state=v['state'], label=v['label'],
            loai=bool(v.get('loai')),
            miss=v['miss'], block=v['block'],
        )

    # Den thi truong cua phien vua chot — so lenh tu dong dung no de tinh co vi the
    # va de biet co phai ha 1/3 khi den chuyen Cam hay khong.
    _rg = (D.get('regime') or [{}])[-1]

    th = dict(
        asof=D['asof'],
        fa_score_lo=40, score_floor=45,
        gtgd_min=15e9,
        vol_floor=2.0,
        # Dieu kien 7 — co lenh mua / co lenh ban. Bo quet trong phien tinh duoc
        # tu chinh dong du lieu ngay cua FireAnt, nen phai biet nguong la bao nhieu.
        ordimb_min=1.20,
        light=_rg.get('light', 'XANH'),
        n=len(syms),
        syms=syms,
    )
    json.dump(th, open(f'{OUT}/thresholds.json', 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))

    # Hai file thu cong di theo sang repo public de bo quet trong phien cung biet:
    # ma bi loai thi khong duoc keu chuong, khong duoc vao so lenh.
    for f in ('loai.txt', 'ghim.txt'):
        if os.path.exists(f):
            shutil.copy(f, f'{OUT}/{f}')

    cho = sum(1 for v in syms.values() if v['state'] == 'cho')
    fa  = sum(1 for v in syms.values() if v['state'] == 'fa')
    lo  = sum(1 for v in syms.values() if v['state'] == 'loai')
    sz = os.path.getsize(f'{OUT}/thresholds.json')
    print(f'out/index.html      {os.path.getsize(f"{OUT}/index.html")/1e6:.2f} MB')
    print(f'out/thresholds.json {sz/1024:.0f} KB · {len(syms)} mã · {cho} mã chờ điểm mua · {fa} mã chưa đạt cơ bản'
          + (f' · {lo} mã anh loại thủ công' if lo else ''))


if __name__ == '__main__':
    main()
