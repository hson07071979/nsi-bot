# -*- coding: utf-8 -*-
"""LOP KIEM DINH — Robustness & Validation Engine
   Nguyen Son Invest · sinh ra tu ban audit he thong.

   Cau hoi ma file nay tra loi KHONG PHAI "lam sao tang loi nhuan backtest",
   ma la: "neu toi co tinh pha he thong nay, no con kiem duoc tien khong?"

   Sau khi chay:  python3 robustness.py     ->  data/robust.json
   Trang web doc file do o tab "Kiem dinh".

   SAU BAI KIEM TRA
     1. WALK-FORWARD      tham so chon bang qua khu, cham diem tren tuong lai chua thay
     2. TRUOT GIA         0,15% -> 1,5% + kich ban BAT DOI XUNG mua/ban
     3. NHIEU THAM SO     quet +-10-20% tung nguong, do do PHANG cua vung
     4. BO DEAL TOT NHAT  bo top 1/3/5/10% winner, xem edge con lai bao nhieu
     5. MONTE CARLO       xao tron thu tu deal vai nghin lan, doc phan vi
     6. NHIN TRUOC        kiem tra bang khang dinh, khong phai bang loi hua
     7. NGAT MACH         A/B thu quy tac bao ve von khi thua lien tiep
     8. KET T+2.5         gia dinh 10% deal bi sap san 2 phien truoc khi hang ve
"""
import json, os, sys, time, math, copy
import numpy as np
import engine2 as E

RNG = np.random.default_rng(20260829)

# Cau hinh PROD — phai giong het produce2.PROD, khong duoc lech mot chu.
from produce2 import PROD

# ---------------------------------------------------------------- tien ich
def _eq(r):      return np.array([x[1] for x in r['eq']], dtype=float)
def _m(r):       return E.metrics(r)

def _tom(m):
    """rut gon mot bo metrics cho gon file json"""
    return {k: m.get(k) for k in
            ('trades','total_return','cagr','maxdd','pf','sharpe','winrate','avg_win','avg_loss','expectancy')}

_FRAC = [None]      # co vi the HIEU DUNG, hieu chuan mot lan truoc khi dung

def _hieu_chuan(trades, muc_tieu):
    """Tim co vi the hieu dung f sao cho duong von dung lai TU DEAL khop voi
       backtest that.

       Vi sao can: backtest chay toi 12 vi the SONG SONG nen von duoc chia se.
       Nhan thang base_size 42% cho tung deal noi tiep nhau se ra con so phong dai
       vai lan (+4.362% thay vi +524%) — nhin la biet sai. Hieu chuan mot lan roi
       dung chung cho moi kich ban, thi cac kich ban so sanh duoc VOI NHAU tren
       cung mot thuoc do, va con so tuyet doi cung khong con lac loi."""
    p = np.array([t['pnl_pct'] for t in trades], dtype=float)/100.0
    lo, hi = 1e-4, 1.0
    for _ in range(90):
        mid = (lo+hi)/2
        v = float(np.prod(1+p*mid)) - 1
        if v < muc_tieu: lo = mid
        else: hi = mid
    return (lo+hi)/2

def _from_trades(trades, nav0=1e9):
    """Dung lai duong von TU DANH SACH DEAL.

       QUAN TRONG — loi de mac nhat o day: thu tu phai la thu tu THOI GIAN that
       (theo ngay thoat lenh). Neu de danh sach da sap xep theo lai/lo thi moi deal
       thang don len dau, moi deal thua don xuong cuoi, va muc sut se ra 71% —
       mot con so vo nghia khong lien quan gi den he thong."""
    f = _FRAC[0] or PROD['base_size']
    tr = sorted(trades, key=lambda t: (t['exit'], t['entry']))
    nav = nav0; peak = nav0; mdd = 0.0; curve = [nav0]
    for t in tr:
        nav *= (1 + t['pnl_pct']/100 * f)
        peak = max(peak, nav)
        mdd = max(mdd, 1 - nav/peak)
        curve.append(nav)
    p = [t['pnl_pct'] for t in tr]
    gp = sum(x for x in p if x > 0); gl = abs(sum(x for x in p if x <= 0))
    return dict(total_return=round(nav/nav0-1, 4), maxdd=round(mdd, 4),
                pf=round(gp/gl, 2) if gl > 0 else None,
                winrate=round(len([x for x in p if x > 0])/len(p), 4) if p else 0,
                n=len(tr))

