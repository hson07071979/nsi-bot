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
            # Neu lenh nay duoc vao thi vao bao nhieu % NAV, va cai gi quyet dinh
            # con so do. CHI hai truong ngan — phan giai thich day du nam trong
            # index.html (tai mot lan), khong nhoi vao day vi lop truc tiep tai
            # lai file nay moi 45 giay.
            size_pct=v.get('size_pct'), size_tran=v.get('size_tran'),
            # Ma dang cam: lop quet trong phien KHONG duoc keu MUA lan nua, va
            # trang web phai hien "DANG CAM" thay vi "CHO DIEM MUA".
            dang_cam=bool(v.get('dang_cam')),
            miss=v['miss'], block=v['block'],
        )

    # Den thi truong cua phien vua chot — so lenh tu dong dung no de tinh co vi the
    # va de biet co phai ha 1/3 khi den chuyen Cam hay khong.
    _rg = (D.get('regime') or [{}])[-1]

    # ---- PROD thresholds come from produce2.PROD (cfg_prod), never typed here ----
    CF = D.get('cfg_prod') or {}
    for k in ('ordimb_min', 'gtgd_min', 'vol_floor', 'score_floor', 'top_n', 'base_range'):
        if CF.get(k) is None:
            sys.exit(f'HONG: cfg_prod thieu {k} — produce2.py chua ghi cau hinh dang chay')
    spec = D.get('spec') or {}
    if not spec:
        sys.exit('HONG: thieu khoi spec (spec_export) — lop quet trong phien khong the tai hien bo may')
    # every symbol the live scanner evaluates must also carry the display fields
    for k, sp in spec.items():
        if k not in syms and k in L:
            v = L[k]
            syms[k] = dict(name=v['name'], exch=v['exch'], ref=v['price'], need_px=v['need_px'],
                           need_vol=v['need_vol'], vma20=v['vma20'], thr=v['thr'], score=v['score'],
                           base=v['base'], fund=v.get('fund'), sector=v.get('sector'), state=v['state'],
                           label=v['label'], loai=bool(v.get('loai')), size_pct=v.get('size_pct'),
                           size_tran=v.get('size_tran'), dang_cam=bool(v.get('dang_cam')),
                           miss=v['miss'], block=v['block'])
    for k in syms:
        if k in spec:
            syms[k]['spec'] = spec[k]
            # exact next-session volume need (engine: today is INSIDE its 20-day mean)
            sp = spec[k]; f = float(CF['vol_floor'])
            if sp.get('vol_s19') is not None and sp.get('vol_c19'):
                n = sp['vol_c19'] + 1
                syms[k]['need_vol'] = int(f * sp['vol_s19'] / (n - f)) if n > f else None

    th = dict(
        asof=D['asof'],
        spec_version=2,
        prod_config_hash=D.get('prod_config_hash'),
        cfg=CF,
        book=D.get('book'),
        signals_today=D.get('signals_today') or [],
        signals_recent=D.get('signals_recent') or [],
        light_by_date=D.get('light_by_date') or {},
        spec_u=D.get('spec_u'),
        # Do phu du lieu dong tien mua/ban cua phien cuoi. Buoc chan trung phien
        # trong daily.yml doc con so nay de biet ban DA DANG co "day du" chua:
        # cao som thi FireAnt chua do BuyCount/SellCount, trang van dang duoc
        # nhung mong, va nhip sau nen chay lai chu khong duoc bo qua.
        oi_cover=D.get('oi_cover'),
        fa_score_lo=40, score_floor=CF['score_floor'],
        gtgd_min=CF['gtgd_min'],
        vol_floor=CF['vol_floor'],
        # Dieu kien 9 — co lenh mua / co lenh ban. Doc tu PROD, khong go tay.
        ordimb_min=CF['ordimb_min'],
        use_ordimb=bool(CF.get('use_ordimb', True)),
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
    # Shared definitions travel to the runtime repo byte-for-byte: the live scanner
    # and the paper book import THESE files, so they cannot drift from the engine.
    for f in ('signal_spec.py', 'allocator.py'):
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
