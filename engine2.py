# -*- coding: utf-8 -*-
"""NGUYEN SON INVEST - BOT v2 (du lieu FireAnt)
   He 9 lop theo 'He Thong Giao Dich Hop Nhat v1.0', chay walk-forward khong nhin truoc."""
import numpy as np, json, datetime as dt, copy
from fa_prep import build as fa_build
from fa_ind import indicators
from regime2 import build_regime
from prep import parse_funda
from engine import funda_timeline, as_of, risk_gate, canslim_score, BANKS, BROKERS, INSUR

CFG = dict(
  nav0=1_000_000_000.0, fee_buy=0.0015, fee_sell=0.0025, slip=0.002,
  base_size=0.10, max_pos=0.20, max_total=0.60, max_pos_n=8, min_size=0.02,
  min_mktcap=1000e9, min_history=250,
  use_top_liquid=True, top_n=300,   # chi giao dich TOP 300 GTGD binh quan 20 phien (tinh theo tung phien)
  vol_floor=2.0, vol_ceil=4.5, gtgd_min=15e9, volat_min=0.015,
  base_len=30, base_range=0.18, no_ceil_in_base=False,
  score_floor=45, use_cond6=False, use_cond8=True,
  t_valve=6, stop=-0.07, hard_stop=-0.10, big_win=0.25,
  trail_ma=30, trail_fast=10, conf=2,
  use_protective_candle=False, use_big_sell=False, use_orange_cut=True,
  # Chi ha 1/3 khi den THUC SU XAU DI so voi luc mua. Mua duoi den Cam (co 35%)
  # roi hai phien sau lai ha 1/3 cung vi den Cam la vo ly — khong co gi thay doi ca.
  orange_cut_only_if_worse=False,
  use_partial_take=False, use_hard_stop=True, use_pyramid=True,
  use_market_gate=True, use_ftd=True, ftd_gain=0.015,
  size_map={'XANH':1.0,'VANG':0.5,'CAM':0.0,'DO':0.0},
  use_ordimb=False, ordimb_min=1.0, hard_ceiling=False, use_fnet=False, rs_min=0,
  use_giveback=False, gb_trigger=0.10, gb_keep=0.50, use_shelf=False, shelf_range=0.10,
  re_cfo_warn=False, icr_cfo_rescue=False, cfo_icr_min=3.0,   # True = BDS co CFO<0 chi bi co vang (size x0.5) thay vi chan han
  use_be=False, be_trigger=0.08, be_level=0.01,
  # nan_tot_fix=False -> tai hien loi cu (tran tong von + tran nganh bi NaN lam
  # ngung ap dung khi co ma bi treo). Chi de chay A/B, dung bat o PROD.
  nan_tot_fix=True,
  start='2019-01-02', end=None,
  # --- LOP KIEM DINH: truot gia bat doi xung ---
  # Chieu MUA tran thuong truot it (khop duoc la may) nhung THIEU khoi luong.
  # Chieu BAN thao khi gay MA thi truot RAT NANG vi trang ben mua.
  # De None thi ca hai chieu dung chung 'slip' nhu cu — khong doi hanh vi PROD.
  slip_buy=None, slip_sell=None,
  # --- LOP KIEM DINH: ngat mach bao ve von (circuit breaker) ---
  # Win rate ~36% thi mot chuoi 8-10 lenh thua lien tiep la chuyen binh thuong
  # ve mat xac suat. Ngat mach KHONG doan thi truong — no chi ha do lon vi the
  # sau khi thiet hai da xay ra, va tu mo lai khi NAV lap dinh moi.
  cb_enable=False, cb_dd=0.08, cb_losses=6, cb_cut=0.5, cb_days=10,
  # --- 2026-09-23 audit flags. Defaults reproduce the pre-audit engine exactly;
  #     PROD in produce2.py decides which ones are switched on. ---
  sector_cap=0.30,          # was a hard-coded 0.30 inside run()
  pyr_caps=False,           # True = pyramid add-on respects max_total + sector_cap (shared allocator)
  max_n_in_loop=False,      # True = max_pos_n re-checked for every same-day entry
  rank_mode='score',        # same-session priority when capital is scarce (see RANKERS)
  cfo_mode='hard',          # hard | off | warn | sector | repeat   (see engine.risk_gate)
  cfo_warn_mul=0.5,
  hs_from=2,                # first holding session where exits (incl. hard stop) are evaluated
  fill_ratio=1.0,           # fraction of the intended shares actually filled
  miss_prob=0.0, miss_seed=1, force_miss=None,   # missed-signal stress
  stage1=None,              # two-stage entry: fraction bought at signal close w/o Cond9
  log_cands=False,          # record every same-day candidate set (ranking research)
)