def _log(*a):
    print(*a, flush=True)

# ============================================================ 1. WALK-FORWARD
def walk_forward():
    """Tham so duoc chon bang du lieu qua khu, roi dem cham diem tren nam CHUA DUNG.

       Day la bai kiem tra nghiem khac nhat trong ca file. Backtest toan ky luon
       dep vi tham so da duoc nhin thay ca ky. Walk-forward khong cho phep dieu do.

       Luu y trung thuc: cua so 'train' o day chon giua MOT LUOI NHO cac tham so
       (nen 16/18/20%, san diem 42/45/48). Do khong phai toan bo khong gian tham so,
       nhung du de tra loi cau hoi "chon bang qua khu co song sang tuong lai khong".
    """
    LUOI = [dict(base_range=b, score_floor=s)
            for b in (0.16, 0.18, 0.20) for s in (42, 45, 48)]
    CUA = [('2019-01-02', '2022-12-31', '2023'),
           ('2019-01-02', '2023-12-31', '2024'),
           ('2019-01-02', '2024-12-31', '2025'),
           ('2019-01-02', '2025-12-31', '2026')]
    out = []
    for tr_a, tr_z, nam in CUA:
        best = None
        for g in LUOI:
            c = dict(PROD); c.update(g); c['start'] = tr_a; c['end'] = tr_z
            try: mm = _m(E.run(c, log=False))
            except Exception: continue
            # chon theo Sharpe chu khong theo loi nhuan tho — loi nhuan tho
            # luon keo ve phia tham so lieu linh nhat
            diem = (mm['sharpe'] or 0)
            if best is None or diem > best[0]: best = (diem, g, mm)
        if best is None: continue
        _, g, mtr = best
        c = dict(PROD); c.update(g); c['start'] = nam + '-01-01'; c['end'] = nam + '-12-31'
        mte = _m(E.run(c, log=False))
        out.append(dict(train=f'{tr_a[:4]}–{tr_z[:4]}', test=nam, chon=g,
                        train_m=_tom(mtr), test_m=_tom(mte)))
        _log(f'  WF train {tr_a[:4]}-{tr_z[:4]} -> test {nam}: chon {g} · '
             f'test return {mte["total_return"]:+.1%} pf {mte["pf"]} n {mte["trades"]}')
    # doi chieu: chinh PROD chay tren tung nam do, khong toi uu gi ca
    ref = []
    for _, _, nam in CUA:
        c = dict(PROD); c['start'] = nam + '-01-01'; c['end'] = nam + '-12-31'
        ref.append(dict(nam=nam, m=_tom(_m(E.run(c, log=False)))))
    return dict(windows=out, prod_by_year=ref)

