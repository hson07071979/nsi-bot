# -*- coding: utf-8 -*-
"""R33 — Luat thoat qua TUNG KICH BAN THI TRUONG (anh Son 30/09/2026: "test tren tat ca cac
scenario cua thi truong chu").

Hai cua thoat KHAC HAN nhau, do rieng va do chung:
  * Khoa lai (S1 + nac 15%): theo LAI CUA TUNG MA — da tung len >= 8/12/15% thi giu san +2/+5/+8%.
  * Den Cam ha 1/3: theo THI TRUONG CHUNG — den chuyen Cam (lenh mua luc Xanh/Vang) thi ban 1/3.
Cau hinh (moi cai mot E.run day du, cung du lieu):
  PROD      = S1 + 15%->+8%, den Cam BAT        (dang chay tu 30/09)
  KHONG_CAM = S1 + 15%->+8%, den Cam TAT        (chi khoa lai)
  CHI_CAM   = KHONG khoa lai, den Cam BAT       (chi den Cam)
  TRAN      = khong khoa lai, khong den Cam     (chi cac cua con lai: cat lo, momentum, van, MA)
  S1        = S1 (khong nac 15%), den Cam BAT
Kich ban:
  (a) tung nam 2019..2026;
  (b) che do VN-Index theo loi suat 60 phien: TANG MANH (> +10%), DI NGANG, GIAM MANH (< -10%);
  (c) den thi truong cua bo may: XANH / VANG / CAM / DO;
  (d) 10 dot VN-Index sut manh nhat (tu dinh 60 phien, >= 10%) — bo may mat bao nhieu trong dung dot do.
Moi o: loi nhuan kep cua duong von trong cac phien thuoc kich ban, sut giam lon nhat trong kich ban.
Ket qua: evidence/r33_scenarios.json + bang in ra log. KHONG doi PROD."""
import os, sys, json
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
import engine2 as E
from produce2 import PROD

OUT = os.environ.get('OUT', 'evidence/r33_scenarios.json')
S1_15 = [[0.08, 0.02], [0.12, 0.05], [0.15, 0.08]]
CFGS = [('PROD', dict(profit_lock=S1_15, use_orange_cut=True)),
        ('KHONG_CAM', dict(profit_lock=S1_15, use_orange_cut=False)),
        ('CHI_CAM', dict(profit_lock=None, use_orange_cut=True)),
        ('TRAN', dict(profit_lock=None, use_orange_cut=False)),
        ('S1', dict(profit_lock=[[0.08, 0.02], [0.12, 0.05]], use_orange_cut=True))]


def seg(ret, mask):
    """Loi nhuan kep + sut giam lon nhat cua chuoi loi suat ngay trong cac phien mask=True."""
    r = ret[mask]
    if len(r) == 0:
        return dict(n=0, ret=None, dd=None)
    nav = np.cumprod(1 + r); dd = 1 - nav / np.maximum.accumulate(np.r_[1.0, nav])[1:]
    return dict(n=int(len(r)), ret=round(float(nav[-1] - 1), 4), dd=round(float(max(dd.max(), 0)), 4))


