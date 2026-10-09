# -*- coding: utf-8 -*-
"""R36 (09/10/2026) — Ngay cong bo BCTC da nguon: bot dung so quy moi tu PHIEN SAU
ngay ban dau duoc dang (Vietstock + CafeF + Vietcap, >= 2 nguon khop) thay vi
max(ngay Vietcap, het quy + 45 ngay). CHI NGHIEN CUU — prep.NGAY_DA_NGUON van TAT.

Do:
  1. do phu tung nguon, cach chon ngay (vs+cf, vs+vc, lech, 1 nguon, cach cu)
  2. so ngay som hon cach cu, theo quy trong nam (Q1..Q4) va theo nam
  3. backtest PROD: A = cach cu, B = da nguon; moi ben 20 seed Monte Carlo lo 10% lenh
  4. hom nay: bao nhieu ma doi quy dang dung neu bat
"""
import os, sys, json, subprocess, datetime as dt, warnings; warnings.filterwarnings('ignore')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from collections import Counter, defaultdict
import numpy as np
import prep
import engine2 as E
from engine import as_of
from research import common as C

NSEED = int(os.environ.get('R36_SEED', os.environ.get('NSEED', '30')))
OUT = 'evidence/r36_ngay_cong_bo.json'

if not os.path.exists(prep.NGAY_FILE):
    subprocess.run([sys.executable, 'fetch_ngay_cong_bo.py'], check=True)
nf = json.load(open(prep.NGAY_FILE, encoding='utf-8'))


def bo(bat, san=10):
    prep.NGAY_DA_NGUON = bat; prep.SAN_NGAY = san; prep._ngay_cache.clear()
    return prep.parse_funda('data/funda_raw2.json')


A, B = bo(False), bo(True)

# ---------- 1 + 2: ngay ----------
cach, som_q, som_nam, mau = Counter(), defaultdict(list), defaultdict(list), []
for s, rb in B.items():
    ra = {(r['y'], r['q']): r for r in A.get(s, [])}
    for r in rb:
        if r['y'] < 2019: continue
        a = ra.get((r['y'], r['q']))
        if not a: continue
        ng = r.get('nguon_ngay') or 'cach cu'
        cach[ng.split(':')[0] if ng.startswith('lech') else ng] += 1
        d = (a['avail'] - r['avail']).days
        som_q[f"Q{r['q']}"].append(d); som_nam[str(r['y'])].append(d)
        if s in ('FPT', 'HPG', 'VCB', 'MWG', 'PET', 'HAG') and r['y'] >= 2024:
            mau.append(dict(sym=s, quy=f"{r['y']}Q{r['q']}", cu=str(a['avail']), moi=str(r['avail']), nguon=ng))


def tk(v):
    v = np.array(v) if v else np.array([0])
    return dict(n=int(len(v)), tb=round(float(v.mean()), 1), trung_vi=float(np.median(v)),
                p10=float(np.percentile(v, 10)), p90=float(np.percentile(v, 90)),
                muon_hon=int((v < 0).sum()))


phu = dict(ma=len(nf), vietstock=sum(1 for d in nf.values() if d.get('vs')),
           cafef=sum(1 for d in nf.values() if d.get('cf')))
print('DO PHU', phu)
print('CACH CHON', dict(cach.most_common()))
for k in sorted(som_q): print('  som hon (ngay)', k, tk(som_q[k]))
for k in sorted(som_nam): print('  som hon (ngay)', k, tk(som_nam[k]))

# ---------- 4: hom nay ----------
hn = dt.date.today()
doi = []
for s in B:
    fa = as_of(E.funda_timeline(A[s]), hn) if A.get(s) else None
    fb = as_of(E.funda_timeline(B[s]), hn) if B.get(s) else None
    la, lb = (fa or {}).get('label'), (fb or {}).get('label')
    if la != lb: doi.append((s, la, lb))
print('HOM NAY doi quy dang dung:', len(doi), doi[:20])

# ---------- 3: backtest ----------
out = dict(meta=C.meta(dict(script='r36_ngay_cong_bo', nseed=NSEED)), do_phu=phu, cach_chon=dict(cach),
           som_hon_theo_quy={k: tk(v) for k, v in sorted(som_q.items())},
           som_hon_theo_nam={k: tk(v) for k, v in sorted(som_nam.items())},
           mau=mau, hom_nay_doi=doi)
VET = {}
# C = da nguon nhung GIU san 45 ngay: chi keo quy 2 / quy 4 (Vietcap ghi ngay ban soat
#     xet / kiem toan) ve moc 45 ngay — tach phan loi/hai cua 'som hon 45 ngay'.
for ten, bat, san in (('A_cach_cu', False, 10), ('B_da_nguon_san10', True, 10), ('C_da_nguon_san45', True, 45)):
    prep.NGAY_DA_NGUON = bat; prep.SAN_NGAY = san; prep._ngay_cache.clear(); E._CACHE.clear(); E.load()
    s, r = C.run({}, name=ten, keep=True)
    VET[ten] = r['trades']
    print(ten, 'tung nam', {k: round(v * 100, 1) for k, v in s['yearly'].items()}, '| tap trung', s['concentration'], flush=True)
    mc = [C.run(dict(miss_prob=0.10, miss_seed=sd), name=f'{ten}|{sd}')['metrics']['total_return']
          for sd in range(1, NSEED + 1)]
    s['mc_med'] = float(np.median(mc)); s['mc_p10'] = float(np.percentile(mc, 10))
    print(C.line(s), '| MC med %+.1f%% p10 %+.1f%%' % (s['mc_med'] * 100, s['mc_p10'] * 100), flush=True)
    out[ten] = s
# ---------- vi sao khac: lenh co o ben nay ma khong co o ben kia ----------
def _k(t): return (t['sym'], t['entry'])
A_ = {}
for t in VET['A_cach_cu']: A_.setdefault(_k(t), []).append(t)
for ten in ('B_da_nguon_san10', 'C_da_nguon_san45'):
    B_ = {}
    for t in VET[ten]: B_.setdefault(_k(t), []).append(t)
    chi_a = sorted(((k, sum(x['pnl_vnd'] for x in v)) for k, v in A_.items() if k not in B_), key=lambda x: -abs(x[1]))
    chi_b = sorted(((k, sum(x['pnl_vnd'] for x in v)) for k, v in B_.items() if k not in A_), key=lambda x: -abs(x[1]))
    print(f'\n{ten}: lenh chi co o A {len(chi_a)} (tong {sum(x[1] for x in chi_a)/1e9:+.2f} ty) | '
          f'chi co o {ten[0]} {len(chi_b)} (tong {sum(x[1] for x in chi_b)/1e9:+.2f} ty)')
    print('  chi A, lon nhat:', [(f'{k[0]} {k[1]}', round(v / 1e9, 2)) for k, v in chi_a[:12]])
    print(f'  chi {ten[0]}, lon nhat:', [(f'{k[0]} {k[1]}', round(v / 1e9, 2)) for k, v in chi_b[:12]])
    out['khac_' + ten] = dict(chi_a=[(k, v) for k, v in chi_a[:40]], chi_b=[(k, v) for k, v in chi_b[:40]])

prep.NGAY_DA_NGUON = False; prep.SAN_NGAY = 10
os.makedirs('evidence', exist_ok=True)
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, default=str, indent=1)
print('ghi', OUT)