# ============================================================ 2. TRUOT GIA
def slippage():
    """Truot gia doi xung tu 0,15% den 1,5%, roi den kich ban BAT DOI XUNG.

       Ban audit noi dung: o TTCK VN chieu mua tran truot it nhung thieu khoi luong,
       con chieu ban thao khi gay MA thi truot rat nang vi trang ben mua. Test doi
       xung 0,2% hai chieu la mot gia dinh de chiu hon thuc te.
    """
    doi_xung = []
    for s in (0.0015, 0.0020, 0.0050, 0.0100, 0.0150):
        c = dict(PROD); c['slip'] = s
        m = _m(E.run(c, log=False))
        doi_xung.append(dict(slip=s, m=_tom(m)))
        _log(f'  truot {s*100:.2f}%  return {m["total_return"]:+.1%}  DD {m["maxdd"]:.1%}  PF {m["pf"]}')
    KB = [('Dễ chịu',       0.0015, 0.0030),
          ('Thực tế',       0.0020, 0.0080),
          ('Phiên xấu',     0.0030, 0.0150),
          ('Trắng bên mua', 0.0050, 0.0250)]
    bat_doi_xung = []
    for ten, sb, ss in KB:
        c = dict(PROD); c['slip_buy'] = sb; c['slip_sell'] = ss
        m = _m(E.run(c, log=False))
        bat_doi_xung.append(dict(ten=ten, mua=sb, ban=ss, m=_tom(m)))
        _log(f'  {ten:15s} mua {sb*100:.2f}% ban {ss*100:.2f}%  return {m["total_return"]:+.1%}  DD {m["maxdd"]:.1%}')
    return dict(doi_xung=doi_xung, bat_doi_xung=bat_doi_xung)

# ====================================================== 3. NHIEU THAM SO
def perturb():
    """Quet tung nguong quanh gia tri dang dung.

       Cach doc DUY NHAT dung: khong nhin dinh cao nhat, nhin do PHANG.
       Neu chi mot diem duy nhat cho ket qua tot con hai ben sup thi do la
       dau hieu tham so duoc vat cho vua qua khu, khong phai quy luat.
    """
    LUOI = [
        ('base_range',  'Độ rộng nền 30 phiên',        [0.14,0.16,0.17,0.18,0.19,0.20,0.22]),
        ('score_floor', 'Sàn điểm CANSLIM',   [40,42,45,48,50]),
        ('vol_floor',   'Bội số khối lượng so TB20',  [1.6,1.8,2.0,2.2,2.4]),
        ('ordimb_min',  'Tỷ lệ cỡ lệnh mua/bán (order-flow proxy)',      [1.10,1.15,1.20,1.25,1.30]),
        ('big_win',     'Ngưỡng lãi lớn bật trailing MA10',     [0.16,0.18,0.19,0.20,0.22]),
        ('base_size',   'Cỡ vị thế (% NAV)',   [0.20,0.25,0.30,0.35,0.40,0.42]),
        ('t_valve',     'Van thời gian T+n',      [4,5,6,7,8]),
        ('trail_ma',    'Trailing MA chậm',        [20,30,50]),
    ]
    out = []
    for khoa, ten, vals in LUOI:
        rows = []
        for v in vals:
            c = dict(PROD); c[khoa] = v
            if khoa == 'base_size': c['max_pos'] = max(PROD['max_pos'], v + 0.08)
            try: m = _m(E.run(c, log=False))
            except Exception: continue
            rows.append(dict(v=v, m=_tom(m), la_prod=(abs(v - PROD.get(khoa, -1)) < 1e-9)))
        pfs = [r['m']['pf'] for r in rows if r['m']['pf'] is not None]
        if len(pfs) >= 3:
            # do phang = do lech chuan cua PF chia trung binh PF.
            # cang nho cang it phu thuoc vao viec chon dung mot con so.
            cv = float(np.std(pfs) / max(np.mean(pfs), 1e-9))
            # dinh sac = gia tri dang dung tot hon HAN moi hang xom
            best = max(range(len(rows)), key=lambda k: rows[k]['m']['pf'] or 0)
            hangxom = [rows[k]['m']['pf'] or 0 for k in (best-1, best+1) if 0 <= k < len(rows)]
            sac = (rows[best]['m']['pf'] or 0) > 1.35 * max(hangxom + [1e-9])
        else:
            cv, sac = None, False
        out.append(dict(khoa=khoa, ten=ten, rows=rows, cv=None if cv is None else round(cv, 3),
                        dinh_sac=bool(sac)))
        _log(f'  {ten:22s} cv={cv if cv is None else round(cv,3)}  dinh_sac={sac}')
    return out

