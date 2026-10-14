# -*- coding: utf-8 -*-
"""R37b — Kiểm riêng hệ số đèn CAM 0.45 (anh Sơn chọn phương án B, 14/10/2026).

R37 cho thấy Cam 0.35→0.45 qua tiêu chí R11 nhưng lợi dồn vào 2023–26 và có dạng "tăng size thì tăng lãi tới trần DD".
Lượt này KHÓA mọi thứ như PROD (kể cả Đỏ 0.2), chỉ đổi sm_CAM, và kiểm những điều R37 chưa kiểm.

TIÊU CHÍ CHẤP NHẬN — chốt TRƯỚC khi xem kết quả (không sửa sau):
  T1 walk-forward neo: năm kiểm Y = 2021..2026, chọn sm_CAM trên lưới bằng dữ liệu 2019..Y-1 (lãi kép cao nhất,
     DD giai đoạn học ≤ 12%), đo năm Y. Lãi kép ngoài mẫu của cách chọn này ≥ PROD.
  T2 từng năm: 0.45 hơn PROD ở ≥ 5/8 năm (2019..2026).
  T3 bỏ-một-năm: bỏ lần lượt từng năm, lãi kép các năm còn lại của 0.45 vẫn ≥ PROD ở MỌI lần bỏ.
  T4 bình nguyên: trung vị MC (NSEED lần lỡ 10% lệnh) của 0.40 và 0.50 đều > PROD.
  T5 rủi ro: DD thực ≤ 12%; DD p95 bootstrap không xấu hơn quá 1 điểm %; xác suất DD>15% không tăng quá 3 điểm %.
Kết luận: đạt cả 5 → "đủ bằng chứng để anh cân nhắc đổi"; thiếu bất kỳ → "giữ PROD". KHÔNG tự đổi PROD.

Ghi chú phương pháp: lợi suất từng năm cắt từ MỘT đường vốn chạy cả kỳ (vị thế mang qua năm vẫn tính), nên walk-forward
ở đây là chọn tham số ngoài mẫu trên đường vốn liên tục, không phải chạy lại engine từ đầu mỗi năm.
Kết quả: evidence/r37b_cam.json.
"""
import os, sys, json, time
import numpy as np
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'research'))
import r37_mc_sizing as R  # noqa: E402  (_init, _cfg, _boot dùng chung — cùng cách ghép size_map)

OUT = os.environ.get('OUT', 'evidence/r37b_cam.json')
NSEED = int(os.environ.get('NSEED_FINAL', 120))
PROCS = int(os.environ.get('PROCS', 3))
GRID = [0.25, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]
PROD_CAM, CAND = 0.35, 0.45
YEARS = [str(y) for y in range(2019, 2027)]


def nam(eq):
    """Lợi suất và DD từng năm từ đường vốn cả kỳ: gốc = NAV cuối năm trước (năm đầu: NAV đầu kỳ)."""
    out, prev = {}, eq[0][1]
    for y in YEARS:
        v = np.array([x[1] for x in eq if x[0][:4] == y], float)
        if not len(v):
            continue
        path = np.concatenate([[prev], v])
        dd = 1 - path / np.maximum.accumulate(path)
        out[y] = dict(ret=float(v[-1] / prev - 1), dd=float(dd.max()))
        prev = v[-1]
    return out


def dd_doan(eq, den_nam):
    v = np.array([x[1] for x in eq if x[0][:4] <= den_nam], float)
    return float((1 - v / np.maximum.accumulate(v)).max()) if len(v) else 0.0


def evaluate(cam):
    E = R._E
    C = R._cfg({'sm_CAM': cam})
    r = E.run(C, log=False); m = E.metrics(r)
    tr = r['trades']
    cam_tr = [t for t in tr if t.get('light') == 'CAM']
    by = {}
    for t in tr:
        y = str(t['entry'])[:4]
        b = by.setdefault(y, dict(n=0, n_cam=0, lai_cam_vnd=0.0))
        b['n'] += 1
        if t.get('light') == 'CAM':
            b['n_cam'] += 1; b['lai_cam_vnd'] += float(t.get('pnl_vnd') or 0)
    out = dict(cam=cam, ret=m['total_return'], cagr=m['cagr'], dd=m['maxdd'], pf=m['pf'], sharpe=m['sharpe'],
               trades=m['trades'], nam=nam(r['eq']), lenh_nam=by,
               lenh_cam=dict(n=len(cam_tr), thang=sum(1 for t in cam_tr if t['pnl_pct'] > 0),
                             tb_pct=float(np.mean([t['pnl_pct'] for t in cam_tr])) if cam_tr else None,
                             trung_vi_pct=float(np.median([t['pnl_pct'] for t in cam_tr])) if cam_tr else None),
               dd_hoc={y: dd_doan(r['eq'], y) for y in YEARS})
    out.update(R._boot(r['eq']))
    mc = []
    for s in range(NSEED):
        C2 = dict(C); C2.update(miss_prob=0.10, miss_seed=1000 + s)
        mc.append(E.metrics(E.run(C2, log=False))['total_return'])
    mc = np.array(mc)
    out.update(mc_p50=float(np.median(mc)), mc_p10=float(np.quantile(mc, .10)), mc_p90=float(np.quantile(mc, .90)))
    return out