def main():
    runs = {}
    for name, over in CFGS:
        C = dict(E.CFG); C.update(PROD); C.update(over)
        r = E.run(C, log=False); runs[name] = r
        print(name, E.metrics(r), flush=True)
    r0 = runs['PROD']; cal = [str(x) for x in r0['cal']]; n = len(r0['eq']); i0 = len(cal) - n
    dates = [e[0] for e in r0['eq']]
    vni = np.asarray(r0['R']['vni'][i0:i0 + n], float)
    light = list(r0['R']['light'][i0:i0 + n])
    v60 = np.full(n, np.nan); v60[60:] = vni[60:] / vni[:-60] - 1
    # ---- kich ban ----
    sc = {}
    for y in sorted({d[:4] for d in dates}):
        sc[f'Năm {y}'] = np.array([d[:4] == y for d in dates])
    sc['VNI tăng mạnh (60 phiên > +10%)'] = v60 > 0.10
    sc['VNI đi ngang (±10%)'] = (v60 >= -0.10) & (v60 <= 0.10)
    sc['VNI giảm mạnh (60 phiên < −10%)'] = v60 < -0.10
    for L_, vi in (('XANH', 'Xanh'), ('VANG', 'Vàng'), ('CAM', 'Cam'), ('DO', 'Đỏ')):
        sc[f'Đèn {vi}'] = np.array([x == L_ for x in light])
    # (d) cac dot sut: tu dinh 60 phien, giam >= 10%, khong chong nhau — lay 10 dot sau nhat
    dots = []; used = np.zeros(n, bool)
    pk = np.array([vni[max(0, k - 60):k + 1].max() for k in range(n)])
    ddv = 1 - vni / pk
    order = np.argsort(-ddv)
    for k in order:
        if ddv[k] < 0.10 or len(dots) >= 10: break
        a = max(0, k - 60) + int(np.argmax(vni[max(0, k - 60):k + 1]))
        if used[a:k + 1].any(): continue
        used[a:k + 1] = True; dots.append((a, k, float(ddv[k])))
    for a, k, d in sorted(dots):
        m = np.zeros(n, bool); m[a + 1:k + 1] = True
        sc[f'Đợt sụt VNI {dates[a]}→{dates[k]} (−{d*100:.0f}%)'] = m
    # ---- do ----
    out = dict(meta=dict(research='R33 kịch bản thị trường', asof=dates[-1], prod_config_hash=None),
               configs={k: v for k, v in CFGS}, metrics={k: E.metrics(v) for k, v in runs.items()}, rows=[])
    rets = {}
    for name, r in runs.items():
        nav = np.array([e[1] for e in r['eq']], float)
        rets[name] = np.r_[0.0, nav[1:] / nav[:-1] - 1]
    vret = np.r_[0.0, vni[1:] / vni[:-1] - 1]
    print('\n==== KICH BAN (loi nhuan % / sut giam lon nhat %) ====')
    print(f"{'Kịch bản':48s} {'phiên':>5s} " + ' '.join(f'{k:>16s}' for k, _ in CFGS) + f" {'VN-Index':>10s}")
    for label, m in sc.items():
        row = dict(scenario=label, sessions=int(m.sum()), vni=seg(vret, m))
        for k, _ in CFGS:
            row[k] = seg(rets[k], m)
        out['rows'].append(row)
        cell = lambda s: '—' if s['ret'] is None else f"{s['ret']*100:+7.1f}/{s['dd']*100:4.1f}"
        print(f"{label:48s} {row['sessions']:5d} " + ' '.join(f'{cell(row[k]):>16s}' for k, _ in CFGS)
              + f" {cell(row['vni']):>10s}", flush=True)
    # dem kich ban moi cua thoat giup / hai
    tong = {}
    for a, b, ten in (('PROD', 'KHONG_CAM', 'đèn Cam (có khoá lãi)'), ('KHONG_CAM', 'TRAN', 'khoá lãi (không đèn Cam)'),
                      ('CHI_CAM', 'TRAN', 'đèn Cam (không khoá lãi)'), ('PROD', 'S1', 'nấc 15%')):
        g = h = 0
        for row in out['rows']:
            if row[a]['ret'] is None: continue
            if row[a]['ret'] > row[b]['ret'] + 1e-4: g += 1
            elif row[a]['ret'] < row[b]['ret'] - 1e-4: h += 1
        tong[ten] = dict(giup=g, hai=h, bang=len(out['rows']) - g - h)
        print(f"{ten:30s}: tốt hơn ở {g} kịch bản, kém hơn ở {h}, bằng nhau {len(out['rows']) - g - h}")
    out['tong'] = tong
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1, default=str)


if __name__ == '__main__':
    main()