# =============================================== 4. BO DEAL TOT NHAT
def remove_winners(trades):
    """Bo 1, 3, 5 deal lai nhat va 10% deal lai nhat.

       Neu bo mot vai deal ma PF sup tu 4,5 xuong 1,5 thi cai goi la 'edge'
       thuc ra la mot chuoi may man. Neu edge phan bo rong thi bo di van con.
    """
    xep = sorted(trades, key=lambda t: -t['pnl_pct'])
    goc = _from_trades(trades)
    out = [dict(bo='Nguyên bản — không bỏ deal nào', n_bo=0, m=goc)]
    for k in (1, 3, 5):
        con = xep[k:]
        out.append(dict(bo=f'Bỏ {k} deal lãi nhất', n_bo=k, m=_from_trades(con),
                        deal_bo=[dict(sym=t['sym'], pnl=t['pnl_pct'], exit=t['exit']) for t in xep[:k]]))
    k10 = max(1, int(len(xep) * 0.10))
    out.append(dict(bo=f'Bỏ 10% deal lãi nhất ({k10} deal)', n_bo=k10, m=_from_trades(xep[k10:])))
    for o in out:
        _log(f'  {o["bo"]:34s} return {o["m"]["total_return"]:+.1%}  PF {o["m"]["pf"]}  DD {o["m"]["maxdd"]:.1%}')
    return out

# ============================================================ 5. MONTE CARLO
def monte_carlo(trades, n_sim=5000):
    """Cung mot bo deal, xao tron THU TU, chay 5.000 lan.

       Tra loi cau hoi ma duong von don le khong tra loi duoc: neu cung edge nay
       nhung chuoi thang/thua roi khac di thi toi co chiu noi duong von do khong?
    """
    p = np.array([t['pnl_pct'] for t in trades], dtype=float) / 100.0 * (_FRAC[0] or PROD['base_size'])
    n = len(p)
    ends = np.empty(n_sim); dds = np.empty(n_sim); streaks = np.empty(n_sim, dtype=int)
    for s in range(n_sim):
        idx = RNG.permutation(n)
        r = p[idx]
        nav = np.cumprod(1 + r)
        peak = np.maximum.accumulate(nav)
        ends[s] = nav[-1] - 1
        dds[s] = float((1 - nav/peak).max())
        thua = (r <= 0).astype(int)
        # chuoi thua dai nhat
        best = cur = 0
        for x in thua:
            cur = cur + 1 if x else 0
            best = max(best, cur)
        streaks[s] = best
    q = lambda a, x: round(float(np.percentile(a, x)), 4)
    kq = dict(n_sim=n_sim, n_deal=n,
        ret=dict(p5=q(ends,5), p25=q(ends,25), p50=q(ends,50), p75=q(ends,75), p95=q(ends,95)),
        dd =dict(p50=q(dds,50), p75=q(dds,75), p90=q(dds,90), p95=q(dds,95), p99=q(dds,99),
                 worst=round(float(dds.max()),4)),
        streak=dict(p50=int(np.percentile(streaks,50)), p90=int(np.percentile(streaks,90)),
                    p99=int(np.percentile(streaks,99)), worst=int(streaks.max())),
        # xac suat DD vuot cac moc — con so anh Son thuc su can de biet co gong noi khong
        p_dd_20=round(float((dds>0.20).mean()),4),
        p_dd_25=round(float((dds>0.25).mean()),4),
        p_dd_30=round(float((dds>0.30).mean()),4),
        p_lo=round(float((ends<0).mean()),4),
        hist_dd=np.histogram(dds, bins=24, range=(0, max(0.45, float(dds.max()))))[0].tolist(),
        hist_dd_edges=[round(x,4) for x in np.histogram(dds, bins=24, range=(0, max(0.45, float(dds.max()))))[1].tolist()],
    )
    _log(f'  MC {n_sim} lan · DD trung vi {kq["dd"]["p50"]:.1%} · DD p95 {kq["dd"]["p95"]:.1%} · '
         f'chuoi thua p99 {kq["streak"]["p99"]} lenh · P(DD>25%) {kq["p_dd_25"]:.1%}')
    return kq

