# -*- coding: utf-8 -*-
"""CHOT CHAN TRUOC KHI DANG — thà không cập nhật còn hơn đăng bản hỏng cho khách.

Chay sau build_site2.py. Neu bat ky kiem tra nao truot, script thoat voi ma loi
va GitHub Actions se dung, khong day len trang web.
"""
import json
import os
import re
import sys
import datetime as dt

FAIL = []
WARN = []


def check(ok, msg):
    if not ok:
        FAIL.append(msg)
    return ok


def warn(ok, msg):
    if not ok:
        WARN.append(msg)


# ---------- 1. file dung ra ----------
if not os.path.exists('site/index.html'):
    print('HONG: khong co site/index.html'); sys.exit(1)

html = open('site/index.html', encoding='utf-8').read()
size = len(html)
check(size > 1_500_000, f'trang web chi {size/1e6:.2f} MB, nghi thieu du lieu (cho >1,5 MB)')

# ---------- 2. du lieu nhung trong trang ----------
m = re.search(r'<script id="DATA"[^>]*>(.*?)</script>', html, re.S)
if not check(m is not None, 'khong tim thay khoi du lieu trong trang'):
    print('\n'.join(FAIL)); sys.exit(1)

try:
    D = json.loads(m.group(1).replace('<\\/', '</'))
except Exception as e:
    print(f'HONG: khoi du lieu khong doc duoc — {e}'); sys.exit(1)

# ---------- 3. cac khoi bat buoc ----------
for k in ('prod', 'bench', 'monthly', 'top6m', 'candles', 'lookup',
          'screener', 'watchlist', 'regime', 'signals', 'presets'):
    check(k in D and D[k], f'thieu khoi du lieu "{k}"')

# ---------- 3b. lop kiem dinh + lop real-time ----------
# Hai thu nay khong duoc phep bien mat lang le: mot ban dung thieu chung van
# chay binh thuong, nen neu khong kiem o day thi khong ai biet la da mat.
R = D.get('robust')
check(bool(R), 'thieu khoi "robust" — chua chay robustness.py')
if R:
    for k in ('walk_forward', 'slippage', 'perturb', 'remove_winners',
              'monte_carlo', 'lookahead', 'circuit_breaker', 't25', 'scorecard'):
        check(k in R and R[k], f'khoi kiem dinh thieu bai "{k}"')
    check(len(R.get('scorecard', {}).get('tang', [])) == 5, 'cham diem phai co du 5 tang')
    check(bool(R.get('frac_hieu_chuan')), 'thieu co vi the hieu chuan')
    # bay loi da tung mac: danh sach deal bi sap xep theo lai/lo lam sut gia
    nb = [x for x in R.get('remove_winners', []) if x.get('n_bo') == 0]
    if nb:
        lech = abs(nb[0]['m']['total_return'] - D['prod']['metrics']['total_return'])
        check(lech < 0.05, f'duong von dung lai tu deal lech {lech:.1%} so backtest that '
                           '— nhieu kha nang thu tu deal bi sap xep sai')

for ten, dau in (('lop real-time VPS', 'bgapidatafeed.vps.com.vn'),
                 ('trang Kiem dinh', 'function pageKiemDinh'),
                 ('bang dieu khien chuong', 'function bangDieuKhienChuong'),
                 ('nguon nen VPS', 'histdatafeed.vps.com.vn'),
                 ('nguon nen du phong VNDIRECT', 'dchart-api.vndirect.com.vn'),
                 ('thu vien bieu do nhung san', 'Lightweight Charts'),
                 ('bo dung bieu do', 'function moBieuDo')):
    check(dau in html, f'thieu {ten} trong trang')

# Bay lai dung loi da mac: viewBox 1000x260 + preserveAspectRatio="none" nhet vao
# o rong 370px lam MOI CHU trong bieu do bi bop ngang keo doc hon hai lan — nhin
# y het loi font. Khong duoc phep quay lai.
# tim trong MA THAT (the <svg ...>), khong tinh phan ghi chu giai thich loi cu
check('<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none"' not in html,
      'co bieu do dung preserveAspectRatio="none" — chu se bi bien dang')
# iframe TradingView tung lam o bieu do trang tron voi ma nho ("Ma giao dich nay
# chi co tren TradingView"). Da thay bang bieu do tu dung.
check('tradingview.com/widgetembed' not in html,
      'van con nhung iframe TradingView — ma nho se khong co bieu do')

