# -*- coding: utf-8 -*-
"""R37 — Monte Carlo cho CÁCH GIẢI NGÂN (anh Sơn 14/10/2026).

Câu hỏi: cách chia vốn hiện tại (base_size 0.42, hệ số đèn Xanh/Vàng/Cam/Đỏ = 1/0.6/0.35/0.2, trần mỗi mã 50%,
tối đa 12 mã, trần ngành 30%) đã tối ưu chưa?

KHÓA LẠI mọi thứ khác đúng như PROD (produce2.PROD): 9 điều kiện vào lệnh, TOP110, điểm sàn, luật thoát S1,
van T+4, MA30, đèn thị trường. Chỉ đổi các núm GIẢI NGÂN, từng núm một (coordinate descent), mọi núm khác giữ
ở giá trị tốt nhất hiện có.

Tiêu chí CHẤP NHẬN thay đổi giống R11 (đã dùng để duyệt PROD): chỉ đổi khi BỀN —
  * MC thực thi: trung vị tổng lợi nhuận qua NSEED lần lỡ ngẫu nhiên 10% lệnh vượt bản đang chạy ≥ 2%, p10 không kém;
  * bình nguyên: trung bình MC của hai giá trị kề cũng vượt bản đang chạy;
  * bootstrap khối 20 phiên (2000 đường): DD p95 không xấu hơn quá 1 điểm %;
  * DD thực ≤ 12% và không xấu hơn quá 1 điểm %;
  * 2023-26 không kém, 2019-22 không kém quá 10%, cả kỳ không thấp hơn.
Kết quả: evidence/r37_mc_sizing.json (Artifact "nghien-cuu"). KHÔNG đụng PROD, KHÔNG đăng web.
"""
import os, sys, json, time, hashlib
import numpy as np
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
OUT = os.environ.get('OUT', 'evidence/r37_mc_sizing.json')
NSEED = int(os.environ.get('NSEED', 40))          # lần lỡ lệnh ngẫu nhiên cho mỗi cấu hình
NSEED_FINAL = int(os.environ.get('NSEED_FINAL', 120))
PROCS = int(os.environ.get('PROCS', 3))

LIGHTS = ('XANH', 'VANG', 'CAM', 'DO')
# Núm giải ngân và lưới thử (giá trị PROD nằm trong lưới).
STEPS = [
    ('base_size', [0.30, 0.34, 0.38, 0.42, 0.46, 0.50, 0.55]),
    ('sm_VANG', [0.40, 0.50, 0.60, 0.70, 0.80, 1.00]),
    ('sm_CAM', [0.15, 0.25, 0.35, 0.45, 0.60]),
    ('sm_DO', [0.0, 0.10, 0.20, 0.30, 0.40]),
    ('max_pos', [0.30, 0.40, 0.50, 0.60]),
    ('max_pos_n', [6, 8, 10, 12, 15]),
    ('sector_cap', [0.20, 0.25, 0.30, 0.35, 0.40]),
]

_E = None
_PROD = None


def _init():
    global _E, _PROD
    import engine2 as E
    E.load(); _E = E
    from produce2 import PROD
    _PROD = PROD


