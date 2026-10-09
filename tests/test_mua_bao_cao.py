# -*- coding: utf-8 -*-
"""MUA BAO CAO (anh Son duyet 09/10/2026):
  1. quy moi chi vao bo may khi du 3 phan (KQKD + LCTT + bang chi so), toi da cho 15 ngay
  3. tai lai lan 2 + muon so dem truoc toi da 3 dem
  4. nhat ky ma doi trang thai vi quy moi
Khong can du lieu that: dung so gia lap.
Run: python3 tests/test_mua_bao_cao.py"""
import os, sys, json, tempfile, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
T = []
def test(fn): T.append(fn); return fn


def _quy(y, q, pub, ratio=True, is_=True, cf=True, npat=100e9):
    """Ba phan Vietcap cho mot quy, theo dung khuon API."""
    d = {'ratio': [], 'is': [], 'cf': []}
    if ratio: d['ratio'].append({'yearReport': y, 'quarter': q, 'roe': 0.2, 'ebit': 50e9, 'debtToEquity': 0.5})
    if is_: d['is'].append({'yearReport': y, 'lengthReport': q, 'isa3': 1000e9, 'isa22': npat,
                            'isa8': -5e9, 'isa14': 1e9, 'isa16': 120e9, 'publicDate': pub + 'T00:00:00'})
    if cf: d['cf'].append({'yearReport': y, 'lengthReport': q, 'cfa18': 30e9, 'publicDate': pub + 'T00:00:00'})
    return d


def _ma(*quys):
    out = {'ratio': [], 'is': [], 'cf': []}
    for d in quys:
        for k in out: out[k] += d[k]
    return out


def _parse(raw):
    from prep import parse_funda
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(raw, f); p = f.name
    try: return parse_funda(p)
    finally: os.remove(p)


LICH = [(2025, 3, '2025-10-24'), (2025, 4, '2026-03-20'), (2026, 1, '2026-04-28'), (2026, 2, '2026-08-22')]


@test
def test_du_phan_khong_doi():
    rows = _parse({'X': _ma(*[_quy(*q) for q in LICH], _quy(2026, 3, '2026-10-24'))})['X']
    m = rows[-1]
    assert (m['y'], m['q']) == (2026, 3) and 'thieu_phan' not in m
    assert m['avail'] == dt.date(2026, 11, 14)          # san 45 ngay hien hanh van giu


@test
def test_thieu_bang_chi_so_cho_15_ngay():
    # KQKD Q3 cong bo muon (25/11, sau san 45 ngay) nhung bang chi so chua ve
    rows = _parse({'X': _ma(*[_quy(*q) for q in LICH], _quy(2026, 3, '2026-11-25', ratio=False))})['X']
    m = rows[-1]
    assert m['thieu_phan'] == ['ratio'], m.get('thieu_phan')
    assert m['avail'] == dt.date(2026, 12, 10), m['avail']   # 25/11 + 15 ngay
    from engine import funda_timeline, as_of
    tl = funda_timeline(rows)
    assert as_of(tl, dt.date(2026, 12, 1))['label'] == '2026Q2'   # trong 15 ngay: giu quy cu
    assert as_of(tl, dt.date(2026, 12, 10))['label'] == '2026Q3'  # qua han: nhan, kem co thieu


@test
def test_thieu_lctt():
    rows = _parse({'X': _ma(*[_quy(*q) for q in LICH], _quy(2026, 3, '2026-11-20', cf=False))})['X']
    assert rows[-1]['thieu_phan'] == ['cf']


@test
def test_quy_moi_chua_co_kqkd_bi_bo():
    rows = _parse({'X': _ma(*[_quy(*q) for q in LICH], _quy(2026, 3, '2026-10-24', is_=False, cf=False))})['X']
    assert (rows[-1]['y'], rows[-1]['q']) == (2026, 2)


@test
def test_phan_ma_ma_von_khong_co_thi_khong_doi():
    # ma khong bao gio co bang chi so (vd moi niem yet): khong duoc cho vo han
    rows = _parse({'X': _ma(*[_quy(*q, ratio=False) for q in LICH], _quy(2026, 3, '2026-10-24', ratio=False))})['X']
    assert 'thieu_phan' not in rows[-1] and (rows[-1]['y'], rows[-1]['q']) == (2026, 3)