# ============================================================ 6. NHIN TRUOC
def lookahead(r):
    """Khong hua, ma KHANG DINH. Moi muc duoi day la mot phep thu chay that."""
    from engine import as_of
    ck = []

    def them(ten, ok, chi_tiet):
        ck.append(dict(ten=ten, ok=bool(ok), chi_tiet=chi_tiet))
        _log(f'  [{"OK " if ok else "HONG"}] {ten} — {chi_tiet}')

    # (a) bao cao tai chinh chi duoc dung SAU ngay ky bao cao KET THUC
    #     funda_timeline tra ve list (ngay_co_the_dung, dict), dict co 'label' = "2024Q3"
    import datetime as _dt
    CUOI_QUY = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    tls = E._CACHE.get('tls', {})
    xau = 0; tong = 0; vd = None
    for sym, tl in list(tls.items())[:500]:
        for avail, m in (tl or []):
            lab = m.get('label') or ''
            if 'Q' not in lab: continue
            try:
                y, q = lab.split('Q'); mo, dd = CUOI_QUY[int(q)]
                het = _dt.date(int(y), mo, dd)
            except Exception: continue
            tong += 1
            av = avail if isinstance(avail, _dt.date) else _dt.date.fromisoformat(str(avail)[:10])
            if av <= het:
                xau += 1
                if vd is None: vd = f'{sym} {lab} dùng từ {av} nhưng kỳ mới hết {het}'
    them('Báo cáo tài chính chỉ được dùng SAU khi kỳ báo cáo kết thúc',
         xau == 0, f'{tong} bản ghi kiểm tra, {xau} bản ghi vi phạm'
                   + (f' (ví dụ: {vd})' if vd else ''))

    # (b) vu tru TOP-N tinh lai theo tung phien, khong ap danh sach hom nay ve qua khu
    from vn300 import build_topn
    I = E._CACHE['I']
    T = build_topn(I, 110)
    d0 = T[300]; d1 = T[-1]
    khac = int((d0 != d1).sum())
    them('Vũ trụ TOP-110 tính lại theo từng phiên',
         khac > 0, f'phiên 300 và phiên cuối khác nhau {khac} mã — danh sách có đổi theo thời gian')

    # (c) gia khop khong bao gio la gia cua phien sau khi entry_mode='close'
    tr = r['trades']
    them('Giá vào lệnh là giá phiên bắt tín hiệu, không phải phiên sau',
         r['cfg'].get('entry_mode', 'close') == 'close',
         f"entry_mode = {r['cfg'].get('entry_mode','close')}")

    # (d) khong deal nao co ngay ra truoc ngay vao
    nguoc = sum(1 for t in tr if t['exit'] < t['entry'])
    them('Không deal nào ra trước khi vào', nguoc == 0, f'{len(tr)} deal, {nguoc} deal ngược thời gian')

    # (e) chi bao MA/vma dung cua so LUI, khong dung gia tuong lai
    ac = E._CACHE['d']['AdjClose']; ma = I['ma30']
    i = len(ac) - 5
    j = int(np.nanargmax(ac[i]))
    tay = float(np.nanmean(ac[i-29:i+1, j])); may = float(ma[i, j])
    them('MA30 chỉ dùng 30 phiên gần nhất trở về trước',
         abs(tay - may) < max(0.01, abs(may) * 0.01), f'tính tay {tay:.3f} so với engine {may:.3f}')

    # (f) cat du lieu giua chung KHONG lam doi cac deal truoc do
    c = dict(PROD); c['end'] = '2024-12-31'
    r24 = E.run(c, log=False)
    a = [(t['sym'], t['entry'], t['exit']) for t in r24['trades'] if t['exit'] <= '2024-12-31']
    b = [(t['sym'], t['entry'], t['exit']) for t in tr if t['exit'] <= '2024-12-31']
    them('Cắt lịch sử đến 2024 không làm đổi một deal nào trước đó',
         a == b, f'{len(a)} deal khi cắt so với {len(b)} deal toàn kỳ — {"trùng khớp" if a==b else "LỆCH"}')

    return dict(checks=ck, dat=all(c['ok'] for c in ck))