if FAIL:
    print('KIEM TRA TRUOT:'); [print('  -', x) for x in FAIL]; sys.exit(1)

# ---------- 4. so lieu backtest co hop ly khong ----------
M = D['prod']['metrics']
check(M['trades'] > 80, f"chi co {M['trades']} lenh, nghi du lieu bi cut")
check(1.0 < M['total_return'] < 20.0, f"loi nhuan {M['total_return']*100:.0f}% nam ngoai khoang hop ly")
check(0.02 < M['maxdd'] < 0.30, f"sut giam toi da {M['maxdd']*100:.1f}% bat thuong")
check(M['pf'] and M['pf'] > 1.5, f"Profit Factor {M['pf']} qua thap, nghi cau hinh sai")

# ---------- 5. vu tru dung 110 chua ----------
TOP_N = 110
sc = D['screener']
check(sc.get('n') == TOP_N, f"bo loc co {sc.get('n')} ma, phai la {TOP_N} — nghi quen chay screener.py")

# ---------- 6. du lieu co moi khong ----------
asof = D.get('asof', '')
check(bool(re.match(r'\d{4}-\d{2}-\d{2}', asof)), f'ngay du lieu khong hop le: {asof}')
if re.match(r'\d{4}-\d{2}-\d{2}', asof):
    d0 = dt.date.fromisoformat(asof)
    days = (dt.date.today() - d0).days
    check(days <= 6, f'du lieu cu {days} ngay (phien {asof}) — nghi FireAnt khong tra ve phien moi')
    warn(days <= 3, f'du lieu {days} ngay tuoi — binh thuong neu vua nghi le')

check(sc.get('asof') == asof, f"bo loc phien {sc.get('asof')} khac trang chinh {asof} — quen chay screener.py")

# ---------- 7. tra cuu va nen ----------
check(len(D['lookup']) > 400, f"o tra cuu chi co {len(D['lookup'])} ma, cho >400")
check(len(D['candles']) > 15, f"chi co {len(D['candles'])} ma co nen")
noname = sum(1 for v in D['lookup'].values() if not v.get('name'))
warn(noname < len(D['lookup']) * 0.2,
     f'{noname} ma thieu ten cong ty — kiem data/by_exchange.csv')

# ---------- 8. watchlist va thanh tra cuu phai NHAT QUAN ----------
# Loi tung gap: watchlist noi long hon bot (nen 25% thay vi 18%) nen MWG vua nam
# trong watchlist vua bi o tra cuu bao "chua tao duoc nen gia chat". Mot ma hoac
# dang CHO DIEM MUA, hoac khong.
_wl = {m['sym'] for m in D['watchlist'].get('members', []) if m.get('status') == 'đạt'}
_cho = {k for k, v in D['lookup'].items() if v.get('state') == 'cho'}
# nhom "chua dat co ban" phai trung khop giua screener va lookup
_fa_scr = {r['sym'] for r in D['screener'].get('fa_watchlist', [])}
_fa_lk = {k for k, v in D['lookup'].items() if v.get('state') == 'fa'}
check(_fa_scr == _fa_lk,
      'nhom "chua dat co ban" lech nhau giua screener.py va lookup.py: '
      + ' '.join(sorted(_fa_scr ^ _fa_lk)))
check(not (_fa_scr & _cho), 'co ma vua o nhom FA vua o danh sach mua: '
      + ' '.join(sorted(_fa_scr & _cho)))
# quyen phu quyet thu cong: ma trong loai.txt tuyet doi khong duoc lot vao dau ca
_loai = {k for k, v in D['lookup'].items() if v.get('loai')}
check(not (_loai & _wl), 'ma anh Son da loai thu cong nhung van o watchlist: '
      + ' '.join(sorted(_loai & _wl)))
check(not (_loai & _cho), 'ma anh Son da loai thu cong nhung van o trang thai cho diem mua: '
      + ' '.join(sorted(_loai & _cho)))
check(not (_loai & _fa_lk), 'ma anh Son da loai thu cong nhung van o nhom FA: '
      + ' '.join(sorted(_loai & _fa_lk)))

_thua = _wl - _cho
_thieu = _cho - _wl
check(not _thua, 'watchlist co ma KHONG o trang thai cho diem mua: ' + ' '.join(sorted(_thua))
                 + ' — nguong trong screener.py lech voi lookup.py')
