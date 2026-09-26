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

# CHOT CHAN GOC: json.loads cua Python CHAP NHAN NaN/Infinity, con JSON.parse
# cua trinh duyet thi NEM LOI -> ca trang trang. Nen phai tu chan tay, khong
# duoc tin json.loads chay duoc la trinh duyet doc duoc. Loi ngay 17/09/2026.
_xau = re.search(r'\b(NaN|Infinity)\b', m.group(1))
if _xau: print('HONG: khoi du lieu co ' + _xau.group(0) + ' -> JSON.parse cua trinh duyet nem loi, ca trang se TRANG'); sys.exit(1)

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

# ---------- 5. bo loc co dung cung mot bo nguong voi bo may khong ----------
# LOI 21/09/2026: dong nay tung ghi cung `TOP_N = 110`. Doi bot sang TOP 120 la
# chot chan nay truot, build do, KHONG DANG DUOC gi len trang — mat ca mot lan
# dung 10 phut. Nay doc thang tu cau hinh bo may nhung trong trang, nen doi
# nguong o produce2.py la kiem tra tu theo, khong bao gio lech nua.
CFP = D.get('cfg_prod') or {}
TOP_N = CFP.get('top_n')
sc = D['screener']
check(TOP_N is not None,
      'thieu khoi "cfg_prod" trong trang — produce2.py chua ghi cau hinh dang chay')
if TOP_N is not None:
    check(sc.get('n') == TOP_N,
          f"bo loc co {sc.get('n')} ma, phai la {TOP_N} — nghi quen chay screener.py, "
          "hoac screener.py va produce2.py dang de hai gia tri top_n khac nhau")

# Cung mot bay, hai nguong con lai. Lop watchlist va lop bo may PHAI dung chung
# mot bo nguong; lech la co ma vua nam trong watchlist vua bi bao "chua du dieu
# kien" — so kien truc da ghi ba lan.
_wr = (D.get('watchlist') or {}).get('rules') or {}
if _wr.get('max_base_range') is not None and CFP.get('base_range') is not None:
    check(abs(_wr['max_base_range'] - CFP['base_range']) < 1e-9,
          f"nen gia lech: watchlist {_wr['max_base_range']:.2f} khac bo may "
          f"{CFP['base_range']:.2f} — sua ca screener.py lan produce2.py")

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
    warn(_oic >= 0.50, f'phien cuoi chi {_oic*100:.0f}% ma (ca ma khong thanh khoan) co du lieu dong tien')
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

# ---------- 8c. AUDIT 23/09/2026: parity + data health are BUILD-BREAKING ----------
# (a) the running config must be stamped and identical everywhere
_h = D.get('prod_config_hash')
check(bool(_h) and (D.get('cfg_prod') or {}).get('prod_config_hash') == _h,
      'thieu / lech prod_config_hash giua site_data va cfg_prod')
check(bool(D.get('spec')) and bool(D.get('spec_u')),
      'thieu signal spec cho phien ke tiep — lop quet trong phien se khong the bao MUA')
# (b) live scanner definition == engine definition, replayed on recent history
try:
    sys.path.insert(0, 'tests')
    import importlib
    tp = importlib.import_module('test_parity')
    _d0 = dt.date.fromisoformat(asof) - dt.timedelta(days=400)
    _pr = tp.main(_d0.isoformat(), None, verbose=False)
    print(f"PARITY live<->engine 400 ngay: {_pr['both']} khop, {_pr['engine_only']} chi engine, "
          f"{_pr['live_only']} chi live, {_pr['cond_disagree']} lech dieu kien, "
          f"{_pr['undetermined']} chua quyet (thong tin: {_pr['agreement']:.1%})")
    # CHOT CUNG (26/09/2026): tin hieu MUA phai khop TUYET DOI. Mot "chi live" la mot
    # lenh backtest chua tung cho phep; mot "chi engine" la mot lenh live bo lo. Ty le
    # % chi de doc — khong quyet dinh DAT/TRUOT. In ro tung ca lech (ngay, ma, dieu kien).
    for _tb in _pr.get('tables') or []:
        print(_tb)
    for _e in (_pr.get('cond_examples') or [])[:20]:
        print('  lech dieu kien:', _e)
    check(_pr['engine_only'] == 0 and _pr['live_only'] == 0,
          f"parity live<->engine: {_pr['engine_only']} chi engine, {_pr['live_only']} chi live "
          f"{_pr['examples'][:10]} — signal_spec.py lech engine2.screen()")
    check(_pr['cond_disagree'] == 0 and _pr['undetermined'] == 0,
          f"parity dieu kien: {_pr['cond_disagree']} lech {_pr['cond_disagree_by']}, "
          f"{_pr['undetermined']} chua quyet — {(_pr.get('cond_examples') or [])[:10]}")
except SystemExit:
    raise
except Exception as e:
    check(False, f'khong chay duoc tests/test_parity.py: {type(e).__name__}: {e}')
# (c) data sources
try:
    _dh = json.load(open('data/data_health.json', encoding='utf-8'))
except Exception:
    _dh = {}
for _src in ('fireant_price', 'vietcap'):
    _b = _dh.get(_src)
    if _b is None:
        warn(False, f'data_health thieu nguon {_src} (ban dung cu chua ghi)')
    else:
        check(_b.get('status') == 'OK', f"nguon {_src} trang thai {_b.get('status')} — khong dang ban thieu du lieu")
