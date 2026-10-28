# -*- coding: utf-8 -*-
import json, numpy as np, datetime as dt, copy
from collections import defaultdict, Counter
import engine2 as E

# ============================================================================
# DOI CAU HINH 21/09/2026 — ba nguong cung luc. Quet 110 cau hinh de chon.
#   base_range  0.18 -> 0.22   (noi nen gia)
#   top_n       110  -> 120    (noi vu tru)
#   ordimb_min  1.20 -> 1.40   (siet dong tien)
# Do duoc: +522,9% -> +688,0% · sut giam 11,34% -> 9,45% · PF 4,44 -> 5,87
#          Sharpe 1,78 -> 1,96 · ty le thang 37,1% -> 46,4% · deal 118 -> 115
# Co che: noi TOP + noi nen TAO THEM tin hieu (118 -> 151 deal) nhung lam loang
# chat luong (PF 4,44 -> 4,04); siet dong tien LOC LAI (151 -> 115) va keo PF
# len 5,87. Ba can gat bu nhau, bat rieng tung cai thi kem hon nhieu.
# Bon bai kiem da qua: (1) ca dai dong tien 1,28-1,48 deu tot hon, PF tang deu
# -> cao nguyen that, NHUNG 1,50 roi vuc (+462,5%) nen dung siet qua 1,45;
# (2) nen 22% la cot cao nhat o ca sau hang TOP 110/115/120/125/130/140, va
# TOP 120 la hang cao nhat o ca sau cot; (3) co truot gia 0,2% van +618,2% so
# +464,9%; (4) 6/8 nam tot hon, hai nam thua deu thua duoi 5 diem.
# KHONG noi TOP len 160-300: nhin tong thi dep (+768% o TOP 200) nhung toan bo
# phan hon nam o 2019-2022, con 2023-2026 THUA han ban cu (+84% so +132%), va
# PF roi deu tu 4,44 xuong 2,5. Do la con so cua song penny 2020-2021 da qua.
# ============================================================================
PROD=dict(base_range=0.24,   # 0.22 -> 0.24 ngay 25/09/2026 (R11, anh Son duyet)
          use_ftd=True, use_ordimb=True, ordimb_min=1.40, slip=0.0,
          size_map={'XANH':1.0,'VANG':0.6,'CAM':0.35,'DO':0.2},
          base_size=0.42, max_pos=0.50, max_total=1.0, max_pos_n=12,
          # S1 PROFIT LOCK thay "ve bo +1%" (anh Son duyet 26/09/2026, research R21 —
          # evidence/r21_exit_only.json, r21b/c/d): dinh lai (dong cua, da gom phi mua) >= 8%
          # -> san +2%; >= 12% -> san +5%. Kiem luc dong cua, ban ATC, tu T+3. Khong co nac
          # 15%/19%: MA10 (big_win 19%) van la cua ra cua lenh lon. Mot dinh nghia duy nhat:
          # exit_rules.py (engine2, portfolio.py, live_scan, trang web qua test node).
          # TOP110 + S1 tren du lieu 23/09: +945,7%, DD 11,74%, PF 3,12 (deal that 6,28), Sharpe 2,10.
          # 29/09 toi: da thu siet 8%->+4% / 10%->+5% / 12%->+6% (R32, du lieu 29/09, cung bat den Cam):
          # +916,2% so +976,5% cua S1, DD bang nhau 11,74%, Sharpe 2,08 so 2,12, lai TB lenh thang
          # 10,89% so 11,49%. San cao ban lenh thang trong nhip rung binh thuong -> mat lenh chay toi MA10.
          # 30/09/2026 (anh Son): S1 + nac 15%, SAN NAC 12% NANG +5% -> +6%. R33 Monte Carlo tung nam
          # (22 cau hinh khoa lai x 60 lan lo 10% lenh, moi thu khac nhu PROD, evidence r33_lock_years.json):
          # bang hoac hon S1+15->+8 o CA 8 NAM (hon 2024/2025/2026, khong thua nam nao), MC ca ky +848,3%
          # (+839,2%), p10 +611,4% (+604,6%), DD 11,74% nhu nhau. San 8% giu +2%: nang len +3/+4% mat
          # ~28 diem nam 2021 (song lon). Doi chieu moi toi: PRESET 's1_15' (12->+5) va 's1'.
          use_be=False, profit_lock=[[0.08, 0.02], [0.12, 0.06], [0.15, 0.08]],
          # Chi ha 1/3 khi den THUC SU XAU DI so voi luc mua. Mua duoi den Cam thi
          # da vao co 35% roi — ha tiep 1/3 cung vi den Cam la dem hai lan mot tin
          # hieu xau. Toan ky co 31/57 lan cat kieu do. A/B: +511,7% -> +540,5%,
          # co truot gia 0,2% thi +460,9% -> +492,4%; bo deal tot nhat ra van hon
          # (3.852 tr so 3.642 tr). Gia phai tra: DD 12,0% -> 12,7%.
          orange_cut_only_if_worse=True,
          # BO CUA THOAT DEN CAM (anh Son duyet 29/09/2026, research R31): khong con ha 1/3 khi den chuyen Cam.
          # Du lieu 25/09: +957,2% -> +938,2%, DD 11,74% -> 12,78%, PF 3,15 -> 3,12, Sharpe 2,11 -> 2,06.
          # BAT LAI cung dot siet khoa lai (anh Son 29/09 toi, R32): khoa lai chi bao ve lenh DA len >= 8%;
          # den Cam ha 1/3 bao ve lenh CHUA len toi do khi thi truong xau di — hai cua khong trung nhau.
          # R31 (co S1) cho thay bat den Cam tot hon o ca bon chi so.
          # BO HAN 30/09/2026 (anh Son): den thi truong TAM TINH khong chac co trong gio giao dich
          # (29-30/09 rong suot 09:00-14:45) -> khong the ha 1/3 trong phien ngoai doi -> backtest co
          # luat nay la so khong lam duoc. Tat trong bo may, so ghi tien (hoan tac lan ha 1/3 BVH
          # 28/09), chuong, trang. Doi chieu moi toi: PRESET 'co_cam' (bat lai de xem mat bao nhieu).
          use_orange_cut=False,
          # VAN THOI GIAN T+4 (doi tu T+6 ngay 30/08/2026).
          # Quet lai tren vu tru 1.213 ma: T+4 thang T+6 o CA BON chi so cung luc —
          # +523,1% so +513,3% · DD 11,34% so 12,43% · PF 4,43 so 4,04 · Sharpe 1,78
          # so 1,71. Va T+4/T+5 gan nhu trung nhau nen day la VUNG PHANG that, khong
          # phai dinh nhon. Walk-forward dong bang cap 18%/T+4: thang 5/8 nam.
          t_valve=4, trail_ma=30, score_floor=45,
          # CHI GIAO DICH TOP 120 MA THANH KHOAN NHAT, xep hang lai theo TUNG PHIEN.
          # Khong dung danh sach VN30/VN100 cua hom nay ap nguoc lai qua khu (nhin truoc).
          # 110 -> 120 ngay 21/09/2026. Dung o 120: tu 160 tro len PF sup (3,08)
          # va 2023-2026 thua han ban cu.
          # 120 -> 105 ngay 26/09/2026 (R17, anh Son chon): voi mua do + ban T+3, TOP 105 cho
          # lai +936% (120: +906%), PF 3,17 (lenh that 6,57), tru truot 0,2/0,8 van +500%.
          # TOP 125-130 DD vuot 15% -> khong dung.
          # 105 -> 110 ngay 26/09/2026 (anh Son duyet, R21 B0/B1): 100-120 la vung phang
          # (TOP110 +920,1% / DD 12,28% so TOP105 +935,5% / 12,01% voi luat thoat cu); TOP110
          # la nen cua vong nghien cuu cua ra S1 va duoc duyet cung S1.
          use_top_liquid=True, top_n=110,
          # Nguong "lai lon" bat trailing MA10 de chot nhanh. 19% nam giua vung phang
          # 18-22% va cho DD thap nhat toan luoi (9,9%). Tu 24% tro len DD nhay len 13%.
          big_win=0.19,
          # ---- AUDIT 23/09/2026 (evidence/audit_r1_fixes.json) ----
          # Pyramid: GIU NGUYEN hanh vi goc theo quyet dinh cua anh Son (24/09).
          # Tran nganh 30% chi ap cho LENH MOI; lenh nhoi them chi xet tran moi ma
          # 50% va tien mat. (Bat pyr_caps=True thi lenh nhoi ton trong ca tran nganh
          # va tran tong von: +696,8% -> +579,1% — co trong evidence, KHONG dung.)
          pyr_caps=False, sector_cap=0.30,
          # max_pos_n re-checked for every same-session entry (never bound in history,
          # identical result — pure correctness guard).
          max_n_in_loop=True,
          # Condition 8 (close in upper half of the candle) removed: A/B identical to
          # the trade (0 trades removed, with and without slippage), and it only adds
          # an intraday timing ambiguity to the live layer.
          use_cond8=False,
          # ---- TOI UU 25/09/2026 (R11/R13, evidence/r11_progress.json, r13_joint.json,
          # r13_verify_final.json). Moi thay doi qua: Monte Carlo lo 10% lenh (200 lan),
          # hai o lan can, DD thuc <= 12%, nua 2023-26 khong kem hon, bo 3 deal lon nhat
          # them vao van hon ban cu. Anh Son duyet ngay 25/09.
          # DK1: HOSE 5,8% -> 5,6% (phai trung fa_ind.THR_HOSE).
          trig_hose=0.056, trig_hnx=0.088,
          # DK5 (loai LNST YoY 0-25%): TAT. Giu vung 0-25% lam giam loi nhuan o moi nac.
          dk5_lo=0.0, dk5_hi=0.0,
          # Momentum sau breakout: toi phien T+3 ma chua tung dong cua lai >= +1% (da tinh
          # phi mua) thi ban — "da break thi phai chay". Cat som -2,5% da thu: KEM hon.
          mo_by=3, mo_need=0.01,
          # MUA DO (anh Son chot 25/09, R14): DK9 chi co so SAU gio dong cua, nen lenh that
          # la: mua DU lenh luc ATC khi dat DK1-8 -> toi xac nhan DK9 -> truot thi ban ATC.
          stage1=1.0, probe_exit='close',
          # BAN SOM NHAT T+3 (anh Son 26/09: tai khoan cua anh chua ban duoc ATC T+2). Ap cho
          # MOI lenh ban (ke ca hard stop, lenh do truot DK9). +906,2%, DD 11,97%, PF 2,78.
          sell_from=3, hs_from=3,
          # TOI DA 1 LENH DO TREO (anh Son duyet 03/10/2026, research R31): dang co >= 1 lenh do
          # CHUA xac nhan DK9 (mua trong phien nay) hoac DA truot DK9 nhung chua toi T+3 de ban thi
          # KHONG mo lenh do moi. Khong doi co lenh do. Du lieu 02/10: +982,4% -> +1.057,9%,
          # DD 12,70% -> 11,85%, PF 3,08 -> 4,28, 297 -> 213 deal, 2026 +14,9% -> +35,7%.
          # MC lo 10% x 30: tv +868% -> +893%, DD p90 14,3% -> 12,8%, PF 3,07 -> 4,08.
          # Gia phai tra: mat PVT 27/02/2026 (+335 tr), GEE 11/04/2025 (+317 tr); mua mo cua T+1
          # +375% -> +172% (nhay voi gia khop). Mot dinh nghia: engine2 (stage 1/3), portfolio.py, live_scan.
          max_unconf=1, unconf_count='both',
          # THU TU UU TIEN KHI NHIEU MA CUNG NO (anh Son duyet 22/10/2026, research R38): xep theo
          # hang phan tram TRONG PHIEN cua diem CANSLIM + hang phan tram cua Vol/TB20 (0,5/0,5), hoa ->
          # ma. Ca hai deu thay duoc truoc ATC (khong dung OrdImb). Du lieu 21/10, 100 lan lo 10% lenh:
          # +1.045,5% -> +1.174,3%, DD 11,84% -> 10,72%, PF 4,33 -> 4,87; 2019-22 +271% -> +294%,
          # 2023-26 +209% -> +224%; MC p10/p50 +632/+920% -> +670/+993%; DD p95 bootstrap 20,1% -> 18,2%;
          # truot 0,2% +810% -> +882%; mo cua T+1 +168% -> +196%; thang 98,5% cach xep ngau nhien.
          # Luu y: walk-forward chon tren 2019-22 ra Vol/TB20 don, o 2023-26 chi bang PROD cu.
          # Mot dinh nghia: engine2.rank_rows; so ghi tien theo thu tu bo may (signals_today.uu_tien);
          # live_scan + trang dung allocator.xep_uu_tien (cung cong thuc).
          rank_mode='score_volr')