class Pos:
    __slots__=('sym','j','ei','epx','sh','peak','b20','b10','part','pyr','sector','bo_low','stage','oi_ok','tgt','eraw','pyr_d','pyr_raw','pyr_adj')
    def __init__(s,**kw):
        for k,v in kw.items(): setattr(s,k,v)

# ---------------------------------------------------------------------------
# SAME-SESSION PRIORITY. When several stocks break out on the same day and cash
# or caps bind, the order below decides who gets the money. Every key uses only
# information known at the signal-session close. Ties -> symbol (deterministic).
# Percentile ranks are computed WITHIN the day's candidate set (0 = worst, 1 = best).
# ---------------------------------------------------------------------------
def _pr(vals, higher_better=True):
    n=len(vals)
    if n<=1: return [1.0]*n
    order=sorted(range(n), key=lambda k:(vals[k] if higher_better else -vals[k]))
    out=[0.0]*n
    for r,k in enumerate(order): out[k]=r/(n-1)
    return out

RANKERS=('score','base','oi','score_base','score_oi','score_base_oi','multi','score_sector','pct')
def rank_rows(rows, mode='score', held_sectors=()):
    if not rows: return rows
    if mode=='score':          # CURRENT PROD behaviour: CANSLIM score desc, then symbol
        rows.sort(key=lambda r:(-r['sc'], r['sym'])); return rows
    sc=_pr([r['sc'] for r in rows]); bs=_pr([r['base'] for r in rows], False)
    oi=_pr([r['oi'] if r['oi']==r['oi'] else 0.0 for r in rows]); vr=_pr([r['volr'] for r in rows])
    rs=_pr([r['rs'] for r in rows])
    if mode=='base':            key=lambda k:-bs[k]
    elif mode=='oi':            key=lambda k:-oi[k]
    elif mode=='pct':           key=lambda k:-rows[k]['pct']
    elif mode=='score_base':    key=lambda k:-(sc[k]+bs[k])
    elif mode=='score_oi':      key=lambda k:-(sc[k]+oi[k])
    elif mode=='score_base_oi': key=lambda k:-(sc[k]+bs[k]+oi[k])
    elif mode=='multi':         key=lambda k:-(sc[k]+bs[k]+oi[k]+vr[k]+rs[k])
    elif mode=='score_sector':  key=lambda k:(rows[k]['sector'] in held_sectors, -rows[k]['sc'])
    else: raise ValueError(mode)
    idx=sorted(range(len(rows)), key=lambda k:(key(k), rows[k]['sym']))
    rows[:]=[rows[k] for k in idx]
    return rows

_CACHE={}
def load():
    if 'd' not in _CACHE:
        d=fa_build(); _CACHE['d']=d
        _CACHE['I']=indicators(d)
        fu=parse_funda('data/funda_raw2.json')
        _CACHE['tls']={s:funda_timeline(r) for s,r in fu.items() if r}
        try: _CACHE['sect']=json.load(open('data/sector2.json'))
        except Exception: _CACHE['sect']={}
        from engine import load_sector_groups
        load_sector_groups(_CACHE['sect'])
    return _CACHE['d'], _CACHE['I'], _CACHE['tls'], _CACHE['sect']

