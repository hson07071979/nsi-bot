# -*- coding: utf-8 -*-
"""WALK-FORWARD CHO ĐÚNG MỘT CẶP THAM SỐ ĐÃ ĐÓNG BĂNG.

   Khac han walk-forward trong robustness.py. O do, moi cua so duoc phep TU CHON
   tham so tot nhat tren du lieu train — nen ket qua tra loi cau hoi "quy trinh
   chon tham so co song sang tuong lai khong".

   O day thi nguoc lai: DONG BANG mot cap (nen X, van T+N) tu truoc, khong cho
   chon gi ca, roi dem cham diem tren tung nam. Cau hoi la: "cap nay co that su
   tot hon cap dang chay tren du lieu chua dung de thiet ke khong".

   Vi sao phai lam rieng: nen 16% va T+4 duoc chon vi chung tot tren TOAN KY.
   Toan ky la du lieu da nhin thay het. Neu khong kiem ngoai mau thi doi production
   theo mot con so toan ky la dung dinh nghia cua overfit.

   Chay: python3 wf_cap.py   ->  data/wf_cap.json
"""
import json
import numpy as np
import engine2 as E
from produce2 import PROD

CAP = [
    ('Dang chay   nen 18% · T+6', dict(base_range=0.18, t_valve=6)),
    ('Ung vien    nen 16% · T+4', dict(base_range=0.16, t_valve=4)),
    ('Ung vien    nen 16% · T+6', dict(base_range=0.16, t_valve=6)),
    ('Ung vien    nen 18% · T+4', dict(base_range=0.18, t_valve=4)),
    ('Doi chieu   nen 14% · T+6', dict(base_range=0.14, t_valve=6)),
]
NAM = ['2019', '2020', '2021', '2022', '2023', '2024', '2025', '2026']
# Nam KHONG duoc dung de chon tham so. Cap 16%/T+4 duoc chon bang toan ky 2019-2026,
# nen thuc ra khong con nam nao that su "ngoai mau". Bon nam gan nhat la thu gan
# nhat voi ngoai mau ma minh co — va phai ghi ro han che nay.
NGOAI_MAU = ['2023', '2024', '2025', '2026']


def m(cfg, **ov):
    c = dict(PROD); c.update(cfg); c.update(ov)
    return E.metrics(E.run(c, log=False))


OUT = {'canh_bao': (
    'Cap 16%/T+4 duoc chon bang du lieu TOAN KY 2019-2026, nen khong nam nao thuc '
    'su la ngoai mau. Bang duoi chi cho biet cap do co on dinh QUA CAC NAM hay chi '
    'thang nho mot vai nam. Do KHONG phai bang chung ngoai mau that.'), 'cap': []}

print('=' * 92)
print('WALK-FORWARD CAP DA DONG BANG — khong cho chon tham so o bat ky cua so nao')
print('=' * 92)
print(f"{'Cau hinh':30s} " + ' '.join(f'{y:>7s}' for y in NAM) + '   gop 4nam  lai/8  lenh')
print('-' * 92)

for ten, cfg in CAP:
    hang = {'ten': ten, 'cfg': cfg, 'nam': []}
    for y in NAM:
        x = m(cfg, start=y + '-01-01', end=y + '-12-31')
        hang['nam'].append(dict(nam=y, ret=x['total_return'], pf=x['pf'],
                                dd=x['maxdd'], n=x['trades']))
    gop4 = float(np.prod([1 + z['ret'] for z in hang['nam'] if z['nam'] in NGOAI_MAU]) - 1)
    lai = sum(1 for z in hang['nam'] if z['ret'] > 0)
    nl = sum(z['n'] for z in hang['nam'])
    toan = m(cfg)
    hang.update(gop_4nam=round(gop4, 4), n_nam_lai=lai, n_lenh=nl,
                toan_ky={k: toan[k] for k in ('total_return', 'maxdd', 'pf', 'sharpe', 'trades')})
    OUT['cap'].append(hang)
    print(f"{ten:30s} " + ' '.join(f"{z['ret']:+6.1%}" for z in hang['nam'])
          + f"  {gop4:+7.1%}   {lai}/8  {nl:4d}")

print('-' * 92)
print(f"{'':30s} " + ' '.join(f'{y:>7s}' for y in NAM))
print()
print('TOAN KY (de doi chieu — day la con so DA NHIN THAY HET du lieu):')
for h in OUT['cap']:
    t = h['toan_ky']
    print(f"  {h['ten']:30s} {t['total_return']:+8.1%}  DD {t['maxdd']:6.2%}  "
          f"PF {t['pf']:5.2f}  Sharpe {t['sharpe']:.2f}  {t['trades']:3d} lenh")

# So sanh truc tiep: cap ung vien co thang cap dang chay o TUNG NAM khong?
goc = OUT['cap'][0]
print('\nSO TUNG NAM voi cau hinh dang chay (18%/T+6):')
for h in OUT['cap'][1:]:
    thang = sum(1 for a, b in zip(h['nam'], goc['nam']) if a['ret'] > b['ret'])
    chenh = [f"{a['nam']}:{(a['ret']-b['ret'])*100:+5.1f}d" for a, b in zip(h['nam'], goc['nam'])]
    print(f"  {h['ten']:30s} thang {thang}/8 nam · " + ' '.join(chenh))
    h['thang_tren_goc'] = thang

json.dump(OUT, open('data/wf_cap.json', 'w'), ensure_ascii=False)
print('\nGHI data/wf_cap.json')