PRESETS={
 'thucte'  : ('Có trượt giá 0,2% (thực tế)', dict(slip=0.002)),
 'toanTT'  : ('Toàn thị trường (không giới hạn thanh khoản)', dict(use_top_liquid=False)),
 'top300'  : ('TOP 300 thanh khoản', dict(top_n=300)),
 'top100'  : ('TOP 100 thanh khoản — ít deal, PF cao', dict(top_n=100)),
 'top180'  : ('TOP 180 thanh khoản — nhiều deal hơn', dict(top_n=180)),
 'bw25'    : ('Ngưỡng lãi lớn 25% (bản cũ)', dict(big_win=0.25)),
 'cu'      : ('Cấu hình CŨ trước 21/09 — TOP 110, nền 18%, dòng tiền 1,20',
              dict(top_n=110, base_range=0.18, ordimb_min=1.20)),
 'dt120'   : ('Dòng tiền 1,20 (nới) — nhiều deal hơn, PF thấp hơn', dict(ordimb_min=1.20)),
 'dt145'   : ('Dòng tiền 1,45 (siết) — ít deal nhất', dict(ordimb_min=1.45)),
 'nhieudeal': ('Nhiều deal hơn — nền 25%, dòng tiền 1,20', dict(base_range=0.25, ordimb_min=1.20)),
 'khoa'    : ('Nhiều deal nhất — nền 25%, size 25%, dòng tiền 1,20', dict(base_range=0.25,base_size=0.25,max_pos=0.33,max_pos_n=16,ordimb_min=1.20)),
 'benhat'  : ('Bền nhất — size 30%', dict(base_size=0.30,max_pos=0.38)),
 'tvalve6' : ('Van T+6 — cấu hình cũ trước 30/08', dict(t_valve=6)),
 # R32 (29/09/2026): tach rieng tung thay doi cua luat thoat de doc moi toi.
 'co_cam'         : ('Có luật Đèn Cam hạ 1/3 (đã bỏ 30/09 — chỉ để đối chiếu)', dict(use_orange_cut=True)),
 'khoa_moi'       : ('Khoá lãi siết 8%→+4%, 10%→+5%, 12%→+6% (thử 29/09)', dict(profit_lock=[[0.08, 0.04], [0.10, 0.05], [0.12, 0.06]])),
 'khoa_3'         : ('Khoá lãi 8%→+3%, 12%→+5%', dict(profit_lock=[[0.08, 0.03], [0.12, 0.05]])),
 's1'             : ('Khoá lãi S1 (8%→+2%, 12%→+5%, không nấc 15%)', dict(profit_lock=[[0.08, 0.02], [0.12, 0.05]])),
 's1_15'          : ('Khoá lãi 8%→+2%, 12%→+5%, 15%→+8% (PROD 30/09 sáng)', dict(profit_lock=[[0.08, 0.02], [0.12, 0.05], [0.15, 0.08]])),
 'thucte_cocam'   : ('Có Đèn Cam hạ 1/3, trượt giá 0,2% (đối chiếu)', dict(use_orange_cut=True, slip=0.002)),
 # R38 (22/10/2026): doi chieu moi toi thu tu uu tien cu va bien the nhieu volume hon.
 'uu_tien_diem'   : ('Ưu tiên theo điểm CANSLIM (PROD trước 22/10)', dict(rank_mode='score')),
 'uu_tien_w04'    : ('Ưu tiên 0,4×điểm + 0,6×Vol/TB20 (giữa vùng phẳng R38b)', dict(rank_mode='score_volr', rank_w=0.4)),
}
STRICT=dict(base_range=0.12, use_ftd=False, use_ordimb=False, t_valve=3, trail_ma=20, slip=0.002,
            use_be=False, size_map={'XANH':1.0,'VANG':0.5,'CAM':0.0,'DO':0.0},
            base_size=0.10,max_pos=0.20,max_total=0.60,max_pos_n=8)