def screen(i, d, I, tls, sect, C, TOPN, base_rng, base_ok, trig, day, held=(),
           blocked=None, ignore_ordimb=False):
    """THE production entry screen for session i (every condition except capital).
    Single source of truth: run() calls it, and tests/test_parity.py compares the
    live scanner's signal_spec.evaluate() against it session by session."""
    S=d['sym']; AC=d['AdjClose']; AH=d['AdjHigh']; AL_=d['AdjLow']; MC=d['MarketCap']; TV=d['TotalValue']
    uni = TOPN[i] if TOPN is not None else np.ones(len(S),dtype=bool)
    cand=np.where(trig[i] & uni & (MC[i]>C['min_mktcap']) & (I['nbars'][i]>=C['min_history'])
                  & (I['volr'][i]>=C['vol_floor']) & (TV[i]>=C['gtgd_min'])
                  & (I['volat20'][i]>=C['volat_min'])
                  & base_ok[i])[0]
    rows=[]
    for j in cand:
        sym=str(S[j])
        if sym in held: continue
        if C['use_cond8'] and AC[i,j] < (AH[i,j]+AL_[i,j])/2: continue
        if C['use_cond6'] and I['volr'][i,j]>C['vol_ceil']: continue
        oi_ok = bool(I['ordimb'][i,j]>=C['ordimb_min'])
        # Two-stage research mode: Cond9 is NOT observable at the signal close,
        # so the candidate set is built without it and Cond9 is only used the
        # next morning to confirm (top up) or abort (sell the probe).
        if C['use_ordimb'] and not oi_ok and not ignore_ordimb: continue
        if C['use_fnet'] and not (I['fnet'][i,j]>=0): continue
        if C['rs_min'] and not (I['rs'][i,j]>=C['rs_min']): continue
        tl=tls.get(sym)
        f=as_of(tl,day) if tl else None
        if f is None: continue
        blk,why,rmul=risk_gate(sym,f)
        if blk:
            if blocked is not None:
                k=(why or 'NA').split()[0]; blocked[k]=blocked.get(k,0)+1
            continue
        npg=f.get('npat_yoy')
        if npg is not None and 0<=npg<0.25: continue        # DK5
        sc,pts=canslim_score(f, I['rs'][i,j], I['mom3'][i,j],
                float(AC[i,j]/I['hi52'][i,j]-1) if I['hi52'][i,j]>0 else None,
                float(I['volr'][i,j]), float(I['tvma20'][i,j]))
        if sc<C['score_floor']: continue
        bm=1.2 if base_rng[i,j]<=0.10 else 1.0
        rows.append(dict(sc=float(sc),j=int(j),sym=sym,rmul=rmul,bm=bm,pts=pts,
                         base=float(base_rng[i,j]),oi=float(I['ordimb'][i,j]),oi_ok=oi_ok,
                         volr=float(I['volr'][i,j]),rs=float(I['rs'][i,j]) if not np.isnan(I['rs'][i,j]) else 0.0,
                         mom=float(I['mom3'][i,j]) if not np.isnan(I['mom3'][i,j]) else 0.0,
                         pct=float(I['pct'][i,j]),sector=sect.get(sym,'Khác'),
                         fund=float(sum(pts.get(k,0) for k in ('C1','C2','C3','A1','A2')))))
    return rows

def prep_masks(d, I, C):
    """Arrays screen() needs, built exactly as run() builds them."""
    base_rng=(I['base_hi']-I['base_lo'])/np.where(I['base_lo']>0,I['base_lo'],np.nan)
    shelf_rng=(I['sh_hi']-I['sh_lo'])/np.where(I['sh_lo']>0,I['sh_lo'],np.nan)
    TOPN=None
    if C.get('use_top_liquid'):
        from vn300 import build_topn
        TOPN=build_topn(I, int(C.get('top_n',300)))
    base_ok=(base_rng<=C['base_range'])
    if C['use_shelf']: base_ok=base_ok|(shelf_rng<=C['shelf_range'])
    _thr=(I['thr_hard'] if C['hard_ceiling'] else I['thr'])
    if C.get('trig_pct') is not None: _thr=np.full_like(_thr, float(C['trig_pct']))
    trig=I['pct']>=_thr
    return base_rng, base_ok, TOPN, trig