@test
def test_lich_su_khong_doi():
    # quy GIUA lich su thieu phan (du lieu cu khong day du) -> khong dung toi
    q = [_quy(*x) for x in LICH]
    q[1] = _quy(2025, 4, '2026-03-20', ratio=False)
    rows = _parse({'X': _ma(*q)})['X']
    assert [('thieu_phan' in r) for r in rows] == [False] * 4
    assert rows[1]['avail'] == dt.date(2026, 3, 20)


@test
def test_muon_dem_truoc_toi_da_3_dem():
    import fetch_funda as FF
    truoc = {'A': {'is': [1], 'cf': [2], 'ratio': [3]}, 'B': {'is': [1], 'cf': [2], 'ratio': [3]}}
    res = {'A': {'is': [9], 'cf': [], 'ratio': [9]}, 'B': {'is': [9], 'cf': [9], 'ratio': [9]}}
    tuoi, muon = FF.muon_dem_truoc(res, truoc, {})
    assert muon == {'A': ['cf']} and tuoi == {'A': 1} and res['A']['cf'] == [2]
    for n in (2, 3):
        res = {'A': {'is': [9], 'cf': [], 'ratio': [9]}}
        tuoi, muon = FF.muon_dem_truoc(res, truoc, tuoi)
        assert tuoi == {'A': n}
    res = {'A': {'is': [9], 'cf': [], 'ratio': [9]}}
    tuoi, muon = FF.muon_dem_truoc(res, truoc, tuoi)
    assert muon == {} and tuoi == {} and res['A']['cf'] == []    # dem thu 4: thieu that
    # du phan lai -> tuoi ve 0
    tuoi, _ = FF.muon_dem_truoc({'A': {'is': [9], 'cf': [9], 'ratio': [9]}}, truoc, {'A': 2})
    assert tuoi == {}


@test
def test_nhat_ky_bctc():
    import watchlist as W
    r1 = [dict(sym='A', quarter='2026Q2', score=52, blocked=False, block='', tim=False, wl=True, fa_wl=False),
          dict(sym='B', quarter='2026Q2', score=40, blocked=False, block='', tim=False, wl=False, fa_wl=False)]
    st = {}
    W.nhat_ky_bctc(st, r1, '2026-11-14')
    assert st['bctc_log'] == []                              # lan dau: chi ghi nho
    r2 = [dict(r1[0], quarter='2026Q3', score=47, blocked=True, block='CFO < 0', wl=False),
          dict(r1[1])]
    W.nhat_ky_bctc(st, r2, '2026-11-15')
    assert len(st['bctc_log']) == 1
    g = st['bctc_log'][0]
    assert g['sym'] == 'A' and g['tu'] == '2026Q2' and g['den'] == '2026Q3'
    assert g['doi'] == ['điểm 52 → 47', 'cổng rủi ro: qua → chặn (CFO < 0)', 'ra khỏi danh sách mua'], g['doi']
    W.nhat_ky_bctc(st, r2, '2026-11-15')                      # chay lai cung phien: khong ghi trung
    assert len(st['bctc_log']) == 1


@test
def test_ngay_dau_quy_tac():
    from prep import ngay_dau
    D = dt.date
    # FPT Q2/2026: Vietstock 27/07, CafeF 28/07 khop; Vietcap 22/08 la ban soat xet
    assert ngay_dau({'vs': '2026-07-27T22:34', 'cf': '2026-07-28T09:51', 'vc': '2026-08-22'}, 2026, 2) == (D(2026, 7, 28), 'vs+cf')
    # FPT Q1/2025: CafeF muon (21/05); Vietstock 22/04 khop Vietcap 23/04
    assert ngay_dau({'vs': '2025-04-22', 'cf': '2025-05-21', 'vc': '2025-04-23'}, 2025, 1) == (D(2025, 4, 23), 'vs+vc')
    # lech nhau het -> ngay muon nhat (an toan)
    assert ngay_dau({'vs': '2025-04-01', 'cf': '2025-05-21', 'vc': '2025-04-23'}, 2025, 1)[0] == D(2025, 5, 21)
    # ngay truoc khi het quy (kieu CAP 2023Q1) bi loai
    assert ngay_dau({'vc': '2023-01-31'}, 2023, 1) == (None, None)