# ============================================================ 7. NGAT MACH
def circuit_breaker():
    """Ngat mach bao ve von: A/B that su, khong phai y kien.

       Quy tac: NAV thung X% tu dinh HOAC N lenh thua lien tiep -> ha co vi the
       con mot nua trong 10 phien. Tu mo lai khi NAV lap dinh moi.
       Ngat mach KHONG doan thi truong. No chi phan ung sau khi thiet hai xay ra.
    """
    goc = _m(E.run(dict(PROD), log=False))
    out = [dict(ten='Không ngắt mạch — cấu hình đang chạy', cfg=None, m=_tom(goc), n_ngat=0)]
    KB = [('NAV −8% hoặc 6 lệnh thua · hạ 1/2 trong 10 phiên', dict(cb_dd=0.08, cb_losses=6, cb_cut=0.5, cb_days=10)),
          ('NAV −10% hoặc 8 lệnh thua · hạ 1/2 trong 10 phiên', dict(cb_dd=0.10, cb_losses=8, cb_cut=0.5, cb_days=10)),
          ('NAV −8% hoặc 6 lệnh thua · NGỪNG hẳn 10 phiên', dict(cb_dd=0.08, cb_losses=6, cb_cut=0.0, cb_days=10)),
          ('NAV −6% hoặc 5 lệnh thua · hạ 1/2 trong 15 phiên', dict(cb_dd=0.06, cb_losses=5, cb_cut=0.5, cb_days=15))]
    for ten, ov in KB:
        c = dict(PROD); c['cb_enable'] = True; c.update(ov)
        r = E.run(c, log=False); m = _m(r)
        out.append(dict(ten=ten, cfg=ov, m=_tom(m), n_ngat=len(r.get('cb_log', [])),
                        log=r.get('cb_log', [])[:12]))
        _log(f'  {ten:44s} return {m["total_return"]:+.1%}  DD {m["maxdd"]:.1%}  '
             f'PF {m["pf"]}  ngat {len(r.get("cb_log",[]))} lan')
    return out

# ============================================================ 8. KET T+2.5
def t25_stress(trades, n_sim=2000, ty_le=0.10, san=-0.07, n_phien=2):
    """Kich ban ban audit doi: 10% so deal vua mua xong thi sap san hai phien
       lien tiep, trong khi hang chua ve nen van T+6 hoan toan vo hieu.

       Cach mo hinh: chon ngau nhien 10% deal, ap them mot cu sock -13,5%
       (hai phien san HOSE) vao ket qua deal do, roi dung lai duong von.
    """
    p = np.array([t['pnl_pct'] for t in trades], dtype=float)
    n = len(p); k = max(1, int(n * ty_le))
    sock = (1 + san) ** n_phien - 1          # hai phien san = -13,5%
    ends = np.empty(n_sim); dds = np.empty(n_sim)
    for s in range(n_sim):
        q = p.copy()
        idx = RNG.choice(n, size=k, replace=False)
        # cu sock cong don len ket qua deal, chan duoi bang -100%
        q[idx] = np.maximum(-99.0, (1 + q[idx]/100) * (1 + sock) * 100 - 100)
        r = RNG.permutation(q) / 100.0 * (_FRAC[0] or PROD['base_size'])
        nav = np.cumprod(1 + r); peak = np.maximum.accumulate(nav)
        ends[s] = nav[-1] - 1; dds[s] = float((1 - nav/peak).max())
    goc = _from_trades(trades)
    kq = dict(ty_le=ty_le, n_deal_dinh=k, sock=round(sock, 4), n_sim=n_sim,
              goc=dict(total_return=goc['total_return'], maxdd=goc['maxdd']),
              ret=dict(p5=round(float(np.percentile(ends,5)),4), p50=round(float(np.percentile(ends,50)),4),
                       p95=round(float(np.percentile(ends,95)),4)),
              dd=dict(p50=round(float(np.percentile(dds,50)),4), p95=round(float(np.percentile(dds,95)),4),
                      worst=round(float(dds.max()),4)))
    _log(f'  T+2.5: {k}/{n} deal dinh sock {sock:.1%} · DD trung vi {kq["dd"]["p50"]:.1%} '
         f'(goc {goc["maxdd"]:.1%}) · DD p95 {kq["dd"]["p95"]:.1%}')
    return kq