def run(cfg=None, log=True):
    C=dict(CFG); C.update(cfg or {})
    import engine as _eng
    _eng.CFG['re_cfo_warn']=C.get('re_cfo_warn',False)
    _eng.CFG['icr_cfo_rescue']=C.get('icr_cfo_rescue',False)
    _eng.CFG['cfo_icr_min']=C.get('cfo_icr_min',3.0)   # dong bo co sang risk_gate
    _eng.CFG['cfo_mode']=C.get('cfo_mode','hard')
    _eng.CFG['cfo_warn_mul']=C.get('cfo_warn_mul',0.5)
    import allocator as AL
    _rng=np.random.default_rng(int(C.get('miss_seed',1)))
    _fm=set(tuple(x) for x in (C.get('force_miss') or []))
    cands_log=[]; pend=[]   # pend: two-stage partial positions waiting for Cond9
    d,I,tls,sect = load()
    # Truot gia hai chieu. Khong khai bao rieng thi ca hai bang 'slip' — y het ban cu.
    SB = C['slip'] if C.get('slip_buy')  is None else float(C['slip_buy'])
    SS = C['slip'] if C.get('slip_sell') is None else float(C['slip_sell'])
    R=build_regime(d,I,C)
    cal=d['cal']; S=d['sym']; N=len(cal)
    PX=d['PriceClose']; AC=d['AdjClose']; AH=d['AdjHigh']; AL_=d['AdjLow']; AO=d['AdjOpen']
    TV=d['TotalValue']; MC=d['MarketCap']; V=d['Volume']
    base_rng=(I['base_hi']-I['base_lo'])/np.where(I['base_lo']>0,I['base_lo'],np.nan)
    shelf_rng=(I['sh_hi']-I['sh_lo'])/np.where(I['sh_lo']>0,I['sh_lo'],np.nan)
    # VU TRU GIAO DICH: chi TOP N ma thanh khoan nhat, tinh lai theo TUNG PHIEN
    # (khong dung danh sach chi so cua hom nay ap nguoc lai qua khu -> khong nhin truoc)
    TOPN=None
    if C.get('use_top_liquid'):
        from vn300 import build_topn
        TOPN=build_topn(I, int(C.get('top_n',300)))
    base_ok = (base_rng<=C['base_range'])
    if C['use_shelf']: base_ok = base_ok | (shelf_rng<=C['shelf_range'])
    _thr = (I['thr_hard'] if C['hard_ceiling'] else I['thr'])
    if C.get('trig_pct') is not None:
        _thr = np.full_like(_thr, float(C['trig_pct']))
    trig=I['pct']>=_thr
    i0=int(np.searchsorted(cal,C['start']))
    # Cat duoi de chay walk-forward: mot lat cat thoi gian that su, khong phai loc sau.
    if C.get('end'): N=min(N,int(np.searchsorted(cal,C['end'],side='right')))
    # trang thai ngat mach
    cb_peak=C['nav0']; cb_streak=0; cb_until=-1; cb_log=[]
    nav=C['nav0']; cash=nav; pos={}; trades=[]; eq=[]; sigs=[]; blocked={}
    for i in range(i0,N):
        day=dt.date.fromisoformat(str(cal[i]))
        mv=0.0
        for p in pos.values():
            px=AC[i,p.j]
            mv += (px if not np.isnan(px) else p.epx)*p.sh
        nav=cash+mv
        eq.append((str(cal[i]),nav,R['light'][i],int(R['dcount'][i])))
        # ---------- TWO-STAGE ENTRY: confirm or abort yesterday's probe at today's open ----------
        for sym in [s_ for s_,p_ in pos.items() if getattr(p_,'stage',0)==1 and p_.ei==i-1]:
            p=pos[sym]; op=AO[i,p.j]
            if np.isnan(op) or op<=0: op=AC[i-1,p.j]
            if p.oi_ok:
                c2=op*(1+SB)*(1+C['fee_buy'])
                _v=lambda q:(AC[i-1,q.j] if not np.isnan(AC[i-1,q.j]) else q.epx)*q.sh
                room,_=AL.addon_capacity(nav,cash,sum(_v(q) for q in pos.values()),
                                         sum(_v(q) for q in pos.values() if q.sector==p.sector),
                                         _v(p),cfg=C)
                add=AL.lots(min(max(0.0,p.tgt-p.sh*p.epx),room),c2)
                if add>=100:
                    p.epx=(p.epx*p.sh+c2*add)/(p.sh+add); cash-=add*c2; p.sh+=add
                p.stage=2
            else:
                # Cond9 failed -> sell the probe at the open. T+2 settlement does not
                # allow this in reality before session ei+2; we model the exit at the
                # ei+2 open instead (conservative) by deferring when held<2.
                p.stage=3
        for sym in [s_ for s_,p_ in pos.items() if getattr(p_,'stage',0)==3 and i-p_.ei>=2]:
            p=pos[sym]; op=AO[i,p.j]
            if np.isnan(op) or op<=0: continue
            got=p.sh*op*(1-C['fee_sell']-SS); cash+=got
            trades.append(dict(sym=str(sym),sector=p.sector,entry=str(cal[p.ei]),exit=str(cal[i]),
                  entry_px=round(float(p.epx),2),exit_px=round(float(op),2),held=int(i-p.ei),
                  pnl_pct=round(float(op*(1-C['fee_sell']-SS)/p.epx-1)*100,2),
                  pnl_vnd=round(float(got-p.sh*p.epx)),reason='Cond9 không xác nhận — bán lệnh thăm dò',
                  light=R['light'][p.ei],peak=round(float(p.peak)*100,1)))
            del pos[sym]
        # ---------- LOP 8: BO THOAT ----------
        for sym in list(pos):
            p=pos[sym]; j=p.j; px=AC[i,j]
            if np.isnan(px): continue
            if getattr(p,'stage',0)==3: continue
            held=i-p.ei; gain=px/p.epx-1
            p.peak=max(p.peak,gain)
            mT=I['ma%d'%C['trail_ma']][i,j]; mF=I['ma%d'%C['trail_fast']][i,j]
            p.b20 = p.b20+1 if (not np.isnan(mT) and px<mT) else 0
            p.b10 = p.b10+1 if (not np.isnan(mF) and px<mF) else 0
            # T+2 settlement: shares bought at the close of session ei can first be
            # sold in session ei+2. `hs_from` < 2 is a counterfactual research switch
            # only (it would assume a sale the market does not allow).
            _hs = C['use_hard_stop'] and gain<=C['hard_stop'] and held>=C.get('hs_from',2)
            if held<2 and not _hs: continue
            r=None; frac=1.0
            if _hs: r='Hard stop −10%'
            elif C['use_protective_candle'] and not np.isnan(p.bo_low) and px<p.bo_low: r='Cây nến bảo vệ'
            elif held>=3 and gain<=C['stop']: r='Cắt lỗ −7%'
            elif C['use_giveback'] and p.peak>=C['gb_trigger'] and gain<=p.peak*C['gb_keep']: r='Chốt bảo vệ (trả lại %d%% đỉnh)'%int((1-C['gb_keep'])*100)
            elif C['use_be'] and p.peak>=C['be_trigger'] and gain<=C['be_level']: r='Về bờ (đã lãi %d%%)'%int(C['be_trigger']*100)
            elif held>=C['t_valve'] and gain<=0: r='Van thời gian T+%d'%C['t_valve']
            elif C['use_big_sell'] and I['pct'][i,j]<-0.04 and V[i,j]>1.2*I['vma20'][i,j]: r='Big sell khẩn'; frac=0.5
            elif p.peak>=C['big_win'] and p.b10>=C['conf']: r='Trailing MA%d (lãi lớn)'%C['trail_fast']
            elif p.b20>=C['conf']: r='Trailing MA%d'%C['trail_ma']
            elif C['use_partial_take'] and gain>=0.20 and V[i,j]>C['vol_ceil']*I['vma20'][i,j]: r='Chốt 1/3 (vol > 4,5×)'; frac=1/3
            elif (C['use_orange_cut'] and R['light'][i]=='CAM' and not p.part
                  and (not C.get('orange_cut_only_if_worse')
                       or R['light'][p.ei] in ('XANH','VANG'))): r='Đèn Cam — hạ 1/3'; frac=1/3
            if r:
                sh=int(p.sh*frac//100*100) if frac<1 else p.sh
                if sh<=0: continue
                got=sh*px*(1-C['fee_sell']-SS); cash+=got
                trades.append(dict(sym=str(sym),sector=sect.get(str(sym),'Khác'),
                  entry=str(cal[p.ei]),exit=str(cal[i]),entry_px=round(float(p.epx),2),
                  exit_px=round(float(px),2),held=int(held),
                  # RAW traded prices for chart markers (candles are raw). entry_px /
                  # exit_px above stay ADJUSTED (+fees) because P&L is computed on them.
                  entry_raw=round(float(getattr(p,'eraw',np.nan)),2),exit_raw=round(float(PX[i,j]),2),
                  pyr_date=getattr(p,'pyr_d',None),pyr_raw=getattr(p,'pyr_raw',None),pyr_adj=getattr(p,'pyr_adj',None),
                  pnl_pct=round(float(px*(1-C['fee_sell']-SS)/p.epx-1)*100,2),
                  pnl_vnd=round(float(got-sh*p.epx)),reason=r,
                  light=R['light'][p.ei],peak=round(float(p.peak)*100,1)))
                if C.get('cb_enable'):
                    cb_streak = cb_streak+1 if trades[-1]['pnl_pct']<=0 else 0
                p.sh-=sh
                if frac<1: p.part=True
                if p.sh<=0: del pos[sym]
        # ---------- LOP 0-7: MO LENH ----------
        smul=R['size'][i] if C['use_market_gate'] else 1.0
        # ---------- NGAT MACH BAO VE VON ----------
        # Kich hoat khi NAV thung nguong tu dinh HOAC dinh chuoi thua lien tiep.
        # Hieu luc cb_days phien, trong do co vi the bi nhan cb_cut (0 = ngung han).
        if C.get('cb_enable'):
            if nav>cb_peak: cb_peak=nav; cb_streak=0
            hit_dd  = (nav/cb_peak-1) <= -abs(C['cb_dd'])
            hit_str = cb_streak >= int(C['cb_losses'])
            if (hit_dd or hit_str) and i>cb_until:
                cb_until=i+int(C['cb_days'])
                cb_log.append(dict(date=str(cal[i]),
                                   ly_do=('NAV -%.0f%% tu dinh'%(100*abs(nav/cb_peak-1))) if hit_dd
                                         else ('%d lenh thua lien tiep'%cb_streak),
                                   den=str(cal[min(cb_until,N-1)])))
                cb_streak=0
            if i<=cb_until: smul*=float(C['cb_cut'])
        if smul>0 and len(pos)<C['max_pos_n']:
            two = C.get('stage1') is not None
            rows=screen(i, d, I, tls, sect, C, TOPN, base_rng, base_ok, trig, day,
                        held=pos, blocked=blocked, ignore_ordimb=two)
            rank_rows(rows, C.get('rank_mode','score'), {q.sector for q in pos.values()})
            day_log=[] if C.get('log_cands') and rows else None
            for rw in rows:
                j=rw['j']; sym=rw['sym']; sc=rw['sc']; rmul=rw['rmul']; bm=rw['bm']; pts=rw['pts']
                secn=rw['sector']
                if day_log is not None: day_log.append(dict(sym=sym,sc=sc,base=rw['base'],oi=rw['oi'],
                        volr=rw['volr'],rs=rw['rs'],mom=rw['mom'],pct=rw['pct'],sector=secn,fund=rw['fund'],
                        taken=False,why=None))
                if C.get('max_n_in_loop') and len(pos)>=C['max_pos_n']:
                    if day_log is not None: day_log[-1]['why']='max_pos_n'
                    continue
                # LOI `tot = NaN` (so 16/09, sua 18/09) -------------------------
                # Ma bi treo / khong co du lieu phien nay thi AC = NaN. Mot NaN lam
                # ca tong thanh NaN, va tu do HAI tran ngung ap dung AM THAM.
                # Mot ma bi treo KHONG co nghia la no dang co gia 0: thieu gia thi lay gia von.
                _dg = lambda q: (AC[i,q.j] if not np.isnan(AC[i,q.j]) else q.epx)*q.sh
                if C.get('nan_tot_fix', True):
                    tot=sum(_dg(q) for q in pos.values())
                    sec=sum(_dg(q) for q in pos.values() if q.sector==secn)
                else:                                   # ban CU, giu lai de chay A/B
                    tot=sum(AC[i,q.j]*q.sh for q in pos.values())
                    sec=sum(AC[i,q.j]*q.sh for q in pos.values() if q.sector==secn)
                if tot/nav>=C['max_total']:
                    if day_log is not None: day_log[-1]['why']='max_total'
                    break
                A=AL.entry_target(nav, cash, tot, sec, 0, None, risk_mul=rmul,
                                  base_rng=rw['base'], cfg=dict(C, max_pos_n=10**9), light_mul=smul)
                tgt=A['actual']
                if not A['ok']:
                    if day_log is not None: day_log[-1]['why']=A['binding']
                    continue
                # --- missed-fill stress (research only) ---
                if (sym,str(cal[i])) in _fm or (C.get('miss_prob',0)>0 and _rng.random()<C['miss_prob']):
                    if day_log is not None: day_log[-1]['why']='missed'
                    continue
                # gia khop: mac dinh dong cua phien tin hieu.
                ei=i; fill=AC[i,j]
                mode=C.get('entry_mode','close')      # close | next_open | next_vwap | signal_high | same_vwap
                if C.get('entry_next_open'): mode='next_open'
                if mode=='signal_high': fill=AH[i,j]
                elif mode=='same_vwap':
                    v=d['Volume'][i,j]; tv=d['TotalValue'][i,j]; ar=d['AdjRatio'][i,j]
                    fill=(tv/v/ar) if (v and v>0 and ar and ar>0) else AC[i,j]
                elif mode!='close':
                    if i+1>=N: continue
                    if mode=='next_open': fo=AO[i+1,j]
                    else:
                        v=d['Volume'][i+1,j]; tv=d['TotalValue'][i+1,j]; ar=d['AdjRatio'][i+1,j]
                        fo=(tv/v/ar) if (v and v>0 and ar and ar>0) else AO[i+1,j]
                    if fo is None or np.isnan(fo) or fo<=0: continue
                    ei=i+1; fill=float(fo)
                px=fill*(1+SB)*(1+C['fee_buy'])
                sh=AL.lots(tgt, px)
                if two: sh=int(sh*float(C['stage1'])//100*100)
                fr=float(C.get('fill_ratio',1.0))
                if fr<1.0: sh=int(sh*fr//100*100)
                if sh<100:
                    if day_log is not None: day_log[-1]['why']='lot'
                    continue
                cash-=sh*px
                # raw price actually paid, same bar as `fill` (FireAnt AdjRatio = PriceClose/AdjClose)
                _ar=d['AdjRatio'][ei,j]
                if mode in ('close','next_open','signal_high'):
                    _raw={'close':d['PriceClose'],'next_open':d['PriceOpen'],'signal_high':d['PriceHigh']}[mode][ei,j]
                    _raw=float(_raw) if _raw==_raw else float(fill*_ar)
                else:
                    _raw=round(float(fill*_ar)/10)*10 if (_ar==_ar and _ar>0) else float(PX[ei,j])
                pos[sym]=Pos(sym=sym,j=int(j),ei=ei,epx=float(px),sh=sh,peak=0.0,b20=0,b10=0,
                             part=False,pyr=False,sector=secn,bo_low=float(AL_[i,j]),
                             stage=(1 if two else 0), oi_ok=rw['oi_ok'], tgt=float(tgt),
                             eraw=_raw, pyr_d=None, pyr_raw=None, pyr_adj=None)
                if day_log is not None: day_log[-1].update(taken=True,why=None,size=round(sh*px/nav,4))
                if log: sigs.append(dict(date=str(cal[i]),sym=sym,score=round(float(sc),1),
                    px=round(float(PX[i,j])/1000,2),light=R['light'][i],sector=secn,pts=pts,
                    size_pct=round(sh*px/nav*100,2),theo_pct=round(A['theoretical']/nav*100,2),
                    binding=A['binding'],ordimb=round(rw['oi'],3),rmul=float(rmul),
                    base=round(float(rw['base']),4),raw_px=float(PX[i,j]),mode=mode))
            if day_log is not None: cands_log.append(dict(date=str(cal[i]),i=i,light=R['light'][i],cands=day_log))
        # ---------- LOP 9: PYRAMID ----------
        for sym,p in list(pos.items()):
            if not C['use_pyramid'] or p.pyr or R['light'][i]!='XANH': continue
            if getattr(p,'stage',0) in (1,3): continue
            held=i-p.ei
            if not (4<=held<=7): continue
            px=AC[i,p.j]
            if np.isnan(px) or px/p.epx-1<0.10 or px<0.999*I['hi10'][i,p.j]: continue
            add=int(p.sh*0.5//100*100)
            c2=px*(1+SB)*(1+C['fee_buy'])
            if C.get('pyr_caps'):
                # Shared allocator: an add-on must respect max_pos, max_total,
                # sector_cap and cash — not only max_pos and cash (audit 23/09/2026).
                _v = lambda q: (AC[i,q.j] if not np.isnan(AC[i,q.j]) else q.epx)*q.sh
                room,_why=AL.addon_capacity(nav, cash, sum(_v(q) for q in pos.values()),
                                            sum(_v(q) for q in pos.values() if q.sector==p.sector),
                                            px*p.sh, cfg=C)
                add=min(add, AL.lots(room, c2))
                if add<100: continue
            elif add<100 or (px*p.sh+add*px)>nav*C['max_pos'] or add*c2>cash: continue
            p.epx=(p.epx*p.sh+c2*add)/(p.sh+add); cash-=add*c2; p.sh+=add; p.pyr=True
            p.pyr_d=str(cal[i]); p.pyr_raw=round(float(PX[i,p.j]),2); p.pyr_adj=round(float(px),2)
    return dict(eq=eq,trades=trades,signals=sigs,R=R,blocked=blocked,pos=pos,
                nav=nav,cash=cash,cal=cal,d=d,I=I,cfg=C,cb_log=cb_log,cands=cands_log)

def metrics(r):
    eq=np.array([x[1] for x in r['eq']]); tr=r['trades']
    yrs=max(len(eq)/250,1e-9); dd=1-eq/np.maximum.accumulate(eq)
    p=[t['pnl_pct'] for t in tr]; w=[x for x in p if x>0]; l=[x for x in p if x<=0]
    gp=sum(t['pnl_vnd'] for t in tr if t['pnl_vnd']>0); gl=abs(sum(t['pnl_vnd'] for t in tr if t['pnl_vnd']<0))
    rets=np.diff(eq)/eq[:-1]
    return dict(trades=len(tr),per_year=round(len(tr)/yrs,1),
      total_return=round(float(eq[-1]/eq[0]-1),4),cagr=round(float((eq[-1]/eq[0])**(1/yrs)-1),4),
      maxdd=round(float(dd.max()),4),winrate=round(len(w)/len(p),4) if p else 0,
      avg_win=round(float(np.mean(w)),2) if w else 0,avg_loss=round(float(np.mean(l)),2) if l else 0,
      rr=round(abs(np.mean(w)/np.mean(l)),2) if (w and l) else None,
      pf=round(gp/gl,2) if gl>0 else None,expectancy=round(float(np.mean(p)),2) if p else 0,
      sharpe=round(float(np.mean(rets)/np.std(rets)*np.sqrt(250)),2) if np.std(rets)>0 else None,
      final_nav=round(float(eq[-1])))
