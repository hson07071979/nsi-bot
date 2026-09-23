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
PROD=dict(base_range=0.22, use_ftd=True, use_ordimb=True, ordimb_min=1.40, slip=0.0,
          size_map={'XANH':1.0,'VANG':0.6,'CAM':0.35,'DO':0.2},
          base_size=0.42, max_pos=0.50, max_total=1.0, max_pos_n=12,
          use_be=True, be_trigger=0.08, be_level=0.01,
          # Chi ha 1/3 khi den THUC SU XAU DI so voi luc mua. Mua duoi den Cam thi
          # da vao co 35% roi — ha tiep 1/3 cung vi den Cam la dem hai lan mot tin
          # hieu xau. Toan ky co 31/57 lan cat kieu do. A/B: +511,7% -> +540,5%,
          # co truot gia 0,2% thi +460,9% -> +492,4%; bo deal tot nhat ra van hon
          # (3.852 tr so 3.642 tr). Gia phai tra: DD 12,0% -> 12,7%.
          orange_cut_only_if_worse=True,
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
          use_top_liquid=True, top_n=120,
          # Nguong "lai lon" bat trailing MA10 de chot nhanh. 19% nam giua vung phang
          # 18-22% va cho DD thap nhat toan luoi (9,9%). Tu 24% tro len DD nhay len 13%.
          big_win=0.19,
          # ---- AUDIT 23/09/2026 (evidence/audit_r1_fixes.json) ----
          # Pyramid add-ons now respect max_total + sector_cap through the shared
          # allocator (allocator.py). Before, an add-on only checked max_pos and
          # cash, so a 30%-sector-capped entry could grow to ~45% in one sector.
          # Rule as documented, cost measured: +696,8% -> +579,1%, DD 9,46% -> 9,45%,
          # PF 5,84 -> 5,62, Sharpe 1,96 -> 1,89 (the old number relied on the breach).
          pyr_caps=True, sector_cap=0.30,
          # max_pos_n re-checked for every same-session entry (never bound in history,
          # identical result — pure correctness guard).
          max_n_in_loop=True,
          # Condition 8 (close in upper half of the candle) removed: A/B identical to
          # the trade (0 trades removed, with and without slippage), and it only adds
          # an intraday timing ambiguity to the live layer.
          use_cond8=False)
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
        trades=[{k:t.get(k) for k in ('sym','sector','entry','exit','entry_px','exit_px','entry_raw','exit_raw','pyr_date','pyr_raw','held','pnl_pct','pnl_vnd','reason','light','peak')} for t in tr])

if __name__=='__main__':
    out={}
    r=E.run(PROD, log=True); out['prod']=pack(r,'Nguyễn Sơn Bot v3 — FireAnt')
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
    _rg_light = out['regime'][-1]['light'] if out.get('regime') else 'XANH'
    out['open_positions']=[{'sym':p.sym,'entry':str(cal[p.ei]),'entry_px':round(float(p.epx),2),
        'shares':int(p.sh),'sector':p.sector,'last':round(float(r['d']['AdjClose'][-1,p.j]),2),
        'pnl':round(float(r['d']['AdjClose'][-1,p.j])/float(p.epx)*100-100,2)} for p in r['pos'].values()]
    out['blocked']={k:int(v) for k,v in r['blocked'].items()}
    out['universe_n']=int(len(r['d']['sym'])); out['asof']=str(cal[-1])
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
        'be_trigger', 'be_level', 'fee_buy', 'fee_sell', 'slip', 'min_mktcap',
        'use_cond6', 'use_cond8', 'use_hard_stop', 'use_protective_candle',
        'use_big_sell', 'use_partial_take', 'use_be', 'use_giveback',
        'use_orange_cut', 'orange_cut_only_if_worse', 'use_market_gate',
        'use_ftd', 'use_pyramid', 'use_ordimb')}

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

    def cv(o):
        if isinstance(o,dict): return {k:cv(v) for k,v in o.items()}
        if isinstance(o,list): return [cv(x) for x in o]
        if isinstance(o,(np.floating,np.integer)): return float(o)
        if isinstance(o,np.bool_): return bool(o)
        return o
    json.dump(cv(out),open('data/site_data2.json','w'),ensure_ascii=False)
    print('SAVED trades',len(out['prod']['trades']),'signals',len(out['signals']))