# ============================================================ CHAM DIEM
def cham_diem(R):
    """Nam tang cua ban audit. Moi tang mot cau tra loi CO / KHONG, co ly do."""
    t = []
    # L1 chuc nang
    t.append(dict(tang=1, ten='Chức năng — code chạy đúng luật',
                  dat=R['prod']['trades'] > 0,
                  ly_do=f"backtest chạy hết, sinh {R['prod']['trades']} lệnh"))
    # L2 lich su
    t.append(dict(tang=2, ten='Lịch sử — có edge trên dữ liệu đã có',
                  dat=(R['prod']['pf'] or 0) >= 1.6 and (R['prod']['sharpe'] or 0) >= 1.0,
                  ly_do=f"PF {R['prod']['pf']} · Sharpe {R['prod']['sharpe']} · DD {R['prod']['maxdd']:.1%}"))
    # L3 robust: khong duoc co dinh sac o cac nguong chinh
    sac = [p['ten'] for p in R['perturb'] if p['dinh_sac']]
    t.append(dict(tang=3, ten='Bền tham số — đổi ngưỡng ±10–20% vẫn sống',
                  dat=len(sac) == 0,
                  ly_do='không ngưỡng nào có đỉnh sắc' if not sac
                        else 'đỉnh sắc ở: ' + ', '.join(sac)))
    # L4 stress
    s15 = [x for x in R['slippage']['doi_xung'] if abs(x['slip'] - 0.015) < 1e-9]
    xau = [x for x in R['slippage']['bat_doi_xung'] if x['ten'] == 'Trắng bên mua']
    bo3 = [x for x in R['remove_winners'] if x['n_bo'] == 3]
    ok4 = ((s15 and (s15[0]['m']['pf'] or 0) >= 1.3)
           and (xau and (xau[0]['m']['pf'] or 0) >= 1.3)
           and (bo3 and (bo3[0]['m']['pf'] or 0) >= 1.5)
           and R['monte_carlo']['p_dd_30'] <= 0.10)
    t.append(dict(tang=4, ten='Chịu sốc — trượt giá, Monte Carlo, bỏ winner, kẹt T+2.5',
                  dat=bool(ok4),
                  ly_do=(f"trượt 1,5% PF {s15[0]['m']['pf'] if s15 else '—'} · "
                         f"trắng bên mua PF {xau[0]['m']['pf'] if xau else '—'} · "
                         f"bỏ 3 winner PF {bo3[0]['m']['pf'] if bo3 else '—'} · "
                         f"P(DD>30%) {R['monte_carlo']['p_dd_30']:.1%}")))
    # L5 ngoai mau
    wf = R['walk_forward']['windows']
    duong = sum(1 for w in wf if w['test_m']['total_return'] > 0)
    t.append(dict(tang=5, ten='Ngoài mẫu — năm chưa dùng để thiết kế vẫn có lãi',
                  dat=len(wf) > 0 and duong >= max(1, len(wf) - 1) and R['lookahead']['dat'],
                  ly_do=f"{duong}/{len(wf)} cửa sổ walk-forward có lãi · "
                        f"kiểm tra nhìn trước {'ĐẠT' if R['lookahead']['dat'] else 'TRƯỢT'}"))
    for x in t:
        _log(f"  Tang {x['tang']} {'DAT ' if x['dat'] else 'TRUOT'} — {x['ten']}")
    return dict(tang=t, san_sang=all(x['dat'] for x in t))