def yearly(eq):
    d=defaultdict(list)
    for dd,nv,l,_ in eq: d[dd[:4]].append(float(nv))
    o={};p=None
    for y in sorted(d):
        s=p if p is not None else d[y][0]; o[y]=round(d[y][-1]/s-1,4); p=d[y][-1]
    return o

def pack(r,name):
    eq=r['eq']; tr=r['trades']; m=E.metrics(r)
    doors=Counter(t['reason'] for t in tr)
    dmed={k:round(float(np.median([t['pnl_pct'] for t in tr if t['reason']==k])),2) for k in doors}
    return dict(name=name, metrics={k:(float(v) if isinstance(v,(np.floating,)) else v) for k,v in m.items()},
        yearly=yearly(eq), lights=dict(Counter(e[2] for e in eq)),
        doors=[{'door':k,'n':v,'pct':round(v/len(tr)*100,1),'median':dmed[k]} for k,v in doors.most_common()],
        curve=[[e[0],round(float(e[1])/1e9,4),e[2]] for e in eq],
        trades=[dict({k:t.get(k) for k in ('sym','sector','entry','exit','entry_px','exit_px','entry_raw','exit_raw','pyr_date','pyr_raw','pyr_adj','held','pnl_pct','pnl_vnd','reason','light','peak','sh','frac')},
                     # nhan lenh Hard (28/10/2026) — chi co khoa khi lenh/vi the do anh Son bam tay
                     **{k:t[k] for k in ('hard','hard_id') if t.get(k)}) for t in tr])