def _key(o):
    return hashlib.md5(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _cfg(over):
    """PROD + núm đổi. sm_* ghép vào size_map (Xanh luôn 1.0 — base_size đã là thang)."""
    C = dict(_E.CFG); C.update(_PROD)
    sm = dict(C.get('size_map') or {})
    for k, v in over.items():
        if k.startswith('sm_'):
            sm[k[3:]] = float(v)
        else:
            C[k] = v
    C['size_map'] = sm
    return C


def _seg(eq, a, b):
    v = np.array([x[1] for x in eq if a <= x[0][:4] <= b], float)
    return float(v[-1] / v[0] - 1) if len(v) > 20 else None


def _boot(eq, n=2000, blk=20, seed=7):
    v = np.array([x[1] for x in eq], float); r = v[1:] / v[:-1] - 1; T = len(r)
    rng = np.random.default_rng(seed); dds = []; rets = []
    nb = T // blk + 1
    for _ in range(n):
        st = rng.integers(0, T - blk, nb); p = np.concatenate([r[s:s + blk] for s in st])[:T]
        nav = np.cumprod(1 + p); dd = 1 - nav / np.maximum.accumulate(nav)
        dds.append(dd.max()); rets.append(nav[-1] - 1)
    dds = np.array(dds); rets = np.array(rets)
    return dict(dd_p50=float(np.median(dds)), dd_p95=float(np.quantile(dds, .95)),
                p_dd15=float((dds > .15).mean()), ret_p05=float(np.quantile(rets, .05)), ret_p50=float(np.median(rets)))


def evaluate(args):
    over, nseed = args
    C = _cfg(over)
    r = _E.run(C, log=False); m = _E.metrics(r)
    out = dict(over=over, size_map=C['size_map'], ret=m['total_return'], cagr=m['cagr'], dd=m['maxdd'], pf=m['pf'],
               sharpe=m['sharpe'], trades=m['trades'], h1=_seg(r['eq'], '2019', '2022'), h2=_seg(r['eq'], '2023', '2026'))
    out.update(_boot(r['eq']))
    mc = []
    for s in range(nseed):
        C2 = dict(C); C2.update(miss_prob=0.10, miss_seed=1000 + s)
        mc.append(_E.metrics(_E.run(C2, log=False))['total_return'])
    mc = np.array(mc)
    out.update(mc_p50=float(np.median(mc)), mc_p10=float(np.quantile(mc, .10)), mc_p90=float(np.quantile(mc, .90)),
               nseed=nseed)
    return out


def accept(rows, inc, knob):
    best, why = inc, 'giữ (không giá trị nào vượt đủ điều kiện bền vững)'
    for k, r in enumerate(rows):
        if r['v'] == inc['v']:
            continue
        fail = []
        if r['mc_p50'] < inc['mc_p50'] * 1.02: fail.append('MC trung vị chưa hơn 2%')
        if r['mc_p10'] < inc['mc_p10']: fail.append('MC p10 kém hơn')
        if r['dd_p95'] > inc['dd_p95'] + 0.01: fail.append('DD p95 bootstrap xấu hơn >1đ%')
        if r['dd'] > inc['dd'] + 0.010 or r['dd'] > 0.12: fail.append('DD thực vượt ngưỡng')
        if (r['h2'] or 0) < (inc['h2'] or 0): fail.append('2023-26 kém hơn')
        if (r['h1'] or 0) < (inc['h1'] or 0) * 0.9: fail.append('2019-22 kém hơn >10%')
        if r['ret'] < inc['ret']: fail.append('cả kỳ thấp hơn')
        nb = [rows[j]['mc_p50'] for j in (k - 1, k + 1) if 0 <= j < len(rows)]
        if not nb or np.mean(nb) < inc['mc_p50']: fail.append('không phải bình nguyên')
        r['loai_vi'] = fail
        if not fail and (best is inc or r['mc_p50'] > best['mc_p50']):
            best, why = r, f"đổi {knob}: MC trung vị {inc['mc_p50']*100:.1f}% → {r['mc_p50']*100:.1f}%"
    return best, why


def prod_value(knob):
    if knob.startswith('sm_'):
        return float(_PROD['size_map'][knob[3:]])
    return _PROD.get(knob, _E.CFG.get(knob))


def main():
    t0 = time.time()
    _init()
    cache = {}
    log = []
    base = {}                      # chỉ chứa núm đã đổi khỏi PROD

    def norm(o):
        """Bỏ núm trùng giá trị PROD để cấu hình gốc chỉ tính MỘT lần (khóa cache ổn định)."""
        return {k: v for k, v in o.items() if v != prod_value(k)}

    def run_rows(pool, knob, grid):
        todo, seen = [], set()
        for v in grid:
            o = norm(dict(base, **{knob: v}))
            k = _key(o)
            if k not in cache and k not in seen:
                todo.append((o, NSEED)); seen.add(k)
        for res in pool.imap_unordered(evaluate, todo):
            cache[_key(res['over'])] = res
            print(f"  {json.dumps(res['over']) if res['over'] else 'PROD'}: ret {res['ret']*100:.1f}% dd {res['dd']*100:.2f}% "
                  f"mc50 {res['mc_p50']*100:.1f}% mc10 {res['mc_p10']*100:.1f}% ddp95 {res['dd_p95']*100:.1f}%", flush=True)
        rows = []
        for v in grid:
            r = dict(cache[_key(norm(dict(base, **{knob: v})))]); r['v'] = v
            rows.append(r)
        return rows

    with Pool(PROCS, initializer=_init) as pool:
        goc = run_rows(pool, 'base_size', [prod_value('base_size')])[0]
        print(f"GỐC (PROD): ret {goc['ret']*100:.1f}% cagr {goc['cagr']*100:.2f}% dd {goc['dd']*100:.2f}% pf {goc['pf']} "
              f"sharpe {goc['sharpe']} lệnh {goc['trades']} · MC50 {goc['mc_p50']*100:.1f}%", flush=True)
        for pas in (1, 2):
            changed = False
            for knob, grid in STEPS:
                print(f'== vòng {pas} · {knob}', flush=True)
                cur = base.get(knob, prod_value(knob))
                g = sorted(set(grid + [cur]))
                rows = run_rows(pool, knob, g)
                inc = next(r for r in rows if r['v'] == cur)
                best, why = accept(rows, inc, knob)
                if best is not inc:
                    base[knob] = best['v']; changed = True
                log.append(dict(vong=pas, num=knob, hien_tai=cur, chon=base.get(knob, cur), ly_do=why,
                                bang=[{k: r[k] for k in ('v', 'ret', 'dd', 'pf', 'sharpe', 'trades', 'mc_p50', 'mc_p10',
                                                          'mc_p90', 'dd_p95', 'h1', 'h2')} | {'loai_vi': r.get('loai_vi', [])}
                                      for r in rows]))
                json.dump(dict(trang_thai='dang_chay', goc_prod={k: goc[k] for k in ('ret','dd','pf','mc_p50')}, nhat_ky=log, base=base), open(OUT, 'w'), ensure_ascii=False,
                          indent=1, default=str)
            if not changed:
                break

        # Đối chiếu cuối với nhiều lần lỡ lệnh hơn: PROD vs cấu hình chọn được (nếu khác)
        cuoi = [({}, NSEED_FINAL)] + ([(dict(base), NSEED_FINAL)] if base else [])
        final = list(pool.imap(evaluate, cuoi))

    ket = dict(
        trang_thai='xong', chay_phut=round((time.time() - t0) / 60, 1), nseed=NSEED, nseed_cuoi=NSEED_FINAL,
        prod=dict(base_size=_PROD['base_size'], size_map=_PROD['size_map'], max_pos=_PROD['max_pos'],
                  max_pos_n=_PROD['max_pos_n'], sector_cap=_PROD.get('sector_cap', 0.30)),
        goc_prod={k: goc[k] for k in ('ret', 'cagr', 'dd', 'pf', 'sharpe', 'trades', 'mc_p50', 'mc_p10', 'dd_p95', 'h1', 'h2')},
        doi_so_voi_prod=base, ket_luan=('Cách giải ngân hiện tại đã ở vùng tốt nhất theo tiêu chí bền vững'
                                        if not base else 'Có cấu hình bền hơn — xem doi_so_voi_prod và doi_chieu_cuoi'),
        doi_chieu_cuoi=final, nhat_ky=log)
    json.dump(ket, open(OUT, 'w'), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: ket[k] for k in ('chay_phut', 'doi_so_voi_prod', 'ket_luan')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