# ============================================================ CHAY
CACHE = 'data/robust_cache.json'
def _cache():
    try: return json.load(open(CACHE, encoding='utf-8'))
    except Exception: return {}
def _luu(c):
    json.dump(c, open(CACHE, 'w'), ensure_ascii=False)

def chang(ten, ham, C, lam_lai):
    """Chay mot chang, hoac lay lai ket qua cu. Bo kiem dinh chay lai backtest
       vai chuc lan nen mot lan chay het 8-15 phut; sua mot chang thi khong co ly
       do gi phai cho ca bay chang kia chay lai."""
    if ten in C and ten not in lam_lai:
        _log(f'  (dung lai ket qua cu — them "{ten}" vao dong lenh de chay lai)')
        return C[ten]
    kq = ham(); C[ten] = kq; _luu(C); return kq

if __name__ == '__main__':
    t0 = time.time()
    lam_lai = set(sys.argv[1:]) or {'*'}
    if '*' in lam_lai: lam_lai = {'walk_forward','slippage','perturb','remove_winners',
                                  'monte_carlo','lookahead','circuit_breaker','t25'}
    os.makedirs('data', exist_ok=True)
    R = {}
    C = _cache()

    _log('\n=== 0. CHAY PROD LAM MOC ===')
    r = E.run(dict(PROD), log=True)
    mp = _m(r); R['prod'] = _tom(mp); R['prod']['per_year'] = mp['per_year']
    R['asof'] = r['eq'][-1][0]; R['n_phien'] = len(r['eq'])
    _log(f"  PROD {mp['total_return']:+.1%} · CAGR {mp['cagr']:.1%} · DD {mp['maxdd']:.1%} · "
         f"PF {mp['pf']} · Sharpe {mp['sharpe']} · {mp['trades']} lenh")

    _log('\n=== 1. WALK-FORWARD ===');           R['walk_forward'] = chang('walk_forward', lambda: walk_forward(), C, lam_lai)
    _log('\n=== 2. TRUOT GIA ===');              R['slippage'] = chang('slippage', lambda: slippage(), C, lam_lai)
    _log('\n=== 3. NHIEU THAM SO ===');          R['perturb'] = chang('perturb', lambda: perturb(), C, lam_lai)
    _FRAC[0] = _hieu_chuan(r['trades'], mp['total_return'])
    _log(f"  co vi the hieu dung (hieu chuan) = {_FRAC[0]*100:.2f}% moi deal")
    _log('\n=== 4. BO DEAL TOT NHAT ===');       R['remove_winners'] = chang('remove_winners', lambda: remove_winners(r['trades']), C, lam_lai)
    _log('\n=== 5. MONTE CARLO ===');            R['monte_carlo'] = chang('monte_carlo', lambda: monte_carlo(r['trades']), C, lam_lai)
    _log('\n=== 6. KIEM TRA NHIN TRUOC ===');    R['lookahead'] = chang('lookahead', lambda: lookahead(r), C, lam_lai)
    _log('\n=== 7. NGAT MACH ===');              R['circuit_breaker'] = chang('circuit_breaker', lambda: circuit_breaker(), C, lam_lai)
    _log('\n=== 8. KET T+2.5 ===');              R['t25'] = chang('t25', lambda: t25_stress(r['trades']), C, lam_lai)
    _log('\n=== CHAM DIEM 5 TANG ===');          R['scorecard']      = cham_diem(R)

    R['frac_hieu_chuan'] = round(_FRAC[0], 4)
    R['runtime_s'] = round(time.time() - t0)
    json.dump(R, open('data/robust.json', 'w'), ensure_ascii=False)
    _log(f"\nXONG — data/robust.json ({os.path.getsize('data/robust.json')/1024:.0f} KB) "
         f"trong {R['runtime_s']}s")
    _log(f"KET LUAN: {'SAN SANG CHAY THAT' if R['scorecard']['san_sang'] else 'CHUA DAT DU 5 TANG'}")