if __name__=='__main__':
    out={}
    # LENH HARD cua anh Son (manual.json -> hard, 28/10/2026): chi lan chay CHINH nay co lenh tay.
    import hard as HD
    _hard, _hard_loi = HD.doc()
    for _e in _hard_loi: print('LENH HARD hong khuon:', _e, flush=True)
    r=E.run(dict(PROD, hard_orders=_hard), log=True); out['prod']=pack(r,'Nguyễn Sơn Bot v3 — FireAnt')
    _hk = r.get('hard') or {}
    out['hard'] = dict(
        # id da duoc ban dung xu ly (khop hoac tu choi) — trang khoa nut Hoan tac theo danh sach nay
        seen=[x['id'] for x in _hk.get('fills') or []],
        fills=_hk.get('fills') or [], pending=_hk.get('pending') or [], loi_khuon=_hard_loi,
        so_lenh=len(_hard))
    # Chi so cua RIENG luat bot (khong lenh tay) — lop kiem dinh (robustness) chay khong co lenh Hard,
    # nen verify_build so voi khoi nay. Khong co lenh Hard nao khop thi y het metrics.
    if any(_x.get('ok') for _x in out['hard']['fills']):
        out['prod']['metrics_bot'] = E.metrics(E.run(PROD, log=False))
    else:
        out['prod']['metrics_bot'] = out['prod']['metrics']
    for _x in out['hard']['fills']:
        print('LENH HARD', _x['phien'], _x['loai'].upper(), _x['sym'], _x['gia'], '->', 'KHOP' if _x['ok'] else 'TU CHOI', _x['ly_do'],
              ('%s cp' % _x.get('sh')) if _x.get('sh') else '', flush=True)
    for _x in out['hard']['pending']:
        print('LENH HARD CHO', _x['ngay'], _x['loai'].upper(), _x['sym'], '-', _x['ly_do'], flush=True)
    from dealstats import stats as _ds, deals as _dl
    out['prod']['deal_metrics']=_ds(r['trades'])
    out['prod']['deals']=_dl(r['trades'])
    print('PROD',out['prod']['metrics'],flush=True)
    cal=r['cal']; R=r['R']; i0=len(cal)-len(r['eq'])
    n=len(r['eq'])
    vni=R['vni'][i0:i0+n]; base=vni[0]
    out['bench']=[[out['prod']['curve'][k][0], round(float(vni[k]/base),4)] for k in range(n)]
    b=np.array([x[1] for x in out['bench']]); dd=1-b/np.maximum.accumulate(b); yrs=n/250
    out['bench_metrics']={'total':round(float(b[-1]-1),4),'cagr':round(float(b[-1]**(1/yrs)-1),4),'mdd':round(float(dd.max()),4)}
    out['bench_yearly']=(lambda:( {y:round(v,4) for y,v in (lambda dd_: ( {y:(dd_[y][-1]/ (dd_[list(sorted(dd_))[max(0,list(sorted(dd_)).index(y)-1)]][-1] if list(sorted(dd_)).index(y)>0 else dd_[y][0]) -1) for y in sorted(dd_)} ))((lambda: (lambda g: g)(  (lambda: ( {  } ))() ))() ).items()} ))() if False else None
    byy=defaultdict(list)
    for k in range(n): byy[out['bench'][k][0][:4]].append(float(b[k]))
    bo={};p=None
    for y in sorted(byy):
        s=p if p is not None else byy[y][0]; bo[y]=round(byy[y][-1]/s-1,4); p=byy[y][-1]
    out['bench_yearly']=bo
    out['regime']=[{'date':str(cal[i0+k]),'g1':round(float(R['g1'][i0+k]),1),
        'g1ma':(None if np.isnan(R['g1ma'][i0+k]) else round(float(R['g1ma'][i0+k]),1)),
        'vni':round(float(R['vni'][i0+k]),2),
        'vma50':(None if np.isnan(R['vma50'][i0+k]) else round(float(R['vma50'][i0+k]),1)),
        'dd':int(R['dcount'][i0+k]),'light':R['light'][i0+k],
        'br50':round(float(R['above50'][i0+k]),3),'ftd':bool(R['ftd'][i0+k])} for k in range(n)]
    out['signals']=r['signals']
    # ---- DEN TAM TINH TRONG PHIEN (28/09/2026): trang thai regime sau phien cuoi -> thresholds.json.
    # regime_live.step() la DUNG vong lap regime2; phat lai toan ky phai ra dung den cua bo may,
    # lech mot phien la KHONG xuat (chuong trong phien lui ve den hom truoc, nhu cu).
    try:
        import regime_live as _RLV, datetime as _dtm
        from regime2 import _ffill as _ff
        _V = json.load(open('data/VNINDEX.json'))
        _vm = {_dtm.datetime.utcfromtimestamp(t).date().isoformat(): v for t, v in zip(_V['t'], _V['v'])}
        _vv = _ff(np.array([_vm.get(str(x), np.nan) for x in cal], dtype=float))
        _g = R['g1']; _eq = np.r_[0.0, _g[1:] / _g[:-1] - 1]
        _C5 = dict(E.CFG); _C5.update(PROD)
        _L, _st = _RLV.replay(_eq, R['vni'], _vv, _C5)
        _lech = sum(1 for a_, b_ in zip(_L, R['light']) if a_ != b_)
        _dd = r['d']; _I = r['I']
        _val = (_dd['MarketCap'][-1] > 1000e9) & (_I['nbars'][-1] >= 250)
        out['regime_live'] = dict(ok=(_lech == 0), mismatch=_lech, state=_RLV.state_for_export(_st, str(cal[-1])),
                                  g1_syms=[str(x) for x in _dd['sym'][np.where(_val)[0]]],
                                  light=R['light'][-1])
        print('DEN TAM TINH: phat lai', len(_L), 'phien, lech', _lech, '· G1', len(out['regime_live']['g1_syms']), 'ma', flush=True)
    except Exception as _e:
        out['regime_live'] = dict(ok=False, error=f'{type(_e).__name__}: {_e}')
        print('DEN TAM TINH HONG:', _e, flush=True)
    _rg_light = out['regime'][-1]['light'] if out.get('regime') else 'XANH'
    def _lastpx(p):   # ma bi treo phien cuoi -> NaN khong duoc lot vao JSON; lui ve gia von
        v=float(r['d']['AdjClose'][-1,p.j]); return v if v==v else float(p.epx)
    import exit_rules as _ER
    _CF=dict(E.CFG); _CF.update(PROD)
    # DK9 cua PHIEN MUA (so toi ngay mua) + cac lan da ban mot phan (den Cam 1/3) — trang Danh muc
    _oi={(x['sym'],x['date']):x.get('ordimb') for x in r['signals']}
    _parts={}
    for t in r['trades']:
        _parts.setdefault((t['sym'],t['entry']),[]).append(dict(date=t['exit'],frac=t.get('frac'),sh=t.get('sh'),
                                                               reason=t['reason'],pnl_pct=t['pnl_pct'],pnl_vnd=t['pnl_vnd']))
    def _c9(p):
        oi=_oi.get((p.sym,str(cal[p.ei])))
        if oi is None or oi!=oi: return None, 'CHUA_CO'
        return round(float(oi),3), ('DAT' if oi>=PROD['ordimb_min'] else 'TRUOT')
    out['open_positions']=[{'sym':p.sym,
        'ordimb':_c9(p)[0],'cond9':_c9(p)[1],'ordimb_min':PROD['ordimb_min'],
        'sold_parts':_parts.get((p.sym,str(cal[p.ei])),[]),'entry':str(cal[p.ei]),'entry_px':round(float(p.epx),2),
        # gia THO da khop (de ve dau B dung nen) — entry_px o tren la gia von DIEU CHINH da gom phi
        'entry_raw':round(float(getattr(p,'eraw',float('nan'))),0),
        'shares':int(p.sh),'sector':p.sector,'last':round(_lastpx(p),2),
        'pnl':round(_lastpx(p)/float(p.epx)*100-100,2),
        # so phien da giu + dinh lai (da tinh phi mua) — trang dich luat thoat (momentum T+3,
        # van thoi gian, ve bo) thanh viec phai lam cho dung so he thong
        'held':int(len(cal)-1-p.ei),'peak':round(float(getattr(p,'peak',0.0))*100,2),
        # lenh do truot DK9 (stage 3) — se ban ATC phien sell_from (T+3)
        'probe_fail':bool(getattr(p,'stage',0)==3 or (getattr(p,'stage',0)==1 and not getattr(p,'oi_ok',True))),
        'b10':int(p.b10),'b20':int(p.b20),'part':bool(p.part),'light':R['light'][p.ei],
        # 'mua' = vi the mo bang Hard Buy, 'them' = Hard Buy them vao vi the bot (28/10/2026)
        'hard':getattr(p,'hard',None),
        # ty trong (ma, nganh, tong)/NAV luc vao va luc nhoi — chi ghi nhan (26/09/2026)
        'x0':getattr(p,'x0',None),'xp':getattr(p,'xp',None),
        # trang thai cua ra theo exit_rules (S1: peak_gain, profit_floor, sellable, action...)
        **_ER.status(_CF, _lastpx(p)/float(p.epx)-1, float(getattr(p,'peak',0.0)), int(len(cal)-1-p.ei),
                     probe_fail=bool(getattr(p,'stage',0)==3), b10=int(p.b10), b20=int(p.b20),
                     light_today=R['light'][len(cal)-1], light_entry=R['light'][p.ei], part=bool(p.part))} for p in r['pos'].values()]
    # TIN HIEU CUA CHINH PHIEN VUA CHOT — so ghi tien (portfolio.py, repo public) vao
    # so DUNG cac lenh nay, sau khi ban dung toi da lap du dong tien HNX. Mot nguon su
    # that: khong con chuyen live.json bao MUA nhung bo may khong mua (hoac nguoc lai).
    out['signals_today']=[dict(sym=x['sym'],date=x['date'],price=round(x['raw_px']),score=x['score'],
                               sector=x['sector'],light=x['light'],ordimb=x['ordimb'],rmul=x['rmul'],
                               base=x['base'],size_pct_engine=x['size_pct'],
                               cond9_ok=bool(x['ordimb'] is not None and x['ordimb']>=PROD['ordimb_min']), probe=PROD.get('stage1') is not None,
                               uu_tien=x.get('uu_tien'),n_ung_vien=x.get('n_ung_vien'),volr=x.get('volr'))
                          for x in r['signals'] if x['date']==str(cal[-1]) and x.get('mode','close')=='close']
    # 10 phien gan nhat: de so ghi tien XU LY BU dung thu tu neu lo mot dem dung trang
    _rec=[str(x) for x in cal[-30:]]
    out['light_by_date']={d_:R['light'][len(cal)-30+k] for k,d_ in enumerate(_rec)}
    out['signals_recent']=[dict(sym=x['sym'],date=x['date'],price=round(x['raw_px']),score=x['score'],
                                sector=x['sector'],light=x['light'],ordimb=x['ordimb'],rmul=x['rmul'],
                                base=x['base'],size_pct_engine=x['size_pct'],
                                cond9_ok=bool(x['ordimb'] is not None and x['ordimb']>=PROD['ordimb_min']), probe=PROD.get('stage1') is not None,
                                uu_tien=x.get('uu_tien'),n_ung_vien=x.get('n_ung_vien'),volr=x.get('volr'))
                           for x in r['signals'] if x['date'] in _rec and x.get('mode','close')=='close']
    out['blocked']={k:int(v) for k,v in r['blocked'].items()}
    # SO HE THONG (bo may) o phien cuoi: NAV HIEN TAI + tien mat + vi the. Chuong
    # Telegram va trang web tinh "vao bao nhieu % NAV / bao nhieu tien" tren CHINH
    # NAV nay (anh Son 24/09: 25% la 25% NAV hien tai, khong phai 25% cua 1 ty).
    out['book']={'book_id':'HE_THONG','asof':str(cal[-1]),'nav':round(float(r['nav'])),
                 'cash':round(float(r['cash'])),
                 # held + probe_fail: live_scan dem lenh do treo (luat max_unconf, 03/10/2026)
                 'positions':[{'sym':p.sym,'sector':p.sector,'shares':int(p.sh),
                               'held':int(len(cal)-1-p.ei),'hard':getattr(p,'hard',None),
                               'entry':str(cal[p.ei]),
                               # cac lan MUA THEM [phien, so co] (nhoi / Hard) — trang tinh phan chua ve tai khoan
                               'adds':[[str(cal[ia]),int(a)] for (ia,a) in (getattr(p,'adds',None) or [])],
                               'probe_fail':bool(getattr(p,'stage',0)==3 or (getattr(p,'stage',0)==1 and not getattr(p,'oi_ok',True))),
                               'value':round(float(r['d']['AdjClose'][-1,p.j] if r['d']['AdjClose'][-1,p.j]==r['d']['AdjClose'][-1,p.j] else p.epx)*int(p.sh))}
                              for p in r['pos'].values()]}
    # ---- KE HOACH BAN PHIEN TOI (03/10/2026, anh Son): moi ma dang cam, phien toi gia dong cua
    # bao nhieu thi BAN HET ATC. Dung exit_rules.decide (khong them luat). Gia thuc = gia dieu
    # chinh x fx (gia tho / gia dieu chinh cua phien cuoi). Trang web + chuong ntfy doc khoi nay.
    def _kh(sym, j, cost, peak, held_next, b10, b20, probe_fail, part):
        _AC = r['d']['AdjClose'][:, j]; _PX = r['d']['PriceClose'][:, j]
        _prev = [float(x) for x in _AC[-40:] if x == x]
        _fx = float(_PX[-1] / _AC[-1]) if (_AC[-1] == _AC[-1] and _PX[-1] == _PX[-1] and _AC[-1] > 0) else 1.0
        k = _ER.ke_hoach_ban(_CF, float(cost), float(peak), int(held_next), _prev, int(b10), int(b20),
                             probe_fail=bool(probe_fail), part=bool(part), fx=_fx)
        q = lambda v: (round(float(v) * _fx / 1000, 2) if v is not None else None)
        return dict(sym=sym, viec=k['viec'], ly_do=k['ly_do'], held=k['held'], sell_from=k['sell_from'],
                    nguong=(round(k['nguong_raw'] / 1000, 2) if k.get('nguong_raw') else q(k['nguong'])),
                    gia_von=q(cost), dong_cua=q(_AC[-1]), peak=round(float(peak) * 100, 2),
                    b10=k['b10'], b20=k['b20'], moc={kk: q(vv) for kk, vv in k['moc'].items()})
    _kh_he = {}
    for p in r['pos'].values():
        try:
            _kh_he[p.sym] = _kh(p.sym, p.j, p.epx, getattr(p, 'peak', 0.0), len(cal) - p.ei, p.b10, p.b20,
                                getattr(p, 'stage', 0) == 3 or (getattr(p, 'stage', 0) == 1 and not getattr(p, 'oi_ok', True)),
                                p.part)
        except Exception as e:
            print('ke hoach ban loi', p.sym, e, flush=True)
    for q_ in out['book']['positions']:
        if q_['sym'] in _kh_he: q_['ke_hoach'] = _kh_he[q_['sym']]
    for q_ in out['open_positions']:
        if q_['sym'] in _kh_he: q_['ke_hoach'] = _kh_he[q_['sym']]
    # So tay anh Son (manual.json da dang): vi the chua ban -> cung mot ham, trang thai dung lai
    # tu gia dong cua (dinh lai, so phien duoi MA10/MA30). Chi trang quan tri hien khoi nay.
    out['ke_hoach_so_tay'] = []
    try:
        _mn = json.load(open('data/manual.json', encoding='utf-8'))
        _S = [str(x) for x in r['d']['sym']]; _cal = [str(x) for x in cal]
        for t in (_mn.get('trades') or []):
            if t.get('sell_d') or not t.get('buy_d') or not t.get('buy_px') or t.get('sym') not in _S: continue
            j = _S.index(t['sym']); bi = next((k for k, c in enumerate(_cal) if c >= str(t['buy_d'])), None)
            if bi is None: continue
            _AC = r['d']['AdjClose'][:, j]; _PX = r['d']['PriceClose'][:, j]
            f0 = float(_AC[bi] / _PX[bi]) if (_PX[bi] == _PX[bi] and _PX[bi] > 0) else 1.0
            cost = float(t['buy_px']) * 1000 * f0 * (1 + float(PROD.get('fee_buy', E.CFG.get('fee_buy', 0.0015))))
            peak = 0.0; b10 = b20 = 0
            nf, ns = int(_CF.get('trail_fast') or 10), int(_CF.get('trail_ma') or 30)
            for i in range(bi + 1, len(cal)):
                c = _AC[i]
                if c != c: continue
                peak = max(peak, float(c) / cost - 1)
                w10 = _AC[max(0, i - nf + 1):i + 1]; w30 = _AC[max(0, i - ns + 1):i + 1]
                b10 = b10 + 1 if (len(w10) == nf and c < np.nanmean(w10)) else 0
                b20 = b20 + 1 if (len(w30) == ns and c < np.nanmean(w30)) else 0
            k = _kh(t['sym'], j, cost, peak, len(cal) - bi, b10, b20, False, False)
            k.update(buy_d=t['buy_d'], buy_px=t['buy_px'], sh=t.get('sh'))
            out['ke_hoach_so_tay'].append(k)
    except Exception as e:
        print('ke hoach so tay loi', e, flush=True)
    print('KE HOACH BAN', len(_kh_he), 'ma he thong,', len(out['ke_hoach_so_tay']), 'ma so tay', flush=True)
    out['universe_n']=int(len(r['d']['sym'])); out['asof']=str(cal[-1])
    # GIA CO SO CHO NUT HARD (28/10/2026): moi ma HOSE/HNX con giao dich o phien cuoi —
    # [tham chieu cua phien cuoi (PriceBasic), dong cua phien cuoi, san]. Trang tinh tran/san tu
    # chinh du lieu nay (tham chieu = PriceBasic neu lenh thuoc phien cuoi, = dong cua neu thuoc phien sau).
    _dd = r['d']; _PB = _dd['PriceBasic'][-1]; _PC = _dd['PriceClose'][-1]
    out['ma_gia'] = {str(_dd['sym'][k]): [round(float(_PB[k]) / 1000, 2) if _PB[k] == _PB[k] else None,
                                          round(float(_PC[k]) / 1000, 2), str(_dd['exch'][k])]
                     for k in range(len(_dd['sym'])) if _PC[k] == _PC[k] and _PC[k] > 0}
    # DO PHU CUA DONG TIEN MUA/BAN O PHIEN CUOI — canh bao im lang tung nuot ca ngay.
    # FireAnt tra BuyCount/SellCount TRE hon gia vai tieng. Neu cao truoc luc do thi
    # ca 694 ma deu thieu, dieu kien 7 truot het, va bo may KHONG MO DUOC LENH NAO
    # o phien moi nhat — nhin ben ngoai giong het "hom nay khong co tin hieu".
    _oi = r['I']['ordimb'][-1] if 'I' in r else None
    if _oi is not None:
        _song = ~np.isnan(r['d']['AdjClose'][-1])
        _co = int((~np.isnan(_oi) & _song).sum()); _tong = int(_song.sum())
        out['oi_cover'] = round(_co / max(_tong, 1), 3)
        print(f"DONG TIEN phien cuoi: {_co}/{_tong} ma co du lieu ({100*_co/max(_tong,1):.0f}%)", flush=True)
    # monthly 2026
    mm=defaultdict(lambda:[0,0.0])
    for t in r['trades']:
        if t['entry'][:4]=='2026': mm[t['entry'][:7]][0]+=1
        if t['exit'][:4]=='2026':  mm[t['exit'][:7]][1]+=t['pnl_vnd']
    lt=defaultdict(Counter)
    for k in range(n):
        if str(cal[i0+k])[:4]=='2026': lt[str(cal[i0+k])[:7]][R['light'][i0+k]]+=1
    out['m2026']=[{'m':k,'n':mm[k][0],'pnl':round(mm[k][1]/1e6,1),'lights':dict(lt[k])} for k in sorted(set(list(mm)+list(lt)))]
    # presets
    P={}
    for k,(lab,ov) in PRESETS.items():
        cfg=dict(PROD); cfg.update(ov)
        rr=E.run(cfg,log=False); mm2=E.metrics(rr)
        P[k]={'label':lab,'metrics':mm2,'deal_metrics':_ds(rr['trades']),'yearly':yearly(rr['eq']),
              'curve':[[e[0],round(float(e[1])/1e9,4)] for e in rr['eq']]}
        print(k,mm2,flush=True)
    out['presets']=P
    rs=E.run(STRICT,log=False); out['strict']={'name':'Nguyên bản tài liệu','metrics':E.metrics(rs),'yearly':yearly(rs['eq'])}
    print('STRICT',out['strict']['metrics'],flush=True)
    # Ket qua cac thi nghiem MOT LAN (khong chay lai hang ngay). Uu tien doc tu
    # thu muc evidence/ di kem ma nguon; neu khong co thi lay o data/ nhu truoc.
    import hashlib as _hl0
    _f0 = dict(E.CFG); _f0.update(PROD)
    _cur_hash = _hl0.sha256(json.dumps(_f0, sort_keys=True, default=str).encode()).hexdigest()[:12]
    sw={}
    for k,fn in [('s2','sweep2'),('s3','sweep3'),('opt','opt_dd'),('s4','sweep4'),('s5','sweep5'),
                 ('o2','opt2'),('o3','opt3'),('o4','opt4'),('o6','opt6'),('o7','opt7'),
                 ('fill','fill_compare'),('fill2','fill_test2'),('gate','gate_test'),('refine','refine')]:
        sw[k]={}
        for _p in (f'evidence/{fn}.json', f'data/{fn}.json'):
            try:
                sw[k]=json.load(open(_p)); break
            except Exception: pass
        if not sw[k]: print(f'  thieu bang chung: {fn}.json', flush=True)
        # EVIDENCE VERSIONING: only files stamped with TODAY's prod_config_hash are
        # current; everything else is archived research under another config.
        elif isinstance(sw[k], dict):
            _m = sw[k].get('meta') or {}
            sw[k]['_current'] = bool(_m.get('prod_config_hash')) and _m.get('prod_config_hash') == _cur_hash
            sw[k]['_label'] = 'CURRENT' if sw[k]['_current'] else 'ARCHIVED · OLD CONFIG · NOT CURRENT PROD'
    out['sweeps']=sw
    out['peer']={'khoa':{'name':'Khoa Nguyen Invest','total':4.628,'deals':237,'winrate':0.35,'rr':5.2,
                         'vni_1y':0.343,'vni_3y':0.636,'vni_2019':1.114,'url':'https://khoanguyeninvest.vn/'},
                 'anhung':{'name':'An Hưng — The Alchemy of Finance','url':'https://an-hung-finance.vercel.app/',
                           'signals':418,'winrate':0.28,'avg_win':0.161,'avg_loss':-0.027,'rr':6.0,'exp':0.0258}}
    try: out['screener']=json.load(open('data/screener.json'))
    except Exception: out['screener']={}
    try: out['watchlist']=json.load(open('data/watchlist.json'))
    except Exception: out['watchlist']={}
    for _p in ('data/alerts_live.json','data/alerts.json'):
        try:
            out['alerts']=json.load(open(_p)); break
        except Exception: out['alerts']={}
    # ---- ba khoi du lieu cho trang khach hang ----
    from extras import monthly, top6m, candles
    out['monthly'] = monthly(out['prod']['curve'], out['prod']['trades'])
    out['top6m']   = top6m(out['prod'].get('deals') or [], out['asof'], 6)
    _wl = [m['sym'] for m in (out.get('watchlist') or {}).get('members', [])]
    _sig = [x['sym'] for x in out['signals'][-40:]]
    _op  = [x['sym'] for x in out['open_positions']]
    _d6  = [x['sym'] for x in out['top6m']['deals']]
    # Nhung nen cho TOAN BO vu tru giao dich (TOP 120), khong chi vai chuc ma.
    # Trang Chi tiet ma phai xem duoc moi ma he thong co the mua ma khong cần cầu nối.
    # Ma ngoai vu tru thi lay qua cau noi real-time — nhung san ca 694 ma thi trang
    # phong len chuc MB, khong dang.
    from vn300 import build_topn as _tn0
    # LOI 21/09/2026: dong nay tung go cung 110 trong khi bo may da sang TOP 120.
    # Hau qua khong lam do build: ma xep hang 111-120 van duoc bo may giao dich
    # nhung KHONG co nen tren trang Chi tiet ma. Lay thang tu PROD.
    _uni = [str(x) for k, x in enumerate(r['d']['sym']) if _tn0(r['I'], int(PROD['top_n']))[-1][k]]
    _syms = list(dict.fromkeys(_op + _d6 + _wl + _sig + _uni))
    out['candles'] = candles(r['d'], r['I'], _syms, 240, out['prod']['trades'])
    from extras import trade_marks as _tm
    out['marks'] = _tm(r['d'], out['prod']['trades'])   # dau mua/ban cho moi lenh (03/10/2026)
    print('EXTRA candles', len(out['candles']), 'ma', flush=True)
    # o tra cuu tung ma: phien toi can gia bao nhieu, khoi luong bao nhieu
    from lookup import build as _lk
    from vn300 import build_topn as _tn
    _C = dict(E.CFG); _C.update(PROD)
    _dd,_II,_tls,_sect = E.load()
    # Truyen DEN THI TRUONG va DANH MUC DANG CAM vao, de o tra cuu noi duoc
    # "neu vao lenh thi vao bao nhieu %% NAV" bang dung con so bo may se dat.
    out['lookup'] = _lk(r['d'], r['I'], _tls, _sect, _C, _tn(r['I'], _C['top_n']),
                        light=_rg_light, vi_the=out['open_positions'], nav=r['nav'])
    print('EXTRA lookup', len(out['lookup']), 'ma', flush=True)

    # DANH SACH SOI TAY: qua het 7 cong, chi vuong dung cong CFO.
    # Anh Son tu ra soat nhom nay — cong CFO de bat oan (mot quy om hang, mot ky
    # tra truoc nha cung cap deu co the lam CFO am ma doanh nghiep van khoe).
    # KHONG anh huong gi toi bo may: nhung ma nay van bi chan nhu cu.
    out['cfo_soi'] = sorted(
        [dict(sym=v['sym'], name=v['name'], sector=v['sector'], score=v['score'],
              price=v['price'], need_px=v['need_px'], need_vol=v['need_vol'],
              base=v['base'], gtgd=v['gtgd'], mktcap=v['mktcap'], fund=v['fund'],
              cfo_ty=v.get('cfo_ty'), tim=v.get('tim'), tim_vi=v.get('tim_vi'))
         for v in out['lookup'].values() if v.get('cfo_only')],
        key=lambda x: -(x['score'] or 0))
    print('EXTRA cfo_soi', len(out['cfo_soi']), 'ma chi vuong cong CFO', flush=True)
    print('EXTRA monthly',len(out['monthly']),'top6m',len(out['top6m']['deals']),'candles',len(out['candles']),flush=True)

    out['v1']= {'trades':171,'per_year':22.4,'total_return':0.605,'cagr':0.064,'maxdd':0.092,'pf':2.80,'sharpe':1.03,'universe':311}
    # ---- CAU HINH DANG CHAY, nhung thang vao trang ----
    # Truoc day trang go tay "TOP 110", "nen 18%", "dong tien 1,20" vao tung cau
    # chu. Doi luat o day thi chu tren trang van noi so cu — so kien truc da ghi
    # ba lan cung mot bay. Nay trang doc thang khoi nay (part2.js: cpTop/cpNen/
    # cpDT) va verify_build.py cung doc no de so voi screener, nen khong the lech.
    out['cfg_prod'] = {k: PROD.get(k, E.CFG.get(k)) for k in (
        'sector_cap', 'pyr_caps', 'max_n_in_loop', 'min_history', 'cfo_mode', 'rank_mode',
        'base_size', 'max_pos', 'max_total', 'max_pos_n', 'min_size', 'size_map',
        'base_len', 'base_range', 'score_floor', 'top_n', 'use_top_liquid',
        'gtgd_min', 'volat_min', 'vol_floor', 'vol_ceil', 'ordimb_min',
        'stop', 'hard_stop', 't_valve', 'big_win', 'trail_ma', 'trail_fast', 'conf',
        'be_trigger', 'be_level', 'profit_lock', 'fee_buy', 'fee_sell', 'slip', 'min_mktcap',
        'use_cond6', 'use_cond8', 'use_hard_stop', 'use_protective_candle',
        'use_big_sell', 'use_partial_take', 'use_be', 'use_giveback',
        'use_orange_cut', 'orange_cut_only_if_worse', 'use_market_gate',
        'use_ftd', 'use_pyramid', 'use_ordimb',
        'cb_enable', 'stage1', 'entry_mode', 'entry_next_open', 'hs_from', 'sell_from', 'fill_ratio',
        'trig_hose', 'trig_hnx', 'dk5_lo', 'dk5_hi', 'mo_by', 'mo_need', 'mo_window',
        'mo_stop', 'mo_stop_until', 'valve_min', 'ceil_vol_floor', 'probe_exit', 'pre_proxy', 'pre_min',
        'max_unconf', 'unconf_count')}

    import hashlib as _hl
    _full = dict(E.CFG); _full.update(PROD)
    out['prod_config_hash'] = _hl.sha256(json.dumps(_full, sort_keys=True, default=str).encode()).hexdigest()[:12]
    out['cfg_prod']['prod_config_hash'] = out['prod_config_hash']
    # ---- SIGNAL SPEC for the next session (live scanner parity, signal_spec.py) ----
    from spec_export import export as _spx
    _C2 = dict(E.CFG); _C2.update(PROD)
    _held = [x['sym'] for x in out['open_positions']]
    out['spec'], out['spec_u'] = _spx(r['d'], r['I'], _tls, _sect, _C2, len(r['d']['cal']) - 1,
                                      syms_extra=tuple(_held))
    print('SPEC', len(out['spec']), 'ma cho phien ke tiep · TOP-N cut',
          round(out['spec_u']['topn_cut'] / 1e9, 1), 'ty', flush=True)

    # ---- LOP QUAN SAT (R27A) — chi hien thi, KHONG thuoc PROD, KHONG vao prod_config_hash ----
    try:
        import observability as _OB
        _d = r['d']; _last = len(cal) - 1; _AC, _AH, _AL, _PX = _d['AdjClose'], _d['AdjHigh'], _d['AdjLow'], _d['PriceClose']
        _J = {str(s_): j_ for j_, s_ in enumerate(_d['sym'])}; _IX = {str(c_): i_ for i_, c_ in enumerate(cal)}
        _paths = {}
        _cands = {(p['sym'], p['entry']): p.get('cond9') for p in out['open_positions']}
        for _s in (out.get('signals_recent') or []) + (out.get('signals_today') or []):   # vi the so ghi tien = lenh cua bo may
            _cands.setdefault((_s['sym'], _s['date']), ('DAT' if _s.get('cond9_ok') else 'TRUOT'))
        for (_sy, _en), _c9 in _cands.items():
            if _sy in _J and _en in _IX:
                _pb = _OB.path_block(_AC, _AH, _AL, _PX, _IX[_en], _J[_sy], _last, E.CFG['fee_buy'],
                                     cond9=(None if _c9 in (None, 'CHUA_CO') else _c9 == 'DAT'))
                if _pb:
                    _pb['breakout_date'] = _en; _paths[f'{_sy}|{_en}'] = _pb
        _C3 = dict(E.CFG); _C3.update(PROD)
        _w, _ws = _OB.watch78(_d, r['I'], _tls, _sect, _C3, _last, held=set(x['sym'] for x in out['open_positions']),
                              today_signals=set(x['sym'] for x in (out.get('signals_today') or [])))
        out['observability'] = dict(config=_OB.OBS, asof=str(cal[-1]), paths=_paths, watch78=_w, watch78_stats=_ws,
                                    gate_labels=_OB.GATE_VI, gates=list(_OB.GATES), label_vi=_OB.LABEL_VI)
        print('OBS', len(_paths), 'duong di ·', len(_w), 'ma gan dat', _ws, flush=True)
    except Exception as _e:
        # lop quan sat hong KHONG duoc lam hong ban dung: ghi ro, trang tu an khoi nay
        out['observability'] = dict(error=f'{type(_e).__name__}: {_e}')
        print('OBS HONG:', _e, flush=True)

    # ---- R29 MISSED-WINNER AUDIT — chi do, KHONG thuoc PROD, KHONG vao prod_config_hash ----
    try:
        import missed as _MS
        _C4 = dict(E.CFG); _C4.update(PROD)
        out['missed_audit'] = _MS.audit(r['d'], r['I'], _tls, _C4)
        print('R29', out['missed_audit']['n_events'], 'su kien', flush=True)
    except Exception as _e:
        out['missed_audit'] = dict(error=f'{type(_e).__name__}: {_e}')
        print('R29 HONG:', _e, flush=True)

    def cv(o):
        if isinstance(o,dict): return {k:cv(v) for k,v in o.items()}
        if isinstance(o,list): return [cv(x) for x in o]
        if isinstance(o,(np.floating,np.integer)): return float(o)
        if isinstance(o,np.bool_): return bool(o)
        return o
    json.dump(cv(out),open('data/site_data2.json','w'),ensure_ascii=False)
    print('SAVED trades',len(out['prod']['trades']),'signals',len(out['signals']))