def kep(rs):
    return float(np.prod([1 + x for x in rs]) - 1)


def main():
    t0 = time.time()
    R._init()
    with Pool(PROCS, initializer=R._init) as pool:
        rows = {r['cam']: r for r in pool.imap_unordered(evaluate, GRID)}
    for c in GRID:
        r = rows[c]
        print(f"Cam {c:.2f}: ret {r['ret']*100:.1f}% dd {r['dd']*100:.2f}% pf {r['pf']} lệnh {r['trades']} "
              f"mc50 {r['mc_p50']*100:.1f}% mc10 {r['mc_p10']*100:.1f}% ddp95 {r['dd_p95']*100:.1f}% pDD15 {r['p_dd15']*100:.1f}%",
              flush=True)
    P, X = rows[PROD_CAM], rows[CAND]

    # T1 walk-forward neo
    wf = []
    for i, y in enumerate(YEARS):
        if y < '2021':
            continue
        hoc = YEARS[:i]
        ung = []
        for c in GRID:
            if rows[c]['dd_hoc'][hoc[-1]] <= 0.12:
                ung.append((kep([rows[c]['nam'][h]['ret'] for h in hoc if h in rows[c]['nam']]), c))
        chon = max(ung)[1] if ung else PROD_CAM
        wf.append(dict(nam=y, chon=chon, ret_chon=rows[chon]['nam'][y]['ret'], ret_prod=P['nam'][y]['ret']))
    wf_chon, wf_prod = kep([w['ret_chon'] for w in wf]), kep([w['ret_prod'] for w in wf])
    T1 = wf_chon >= wf_prod

    # T2 từng năm
    tung = [dict(nam=y, prod=P['nam'][y]['ret'], cam45=X['nam'][y]['ret'], dd_prod=P['nam'][y]['dd'], dd_cam45=X['nam'][y]['dd'],
                 lenh_cam=X['lenh_nam'].get(y, {}).get('n_cam', 0)) for y in YEARS if y in P['nam'] and y in X['nam']]
    hon = sum(1 for t in tung if t['cam45'] > t['prod'])
    T2 = hon >= 5

    # T3 bỏ-một-năm
    loyo = []
    for y in YEARS:
        a = kep([X['nam'][k]['ret'] for k in YEARS if k != y and k in X['nam']])
        b = kep([P['nam'][k]['ret'] for k in YEARS if k != y and k in P['nam']])
        loyo.append(dict(bo=y, cam45=a, prod=b, hon=a >= b))
    T3 = all(l['hon'] for l in loyo)

    T4 = rows[0.40]['mc_p50'] > P['mc_p50'] and rows[0.50]['mc_p50'] > P['mc_p50']
    T5 = X['dd'] <= 0.12 and X['dd_p95'] <= P['dd_p95'] + 0.01 and X['p_dd15'] <= P['p_dd15'] + 0.03
    tc = dict(T1_walk_forward=T1, T2_tung_nam=T2, T3_bo_mot_nam=T3, T4_binh_nguyen=T4, T5_rui_ro=T5)
    ket = dict(
        chay_phut=round((time.time() - t0) / 60, 1), nseed=NSEED, tieu_chi=tc,
        ket_luan=('Đủ bằng chứng để anh cân nhắc đổi Cam 0.35→0.45' if all(tc.values())
                  else 'Giữ PROD — chưa đạt: ' + ', '.join(k for k, v in tc.items() if not v)),
        walk_forward=dict(chi_tiet=wf, lai_kep_chon=wf_chon, lai_kep_prod=wf_prod),
        tung_nam=dict(chi_tiet=tung, so_nam_hon=hon), bo_mot_nam=loyo,
        luoi={str(c): {k: rows[c][k] for k in ('ret', 'cagr', 'dd', 'pf', 'sharpe', 'trades', 'mc_p50', 'mc_p10', 'mc_p90',
                                               'dd_p50', 'dd_p95', 'p_dd15', 'ret_p05', 'lenh_cam')} for c in GRID},
        nam_theo_luoi={str(c): rows[c]['nam'] for c in GRID})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(ket, open(OUT, 'w'), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: ket[k] for k in ('chay_phut', 'tieu_chi', 'ket_luan')}, ensure_ascii=False))
    for t in tung:
        print(f"  {t['nam']}: PROD {t['prod']*100:+.1f}% · Cam0.45 {t['cam45']*100:+.1f}% · lệnh Cam {t['lenh_cam']}")
    for w in wf:
        print(f"  WF {w['nam']}: chọn {w['chon']} → {w['ret_chon']*100:+.1f}% (PROD {w['ret_prod']*100:+.1f}%)")


if __name__ == '__main__':
    main()