@test
def test_da_nguon_bat_tat():
    import prep
    raw = {'X': _ma(*[_quy(*q) for q in LICH])}
    ngay = {'X': {'vs': {'2026Q2': '2026-07-27T22:34', '2025Q4': '2026-01-26T21:36'},
                  'cf': {'2026Q2': '2026-07-28T09:51'}}}
    # PROD = bien the C (anh Son chot 09/10/2026): bat, san 45 ngay
    assert prep.NGAY_DA_NGUON is True and prep.SAN_NGAY == 45, 'PROD phai la bien the C'
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(ngay, f); pn = f.name
    cu = (prep.NGAY_DA_NGUON, prep.NGAY_FILE, prep.SAN_NGAY)
    try:
        prep.NGAY_DA_NGUON = False; prep._ngay_cache.clear()
        tat = {(r['y'], r['q']): r['avail'] for r in _parse(raw)['X']}
        prep.NGAY_DA_NGUON, prep.NGAY_FILE, prep.SAN_NGAY = True, pn, 10; prep._ngay_cache.clear()
        bat = {(r['y'], r['q']): r['avail'] for r in _parse(raw)['X']}
        prep.SAN_NGAY = 45; prep._ngay_cache.clear()
        c = {(r['y'], r['q']): r['avail'] for r in _parse(raw)['X']}
        prep.NGAY_FILE = pn + '.khong-co'; prep._ngay_cache.clear()
        mat_file = {(r['y'], r['q']): r['avail'] for r in _parse(raw)['X']}
    finally:
        prep.NGAY_DA_NGUON, prep.NGAY_FILE, prep.SAN_NGAY = cu; prep._ngay_cache.clear(); os.remove(pn)
    # bien the C: Q2/2026 ban dau 28/07 -> keo ve moc 45 ngay 14/08 (cach cu 22/08)
    assert c[(2026, 2)] == dt.date(2026, 8, 14), c[(2026, 2)]
    # mat file ngay cong bo -> tu lui ve cach cu, khong hong
    assert mat_file == tat
    assert tat[(2026, 2)] == dt.date(2026, 8, 22) and bat[(2026, 2)] == dt.date(2026, 7, 29)
    # Q4/2025: chi Vietstock 26/01 vs Vietcap 20/03 (kiem toan) lech, ngay muon nhat la cua
    # Vietcap -> khong co Vietstock/CafeF xac nhan -> giu nguyen cach cu
    assert bat[(2025, 4)] == tat[(2025, 4)] == dt.date(2026, 3, 20)
    # quy khong co ngay Vietstock/CafeF -> giu nguyen cach cu (Vietcap + san 45 ngay)
    assert bat[(2025, 3)] == tat[(2025, 3)] == dt.date(2025, 11, 14)
    assert bat[(2026, 1)] == tat[(2026, 1)]


@test
def test_phan_loai_ten_file():
    from sources.bctc_ngay import phan_loai, gom
    assert phan_loai('Báo cáo tài chính Hợp nhất quý 2 năm 2026') == ((2026, 2), True)
    assert phan_loai('Báo cáo tài chính công ty mẹ quý 2 năm 2026') == ((2026, 2), False)
    assert phan_loai('Báo cáo tài chính hợp nhất quý 2 năm 2026 (đã soát xét)') is None
    assert phan_loai('Báo cáo tài chính Hợp nhất Soát xét 6 tháng đầu năm 2026') is None
    assert phan_loai('Báo cáo tài chính Hợp nhất Kiểm toán năm 2024') is None
    # cong ty me ra truoc hop nhat: CHI tinh hop nhat (bo may dung so hop nhat)
    g = gom([((2026, 2), False, '2026-07-20T10:00'), ((2026, 2), True, '2026-07-27T22:34'),
             ((2026, 1), False, '2026-04-20T10:00')])
    assert g == {'2026Q2': '2026-07-27T22:34', '2026Q1': '2026-04-20T10:00'}


if __name__ == '__main__':
    ok = 0
    for fn in T:
        try:
            fn(); print('PASS', fn.__name__); ok += 1
        except Exception as e:
            import traceback; traceback.print_exc()
            print('FAIL', fn.__name__, type(e).__name__, e)
    print(f'{ok}/{len(T)} passed'); sys.exit(0 if ok == len(T) else 1)
