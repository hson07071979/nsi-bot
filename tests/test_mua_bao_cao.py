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


if __name__ == '__main__':
    ok = 0
    for fn in T:
        try:
            fn(); print('PASS', fn.__name__); ok += 1
        except Exception as e:
            import traceback; traceback.print_exc()
            print('FAIL', fn.__name__, type(e).__name__, e)
    print(f'{ok}/{len(T)} passed'); sys.exit(0 if ok == len(T) else 1)