# (d) order flow on the LAST session, measured per exchange on liquid names:
#     HNX publishes BuyCount/SellCount later than HOSE; a build that runs too early
#     silently kills every HNX signal of the day.
try:
    import numpy as _np
    import engine2 as _E
    _d, _I, _, _ = _E.load()
    _TV = _d['TotalValue'][-1]; _BC = _d['BuyCount'][-1]; _SC = _d['SellCount'][-1]
    import csv as _csv
    try:   # san HIEN TAI (fa.npz `exch` la san lich su suy ra: ACV UPCoM bi gan HOSE)
        _cur = {r_['symbol']: {'HSX': 'HOSE'}.get(r_['exchange'], r_['exchange'])
                for r_ in _csv.DictReader(open('data/by_exchange.csv', encoding='utf-8'))}
    except Exception:
        _cur = {}
    _exn = _np.array([_cur.get(str(s_), str(e_)) for s_, e_ in zip(_d['sym'], _d['exch'])])
    for _ex in ('HOSE', 'HNX'):
        _m = (_exn == _ex) & (_TV >= 5e9)
        _c = float(((_BC > 0) & (_SC > 0) & _m).sum()) / max(1, int(_m.sum()))
        print(f'dong tien phien cuoi {_ex}: {_c:.0%} ma thanh khoan co BuyCount')
        check(_c >= 0.80, f'dong tien phien cuoi {_ex} chi {_c:.0%} ma thanh khoan co du lieu — '
                          'cao qua som, chay lai sau khi FireAnt cap nhat')
except Exception as e:
    # Khong do duoc = khong chung minh duoc du dong tien => chan, khong cho qua im lang.
    check(False, f'khong do duoc do phu dong tien theo san: {type(e).__name__}: {e}')
# (e) paper book: nothing booked without Condition 9, and the ledger reconciles
for _p in (_pf.get('open') or []):
    if _p.get('position_source') in ('live_scan_MUA', 'engine_signal'):
        if CFP.get('stage1') is not None and _p.get('probe_fail'):
            # lenh do truot DK9: chi duoc nam trong so toi da toi phien ban duoc dau tien
            _sf = int(CFP.get('sell_from', 2) or 2)
            check((_p.get('held') or 0) <= _sf,
                  f"lenh do {_p['sym']} {_p['entry']} truot DK9 nhung chua ban sau T+{_sf}")
            continue
        check(_p.get('ordimb') is not None and _p['ordimb'] >= CFP.get('ordimb_min', 1.4),
              f"so paper vao {_p['sym']} {_p['entry']} ma khong chung minh Dieu kien 9")
_ck = _pf.get('checks')
if _ck:
    check(_ck.get('ok'), f'so paper doi soat truot: {_ck}')
# (f) evidence shown on the site must be labelled when produced under another config
_arch = [k for k, v in (D.get('sweeps') or {}).items() if isinstance(v, dict) and v and not v.get('_current')]
warn(not _arch, f'{len(_arch)} bang chung cu (cau hinh khac) — trang phai hien nhan LUU TRU: ' + ' '.join(_arch))

# ---------- 8d. TOP110 + S1 KHOA LAI (26/09/2026) — mot dinh nghia o moi lop ----------
try:
    from produce2 import PROD as _PR
    import exit_rules as _ER
    check(CFP.get('top_n') == _PR['top_n'] == 110, f"top_n trang {CFP.get('top_n')} / PROD {_PR['top_n']} — phai 110")
    check(CFP.get('profit_lock') == _PR.get('profit_lock') and _ER.tiers(CFP) == [(0.08, 0.02), (0.12, 0.05)],
          f"profit_lock trang {CFP.get('profit_lock')} lech PROD {_PR.get('profit_lock')}")
    check(not CFP.get('use_be'), 'use_be (ve bo +1%) van bat trong cau hinh dang chay')
    _tr = (D.get('prod') or {}).get('trades') or D.get('trades') or []
    if _tr:
        check(not any(str(t.get('reason', '')).startswith('Về bờ') for t in _tr), 'backtest con lenh "Về bờ" (+1%)')
        check(any(_ER.is_lock_reason(t.get('reason')) for t in _tr), 'backtest khong co lenh nao ra bang khoa lai S1')
    for _p in (D.get('open_positions') or []):
        for _k in ('peak_gain', 'profit_floor', 'profit_lock_active', 'sellable', 'action'):
            check(_k in _p, f"vi the {_p.get('sym')} thieu truong {_k} (exit_rules.status)")
    check('function erDecide' in html and 'Khoá lãi S1' in html, 'trang thieu exit_rules.js (luat thoat S1 cua Viec can lam)')
    check('luật về bờ' not in html, 'trang con cau "luật về bờ" o Viec can lam')
    for _p in (_pf.get('open') or []):
        # Buoc nay chay TRUOC portfolio.py (so con la ban cua lan dang truoc) nen chi canh bao;
        # CHOT CUNG nam o buoc dang: portfolio.py nang cap trang thai roi tu kiem, truot -> exit 1.
        warn('profit_floor' in _p, f"so ghi tien: {_p.get('sym')} chua co truong khoa lai — buoc dang se nang cap, khong duoc thi DUNG")
    if _pf.get('prod_config_hash') and _pf.get('prod_config_hash') != CFP.get('prod_config_hash'):
        warn(False, f"so ghi tien dang o cau hinh {_pf.get('prod_config_hash')} != {CFP.get('prod_config_hash')} — buoc dang se nang cap trang thai")
except SystemExit:
    raise
except Exception as e:
    check(False, f'khong kiem duoc TOP110 + S1: {type(e).__name__}: {e}')

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