warn(not _thieu, 'ma dang cho diem mua nhung chua vao watchlist: ' + ' '.join(sorted(_thieu)))

# ---------- 8b. ba nguon du lieu song phai co mat trong trang ----------
# Khong bat buoc co noi dung (ngay dau chua co lenh nao), nhung KHOA phai ton tai
# — thieu khoa la trang doc `undefined` va bang danh muc trong tron.
for k in ('portfolio', 'manual', 'config'):
    check(k in D, f'thieu khoa "{k}" trong trang — build_site2.py chua nhung anh chup')

_pf = D.get('portfolio') or {}
_mn = D.get('manual') or {}

# So chay cua bo may (open_positions) va so ghi tien (portfolio.json) phai HOI TU.
# Neu lech, thuong la lop quet trong phien thieu mot dieu kien ma bo may co —
# dung la dieu kien 7 (co lenh mua/ban) va luat DK5. Canh bao chu khong chan,
# vi hai ben co the lech chinh dang mot phien khi bo may vua chot ma so chua kip.
# FireAnt tra thong ke lenh mua/ban TRE hon gia vai tieng. Cao qua som thi ca thi
# truong deu thieu, dieu kien 7 truot het, va bo may khong mo duoc lenh nao o phien
# moi nhat — trong y het "hom nay khong co tin hieu". Da tung xay ra ngay 21/08.
_oic = D.get('oi_cover')
if _oic is not None:
    check(_oic >= 0.50, f'phien cuoi chi {_oic*100:.0f}% ma co du lieu dong tien mua/ban '
                        '— cao qua som, chay lai fireant.py sau 18h gio Viet Nam')
    warn(_oic >= 0.85, f'{(1-_oic)*100:.0f}% ma thieu du lieu dong tien o phien cuoi')

_bm = {p['sym'] for p in (D.get('open_positions') or [])}
_st = {p['sym'] for p in (_pf.get('open') or [])}
warn(not (_st - _bm), 'so ghi tien co ma bo may KHONG cam: ' + ' '.join(sorted(_st - _bm))
     + ' — kiem lai dieu kien 7 va DK5 trong live_scan.py')
warn(not (_bm - _st), 'bo may cam ma so ghi tien chua co: ' + ' '.join(sorted(_bm - _st))
     + ' — binh thuong neu ma do mua truoc ngay bat dau ghi so')
if _pf.get('open') and _mn.get('trades'):
    _trung = {p['sym'] for p in _pf['open']} & {t['sym'] for t in _mn['trades'] if not t.get('sell_px')}
    warn(not _trung, 'ma vua o so tu dong vua o so tay, trang chi hien mot lan: '
         + ' '.join(sorted(_trung)))

# ---------- 9. bang thang ----------
check(len(D['monthly']) > 60, f"bang thang chi co {len(D['monthly'])} thang")

# ---------- ket qua ----------
print('=' * 60)
if WARN:
    print('CANH BAO (van dang duoc):')
    for x in WARN:
        print('  !', x)
if FAIL:
    print('KIEM TRA TRUOT — KHONG DANG LEN TRANG WEB:')
    for x in FAIL:
        print('  X', x)
    print('=' * 60)
    sys.exit(1)

print('KIEM TRA DAT — san sang dang')
print(f"  phien {asof} | {size/1e6:.2f} MB")
print(f"  loi nhuan +{M['total_return']*100:.1f}% | DD {M['maxdd']*100:.1f}% | PF {M['pf']} | {M['trades']} lenh")
print(f"  bo loc {sc['n']} ma | tra cuu {len(D['lookup'])} ma | nen {len(D['candles'])} ma")
_cfg = D.get('config') or {}
print(f"  du lieu song: {len(_pf.get('open') or [])} ma dang cam (so tu dong)"
      f" | so tay {len(_mn.get('trades') or [])} lenh, {len(_mn.get('watch') or [])} ma theo doi"
      f" | real-time {'BAT' if _cfg.get('proxy') else 'tat'}")
print(f"  thu cong: ghim {len(D['screener'].get('seed') or [])} ma | loai {len(_loai)} ma"
      + (' -> ' + ' '.join(sorted(_loai)) if _loai else ''))
print('=' * 60)
